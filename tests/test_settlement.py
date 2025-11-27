"""Tests for settlement service."""
import pytest
from decimal import Decimal
from datetime import datetime
from db import db
from services.settlement_service import SettlementService
from services.market_service import MarketService
from db import (
    EventResult, ResultStatus, EventStatus, MarketStatus, TransactionType
)


class TestSettlementService:
    """Tests for SettlementService."""
    
    def test_compute_payout_per_share(self, app, test_event, test_participant, test_scoring_rule):
        """Test payout calculation."""
        with app.app_context():
            # Create event result
            event_result = EventResult(
                event_id=test_event.id,
                participant_id=test_participant.id,
                primary_score=Decimal('25'),  # Max score
                rank=1,
                status=ResultStatus.FINISHED
            )
            db.session.add(event_result)
            db.session.commit()
            
            # Compute payout
            payout = SettlementService.compute_payout_per_share(event_result, test_scoring_rule)
            
            # With alpha=1.0, beta=0.0, max_score=25, score=25
            # payout = 1.0 * (25/25) + 0.0 = 1.0
            assert abs(payout - Decimal('1.0')) < Decimal('0.01')
    
    def test_compute_payout_partial_score(self, app, test_event, test_participant, test_scoring_rule):
        """Test payout with partial score."""
        with app.app_context():
            # Create event result with half score
            event_result = EventResult(
                event_id=test_event.id,
                participant_id=test_participant.id,
                primary_score=Decimal('12.5'),  # Half of max
                rank=5,
                status=ResultStatus.FINISHED
            )
            db.session.add(event_result)
            db.session.commit()
            
            payout = SettlementService.compute_payout_per_share(event_result, test_scoring_rule)
            
            # payout = 1.0 * (12.5/25) + 0.0 = 0.5
            assert abs(payout - Decimal('0.5')) < Decimal('0.01')
    
    def test_settle_event_single_market(self, app, test_user, test_event, test_market, test_participant, test_asset, test_wallet):
        """Test settling an event with a single market."""
        with app.app_context():
            # Ensure asset points to participant
            test_asset.participant_id = test_participant.id
            db.session.commit()
            
            # Reload market to get updated asset
            test_market = db.session.merge(test_market)
            
            # Buy some shares
            MarketService.buy_shares(test_user.id, test_market.id, Decimal('10.0'))
            
            # Create event result
            event_result = EventResult(
                event_id=test_event.id,
                participant_id=test_participant.id,
                primary_score=Decimal('25'),  # Max score
                rank=1,
                status=ResultStatus.FINISHED
            )
            db.session.add(event_result)
            db.session.commit()
            
            # Get initial balance
            initial_balance = WalletService.get_balance(test_user.id)
            
            # Settle event
            result = SettlementService.settle_event(test_event.id)
            
            assert result['success'] is True
            assert result['markets_settled'] == 1
            assert result['positions_settled'] == 1
            
            # Check that wallet was credited
            final_balance = WalletService.get_balance(test_user.id)
            assert final_balance > initial_balance
            
            # Check that market is settled
            test_market = db.session.merge(test_market)
            assert test_market.status == MarketStatus.SETTLED
    
    def test_settle_event_multiple_markets(self, app, test_user, test_event, test_market, test_participant, test_asset, test_scoring_rule, test_wallet):
        """Test settling an event with multiple markets."""
        with app.app_context():
            # Ensure asset points to participant
            test_asset.participant_id = test_participant.id
            db.session.commit()
            
            # Reload market
            test_market = db.session.merge(test_market)
            
            # Create second market
            from db import Market, Asset, AssetType
            asset2 = Asset(
                type=AssetType.PARTICIPANT,
                participant_id=test_participant.id,
                symbol='TST2',
                display_name='Test Driver 2'
            )
            db.session.add(asset2)
            
            market2 = Market(
                event_id=test_event.id,
                asset_id=asset2.id,
                scoring_rule_id=test_scoring_rule.id,
                market_type='outright',
                status=MarketStatus.OPEN,
                a=Decimal('1.0'),
                b=Decimal('0.5')
            )
            db.session.add(market2)
            db.session.commit()
            
            # Buy shares in both markets
            MarketService.buy_shares(test_user.id, test_market.id, Decimal('10.0'))
            MarketService.buy_shares(test_user.id, market2.id, Decimal('5.0'))
            
            # Create event result
            event_result = EventResult(
                event_id=test_event.id,
                participant_id=test_participant.id,
                primary_score=Decimal('25'),
                rank=1,
                status=ResultStatus.FINISHED
            )
            db.session.add(event_result)
            db.session.commit()
            
            # Settle event
            result = SettlementService.settle_event(test_event.id)
            
            assert result['success'] is True
            assert result['markets_settled'] == 2
            assert result['positions_settled'] == 2
    
    def test_preview_settlement(self, app, test_event, test_market, test_participant, test_asset, test_scoring_rule):
        """Test settlement preview."""
        with app.app_context():
            # Ensure asset points to participant
            test_asset.participant_id = test_participant.id
            db.session.commit()
            
            # Create event result
            event_result = EventResult(
                event_id=test_event.id,
                participant_id=test_participant.id,
                primary_score=Decimal('25'),
                rank=1,
                status=ResultStatus.FINISHED
            )
            db.session.add(event_result)
            db.session.commit()
            
            # Preview settlement
            preview = SettlementService.preview_settlement(test_event.id)
            
            assert 'markets_previewed' in preview
            assert len(preview['previews']) > 0
            assert preview['previews'][0]['payout_per_share'] > 0

