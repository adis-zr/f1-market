"""Settlement service for settling events and markets."""
import logging
from decimal import Decimal
from typing import Dict, List, Optional
from db import (
    db, utc_now, Event, Market, MarketSettlement, Position, EventResult, ScoringRule,
    MarketStatus, EventStatus, TransactionType, FormulaType
)
from services.wallet_service import WalletService
from services.scoring import get_scoring_strategy

logger = logging.getLogger(__name__)


class SettlementService:
    """Service for settling events and markets."""
    
    @staticmethod
    def compute_payout_per_share(event_result: EventResult, scoring_rule: ScoringRule) -> Decimal:
        """
        Compute payout per share based on event result and scoring rule.

        Uses the strategy pattern to delegate to the appropriate scoring formula
        based on the scoring_rule's formula_type. This makes it easy to add
        sport-specific scoring strategies.

        Args:
            event_result: EventResult instance containing performance data
            scoring_rule: ScoringRule instance containing scoring parameters

        Returns:
            Payout per share as Decimal
        """
        # Get the appropriate scoring strategy based on formula type
        strategy = get_scoring_strategy(scoring_rule.formula_type)

        # Delegate payout computation to the strategy
        return strategy.compute_payout(event_result, scoring_rule)
    
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
        # Get event with row-level lock to prevent concurrent settlement
        event = Event.query.filter_by(id=event_id).with_for_update().first()
        if not event:
            raise ValueError(f"Event {event_id} not found")

        # Idempotency check: if event is already finished, return early
        if event.status == EventStatus.FINISHED:
            return {
                "success": True,
                "event_id": event_id,
                "markets_settled": 0,
                "positions_settled": 0,
                "message": "Event already settled",
                "already_settled": True
            }

        # Get all markets for this event that are open or closed (not already settled)
        # Lock markets to prevent concurrent modifications
        markets = Market.query.filter_by(event_id=event_id).filter(
            Market.status.in_([MarketStatus.OPEN, MarketStatus.CLOSED])
        ).with_for_update().all()

        if not markets:
            return {
                "success": True,
                "event_id": event_id,
                "markets_settled": 0,
                "positions_settled": 0,
                "message": "No markets to settle"
            }
        
        settlements = []
        skipped_markets = []
        total_positions_settled = 0
        total_payout = Decimal('0')

        try:
            for market in markets:
                # Get EventResult for this market's asset
                # For participant assets, we need the participant_id
                asset = market.asset
                if not asset:
                    skipped_markets.append({'market_id': market.id, 'reason': 'no_asset'})
                    logger.warning(f"Market {market.id} skipped: no asset linked")
                    continue

                if asset.type.value == "participant" and asset.participant_id:
                    event_result = EventResult.query.filter_by(
                        event_id=event_id,
                        participant_id=asset.participant_id
                    ).first()
                elif asset.type.value == "team" and asset.team_id:
                    # For team assets, we might need to aggregate participant results
                    # For now, skip team assets (can be implemented later)
                    skipped_markets.append({'market_id': market.id, 'reason': 'team_asset_not_supported', 'asset_id': asset.id})
                    continue
                else:
                    # Unknown asset type
                    skipped_markets.append({'market_id': market.id, 'reason': 'unknown_asset_type', 'asset_id': asset.id})
                    logger.warning(f"Market {market.id} skipped: unknown asset type for asset {asset.id}")
                    continue

                if not event_result:
                    # No result found for this asset - skip this market
                    skipped_markets.append({'market_id': market.id, 'reason': 'no_event_result', 'asset_id': asset.id})
                    logger.warning(f"Market {market.id} skipped: no EventResult for asset {asset.id} (participant_id={asset.participant_id})")
                    continue

                # Get scoring rule
                scoring_rule = market.scoring_rule
                if not scoring_rule:
                    skipped_markets.append({'market_id': market.id, 'reason': 'no_scoring_rule', 'asset_id': asset.id})
                    logger.warning(f"Market {market.id} skipped: no scoring rule defined")
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
                    settled_at=utc_now(),
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

                    # Calculate settlement P&L
                    avg_entry = Decimal(str(position.avg_entry_price))
                    settlement_pnl = (payout_per_share - avg_entry) * shares

                    # Credit wallet
                    WalletService.add_ledger_entry(
                        user_id=position.user_id,
                        amount=gross_payout,
                        transaction_type=TransactionType.SETTLEMENT,
                        reference_type="market",
                        reference_id=market.id,
                        description=f"Settlement for {shares} shares in market {market.id}"
                    )

                    # Update position (close it and record realized P&L)
                    position.realized_pnl = Decimal(str(position.realized_pnl)) + settlement_pnl
                    position.shares = Decimal('0')
                    position.last_marked_at = utc_now()
                    
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
                "markets_skipped": len(skipped_markets),
                "positions_settled": total_positions_settled,
                "total_payout": float(total_payout),
                "settlements": settlements,
                "skipped_markets": skipped_markets
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error settling event {event_id}: {e}", exc_info=True)
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
        event = db.session.get(Event, event_id)
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

