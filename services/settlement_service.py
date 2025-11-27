"""Settlement service for settling events and markets."""
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional
from db import (
    db, Event, Market, MarketSettlement, Position, EventResult, ScoringRule,
    MarketStatus, EventStatus, TransactionType, FormulaType
)
from services.wallet_service import WalletService


class SettlementService:
    """Service for settling events and markets."""
    
    @staticmethod
    def compute_payout_per_share(event_result: EventResult, scoring_rule: ScoringRule) -> Decimal:
        """
        Compute payout per share based on event result and scoring rule.
        
        Formula: payout_per_share = alpha * (primary_score / max_score) + beta
        
        Args:
            event_result: EventResult instance
            scoring_rule: ScoringRule instance
        
        Returns:
            Payout per share as Decimal
        """
        primary_score = Decimal(str(event_result.primary_score))
        max_score = Decimal(str(scoring_rule.max_score))
        alpha = Decimal(str(scoring_rule.alpha))
        beta = Decimal(str(scoring_rule.beta))
        
        if max_score == 0:
            raise ValueError("Scoring rule max_score cannot be zero")
        
        # Normalize score
        normalized = primary_score / max_score
        
        # Apply formula based on formula_type
        if scoring_rule.formula_type == FormulaType.LINEAR_NORMALIZED:
            payout = alpha * normalized + beta
        elif scoring_rule.formula_type == FormulaType.SIGMOID:
            # Sigmoid: alpha * (1 / (1 + exp(-k * normalized))) + beta
            # k is a parameter, default to 10 if not in config
            import math
            k = scoring_rule.config_json.get('k', 10) if scoring_rule.config_json else 10
            sigmoid_value = Decimal(str(1 / (1 + math.exp(-k * float(normalized)))))
            payout = alpha * sigmoid_value + beta
        elif scoring_rule.formula_type == FormulaType.PIECEWISE:
            # Piecewise: use config_json to define breakpoints
            # For now, fall back to linear
            payout = alpha * normalized + beta
        else:
            # Default to linear
            payout = alpha * normalized + beta
        
        # Ensure payout is non-negative
        return max(payout, Decimal('0'))
    
    @staticmethod
    def settle_event(event_id: int, source: str = "event_result") -> Dict:
        """
        Settle all markets for an event.
        
        This method:
        1. Loads all markets for the event
        2. For each market, computes payout_per_share from EventResult + ScoringRule
        3. Creates MarketSettlement records
        4. Settles all positions (credits wallets, closes positions)
        5. Updates Event status to finished
        
        Args:
            event_id: Event ID
            source: Source of settlement (e.g., "event_result", "manual")
        
        Returns:
            Dict with settlement summary
        """
        # Get event
        event = Event.query.get(event_id)
        if not event:
            raise ValueError(f"Event {event_id} not found")
        
        # Get all markets for this event that are open or closed (not already settled)
        markets = Market.query.filter_by(event_id=event_id).filter(
            Market.status.in_([MarketStatus.OPEN, MarketStatus.CLOSED])
        ).all()
        
        if not markets:
            return {
                "success": True,
                "event_id": event_id,
                "markets_settled": 0,
                "positions_settled": 0,
                "message": "No markets to settle"
            }
        
        settlements = []
        total_positions_settled = 0
        total_payout = Decimal('0')
        
        try:
            for market in markets:
                # Get EventResult for this market's asset
                # For participant assets, we need the participant_id
                asset = market.asset
                if not asset:
                    continue
                
                if asset.type.value == "participant" and asset.participant_id:
                    event_result = EventResult.query.filter_by(
                        event_id=event_id,
                        participant_id=asset.participant_id
                    ).first()
                elif asset.type.value == "team" and asset.team_id:
                    # For team assets, we might need to aggregate participant results
                    # For now, skip team assets (can be implemented later)
                    continue
                else:
                    # Unknown asset type
                    continue
                
                if not event_result:
                    # No result found for this asset - skip this market
                    # Could also set payout to 0
                    continue
                
                # Get scoring rule
                scoring_rule = market.scoring_rule
                if not scoring_rule:
                    continue
                
                # Compute payout per share
                payout_per_share = SettlementService.compute_payout_per_share(
                    event_result,
                    scoring_rule
                )
                
                # Get current price for settlement_price (before settlement)
                from pricing.bonding_curve import get_current_supply, price
                current_supply = get_current_supply(market.id)
                settlement_price = price(
                    current_supply,
                    Decimal(str(market.a)),
                    Decimal(str(market.b))
                )
                
                # Create MarketSettlement record
                market_settlement = MarketSettlement(
                    market_id=market.id,
                    settled_at=datetime.utcnow(),
                    settlement_price=settlement_price,
                    payout_per_share=payout_per_share,
                    source=source
                )
                db.session.add(market_settlement)
                
                # Update market status
                market.status = MarketStatus.SETTLED
                
                # Settle all positions in this market
                positions = Position.query.filter_by(market_id=market.id).filter(
                    Position.shares > 0
                ).all()
                
                for position in positions:
                    shares = Decimal(str(position.shares))
                    gross_payout = shares * payout_per_share
                    
                    # Credit wallet
                    WalletService.add_ledger_entry(
                        user_id=position.user_id,
                        amount=gross_payout,
                        transaction_type=TransactionType.SETTLEMENT,
                        reference_type="market",
                        reference_id=market.id,
                        description=f"Settlement for {shares} shares in market {market.id}"
                    )
                    
                    # Update position (close it)
                    position.shares = Decimal('0')
                    position.last_marked_at = datetime.utcnow()
                    
                    total_positions_settled += 1
                    total_payout += gross_payout
                
                settlements.append({
                    "market_id": market.id,
                    "asset_id": asset.id,
                    "payout_per_share": float(payout_per_share),
                    "settlement_price": float(settlement_price),
                    "positions_settled": len(positions)
                })
            
            # Update event status
            event.status = EventStatus.FINISHED
            
            # Commit all changes
            db.session.commit()
            
            return {
                "success": True,
                "event_id": event_id,
                "markets_settled": len(settlements),
                "positions_settled": total_positions_settled,
                "total_payout": float(total_payout),
                "settlements": settlements
            }
        
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Error settling event: {str(e)}")
    
    @staticmethod
    def get_settlement_info(market_id: int) -> Optional[Dict]:
        """
        Get settlement information for a market.
        
        Args:
            market_id: Market ID
        
        Returns:
            Dict with settlement info or None if not settled
        """
        settlement = MarketSettlement.query.filter_by(market_id=market_id).first()
        if not settlement:
            return None
        
        return {
            "market_id": market_id,
            "settled_at": settlement.settled_at.isoformat() if settlement.settled_at else None,
            "settlement_price": float(settlement.settlement_price),
            "payout_per_share": float(settlement.payout_per_share),
            "source": settlement.source,
            "created_at": settlement.created_at.isoformat() if settlement.created_at else None
        }
    
    @staticmethod
    def preview_settlement(event_id: int) -> Dict:
        """
        Preview what settlement would look like without actually settling.
        
        Args:
            event_id: Event ID
        
        Returns:
            Dict with preview of settlements
        """
        event = Event.query.get(event_id)
        if not event:
            raise ValueError(f"Event {event_id} not found")
        
        markets = Market.query.filter_by(event_id=event_id).filter(
            Market.status.in_([MarketStatus.OPEN, MarketStatus.CLOSED])
        ).all()
        
        previews = []
        
        for market in markets:
            asset = market.asset
            if not asset:
                continue
            
            if asset.type.value == "participant" and asset.participant_id:
                event_result = EventResult.query.filter_by(
                    event_id=event_id,
                    participant_id=asset.participant_id
                ).first()
            else:
                continue
            
            if not event_result or not market.scoring_rule:
                previews.append({
                    "market_id": market.id,
                    "asset_id": asset.id if asset else None,
                    "status": "no_result_or_rule",
                    "payout_per_share": None
                })
                continue
            
            payout_per_share = SettlementService.compute_payout_per_share(
                event_result,
                market.scoring_rule
            )
            
            # Count positions
            positions = Position.query.filter_by(market_id=market.id).filter(
                Position.shares > 0
            ).all()
            
            total_shares = sum(Decimal(str(p.shares)) for p in positions)
            total_payout = total_shares * payout_per_share
            
            previews.append({
                "market_id": market.id,
                "asset_id": asset.id,
                "payout_per_share": float(payout_per_share),
                "positions_count": len(positions),
                "total_shares": float(total_shares),
                "total_payout": float(total_payout)
            })
        
        return {
            "event_id": event_id,
            "markets_previewed": len(previews),
            "previews": previews
        }

