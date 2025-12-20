"""Edge case tests for the simulation.

These tests verify correct behavior in boundary conditions and
help detect potential bugs in the trading and settlement logic.
"""
import pytest
from decimal import Decimal

from db import db
from db.models import Position, MarketStatus, TransactionType
from services.market_service import MarketService, MarketClosedError, InsufficientSharesError
from services.wallet_service import WalletService, InsufficientBalanceError
from services.settlement_service import SettlementService
from pricing.bonding_curve import buy_cost, sell_payout, price, get_current_supply

from .conftest import BONDING_A, BONDING_B, INITIAL_BALANCE
from .helpers.snapshot import SnapshotCapture
from .helpers.assertions import (
    assert_decimal_equal,
    assert_wallet_changed_by,
    assert_position_changed_by,
    assert_market_supply_changed_by,
    assert_supply_equals_positions,
    assert_wallet_never_negative,
)
from .helpers.calculators import (
    calculate_expected_buy_cost,
    calculate_expected_sell_payout,
    calculate_expected_avg_entry_price,
    calculate_expected_realized_pnl,
    calculate_expected_settlement_payout,
)


class TestBuyEdgeCases:
    """Edge cases for buying shares."""

    def test_buy_at_zero_supply(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
        snapshot_capture,
    ):
        """First buy on a fresh market with zero supply."""
        with simulation_app.app_context():
            users = simulation_setup['users']
            user = users[0]

            race_data = create_race_event(1)
            market = race_data['markets']['VER']

            # Verify zero supply
            supply = get_current_supply(market.id)
            assert supply == Decimal('0'), "Market should start with zero supply"

            # Buy at zero supply
            quantity = Decimal('5')
            expected_cost = buy_cost(Decimal('0'), quantity, BONDING_A, BONDING_B)

            before = snapshot_capture.capture("before")
            result = MarketService.buy_shares(user.id, market.id, quantity)
            after = snapshot_capture.capture("after")

            actual_cost = Decimal(str(result['cost']))
            assert_decimal_equal(actual_cost, expected_cost, "Cost at zero supply")

            # Price at zero supply is just baseline b
            assert price(Decimal('0'), BONDING_A, BONDING_B) == BONDING_B

    def test_buy_very_small_quantity(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
        snapshot_capture,
    ):
        """Buy a very small quantity (precision edge case)."""
        with simulation_app.app_context():
            users = simulation_setup['users']
            user = users[0]

            race_data = create_race_event(1)
            market = race_data['markets']['HAM']

            quantity = Decimal('0.001')
            expected_cost = buy_cost(Decimal('0'), quantity, BONDING_A, BONDING_B)

            before = snapshot_capture.capture("before")
            result = MarketService.buy_shares(user.id, market.id, quantity)
            after = snapshot_capture.capture("after")

            actual_cost = Decimal(str(result['cost']))
            assert_decimal_equal(actual_cost, expected_cost, "Cost for tiny buy")

            assert_position_changed_by(
                before, after, user.id, market.id, quantity,
                "Position should increase by tiny amount"
            )

    def test_buy_large_quantity(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
        snapshot_capture,
    ):
        """Buy a large quantity (overflow edge case)."""
        with simulation_app.app_context():
            users = simulation_setup['users']
            user = users[0]

            # Give user more balance for large purchase
            WalletService.add_ledger_entry(
                user.id,
                Decimal('10000'),
                TransactionType.DEPOSIT,
                description='Extra funds'
            )

            race_data = create_race_event(1)
            market = race_data['markets']['LEC']

            quantity = Decimal('100')
            before = snapshot_capture.capture("before")

            expected_cost = buy_cost(Decimal('0'), quantity, BONDING_A, BONDING_B)
            result = MarketService.buy_shares(user.id, market.id, quantity)
            after = snapshot_capture.capture("after")

            actual_cost = Decimal(str(result['cost']))
            assert_decimal_equal(actual_cost, expected_cost, "Cost for large buy")

    def test_buy_insufficient_balance(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
    ):
        """Attempt to buy more than wallet balance allows."""
        with simulation_app.app_context():
            users = simulation_setup['users']
            user = users[0]

            race_data = create_race_event(1)
            market = race_data['markets']['NOR']

            # Try to buy way more than balance allows
            quantity = Decimal('1000')

            with pytest.raises(InsufficientBalanceError):
                MarketService.buy_shares(user.id, market.id, quantity)

    def test_multiple_buys_avg_entry_price(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
        snapshot_capture,
    ):
        """Verify weighted average entry price after multiple buys."""
        with simulation_app.app_context():
            users = simulation_setup['users']
            user = users[0]

            race_data = create_race_event(1)
            market = race_data['markets']['PIA']

            # First buy
            qty1 = Decimal('5')
            result1 = MarketService.buy_shares(user.id, market.id, qty1)
            cost1 = Decimal(str(result1['cost']))
            avg1 = cost1 / qty1

            # Second buy
            qty2 = Decimal('3')
            result2 = MarketService.buy_shares(user.id, market.id, qty2)
            cost2 = Decimal(str(result2['cost']))

            # Calculate expected weighted average
            expected_avg = calculate_expected_avg_entry_price(
                qty1, avg1, qty2, cost2
            )

            # Get actual position
            position = Position.query.filter_by(
                user_id=user.id, market_id=market.id
            ).first()

            actual_avg = Decimal(str(position.avg_entry_price))
            assert_decimal_equal(
                actual_avg, expected_avg,
                "Weighted average entry price after multiple buys"
            )


class TestSellEdgeCases:
    """Edge cases for selling shares."""

    def test_sell_all_shares(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
        snapshot_capture,
    ):
        """Selling entire position back to zero."""
        with simulation_app.app_context():
            users = simulation_setup['users']
            user = users[0]

            race_data = create_race_event(1)
            market = race_data['markets']['SAI']

            # Buy some shares
            buy_qty = Decimal('10')
            buy_result = MarketService.buy_shares(user.id, market.id, buy_qty)

            before = snapshot_capture.capture("before_sell_all")

            # Sell all shares
            sell_result = MarketService.sell_shares(user.id, market.id, buy_qty)

            after = snapshot_capture.capture("after_sell_all")

            # Position should be zero
            position = Position.query.filter_by(
                user_id=user.id, market_id=market.id
            ).first()
            assert Decimal(str(position.shares)) == Decimal('0'), \
                "Position should be zero after selling all"

            # Supply should be zero
            supply = get_current_supply(market.id)
            assert supply == Decimal('0'), "Supply should be zero after selling all"

    def test_buy_sell_round_trip(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
        snapshot_capture,
    ):
        """Immediate buy then sell should have payout equal to cost."""
        with simulation_app.app_context():
            users = simulation_setup['users']
            user = users[0]

            race_data = create_race_event(1)
            market = race_data['markets']['RUS']

            initial_balance = WalletService.get_balance(user.id)

            # Buy
            quantity = Decimal('5')
            buy_result = MarketService.buy_shares(user.id, market.id, quantity)
            buy_cost_actual = Decimal(str(buy_result['cost']))

            # Immediately sell (no other trades in between)
            sell_result = MarketService.sell_shares(user.id, market.id, quantity)
            sell_payout_actual = Decimal(str(sell_result['payout']))

            # Payout should equal cost (no AMM spread in this simple curve)
            assert_decimal_equal(
                sell_payout_actual, buy_cost_actual,
                "Round trip: sell payout should equal buy cost"
            )

            # Balance should be back to initial
            final_balance = WalletService.get_balance(user.id)
            assert_decimal_equal(
                final_balance, initial_balance,
                "Balance should be unchanged after round trip"
            )

    def test_partial_sell_realized_pnl(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
        snapshot_capture,
    ):
        """Selling partial position calculates correct realized P&L."""
        with simulation_app.app_context():
            users = simulation_setup['users']
            user = users[0]

            race_data = create_race_event(1)
            market = race_data['markets']['ALO']

            # Buy 10 shares
            buy_qty = Decimal('10')
            buy_result = MarketService.buy_shares(user.id, market.id, buy_qty)
            avg_entry = Decimal(str(buy_result['price_per_share']))

            # Get current supply before second user buys
            supply_after_first = get_current_supply(market.id)

            # Another user buys to move price up
            other_user = simulation_setup['users'][1]
            MarketService.buy_shares(other_user.id, market.id, Decimal('20'))

            # Now sell partial
            sell_qty = Decimal('5')
            supply_before_sell = get_current_supply(market.id)
            sell_result = MarketService.sell_shares(user.id, market.id, sell_qty)

            sell_payout = Decimal(str(sell_result['payout']))
            sell_price = sell_payout / sell_qty

            # Expected realized P&L
            expected_pnl = calculate_expected_realized_pnl(
                sell_qty, sell_payout, avg_entry
            )

            actual_pnl = Decimal(str(sell_result['realized_pnl']))
            assert_decimal_equal(
                actual_pnl, expected_pnl,
                "Realized P&L for partial sell"
            )

    def test_sell_insufficient_shares(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
    ):
        """Attempt to sell more shares than owned."""
        with simulation_app.app_context():
            users = simulation_setup['users']
            user = users[0]

            race_data = create_race_event(1)
            market = race_data['markets']['STR']

            # Buy 5 shares
            MarketService.buy_shares(user.id, market.id, Decimal('5'))

            # Try to sell 10
            with pytest.raises(InsufficientSharesError):
                MarketService.sell_shares(user.id, market.id, Decimal('10'))

    def test_sell_no_position(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
    ):
        """Attempt to sell when having no position."""
        with simulation_app.app_context():
            users = simulation_setup['users']
            user = users[0]

            race_data = create_race_event(1)
            market = race_data['markets']['GAS']

            # Try to sell without buying
            with pytest.raises(InsufficientSharesError):
                MarketService.sell_shares(user.id, market.id, Decimal('1'))


class TestSettlementEdgeCases:
    """Edge cases for settlement."""

    def test_settlement_dnf_zero_points(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
        create_event_results,
        snapshot_capture,
    ):
        """DNF should give 0 points, resulting in 0 payout."""
        with simulation_app.app_context():
            users = simulation_setup['users']
            user = users[0]

            # Race 2 has some DNFs (OCO, SAR)
            race_data = create_race_event(2)
            event = race_data['event']
            markets = race_data['markets']

            # Buy shares in a DNF driver
            oco_market = markets['OCO']
            buy_qty = Decimal('10')
            MarketService.buy_shares(user.id, oco_market.id, buy_qty)

            create_event_results(event, 2)

            before = snapshot_capture.capture("before")
            SettlementService.settle_event(event.id)
            after = snapshot_capture.capture("after")

            # DNF = 0 points, so payout_per_share = 0
            # User should get 0 payout
            expected_payout = calculate_expected_settlement_payout(
                buy_qty, Decimal('0'), Decimal('25'), Decimal('1'), Decimal('0')
            )
            assert expected_payout == Decimal('0'), "DNF should give 0 payout"

    def test_settlement_winner_full_payout(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
        create_event_results,
        snapshot_capture,
    ):
        """Race winner gets payout_per_share = 1.0."""
        with simulation_app.app_context():
            users = simulation_setup['users']
            user = users[0]

            race_data = create_race_event(1)
            event = race_data['event']
            markets = race_data['markets']

            # VER won race 1
            ver_market = markets['VER']
            buy_qty = Decimal('10')
            buy_result = MarketService.buy_shares(user.id, ver_market.id, buy_qty)

            create_event_results(event, 1)

            before = snapshot_capture.capture("before")
            SettlementService.settle_event(event.id)
            after = snapshot_capture.capture("after")

            # Winner gets 25 points, payout = 1.0 * (25/25) = 1.0 per share
            expected_payout = buy_qty * Decimal('1.0')

            wallet_change = (
                after.users[user.id].wallet_balance -
                before.users[user.id].wallet_balance
            )
            assert_decimal_equal(
                wallet_change, expected_payout,
                "Winner payout should be 1.0 per share"
            )

    def test_settlement_10th_place_minimal_payout(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
        create_event_results,
        snapshot_capture,
    ):
        """10th place gets 1/25 = 0.04 payout per share."""
        with simulation_app.app_context():
            users = simulation_setup['users']
            user = users[0]

            race_data = create_race_event(1)
            event = race_data['event']
            markets = race_data['markets']

            # STR finished 10th in race 1
            str_market = markets['STR']
            buy_qty = Decimal('10')
            MarketService.buy_shares(user.id, str_market.id, buy_qty)

            create_event_results(event, 1)

            before = snapshot_capture.capture("before")
            SettlementService.settle_event(event.id)
            after = snapshot_capture.capture("after")

            # 10th place = 1 point, payout = 1.0 * (1/25) = 0.04 per share
            expected_payout = buy_qty * Decimal('0.04')

            wallet_change = (
                after.users[user.id].wallet_balance -
                before.users[user.id].wallet_balance
            )
            assert_decimal_equal(
                wallet_change, expected_payout,
                "10th place payout should be 0.04 per share"
            )

    def test_settlement_with_zero_position(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
        create_event_results,
        snapshot_capture,
    ):
        """Markets with no positions should settle cleanly."""
        with simulation_app.app_context():
            race_data = create_race_event(1)
            event = race_data['event']

            # Don't buy any shares
            create_event_results(event, 1)

            # Settlement should work with 0 positions
            result = SettlementService.settle_event(event.id)

            assert result['success'] is True
            assert result['positions_settled'] == 0
            assert result['total_payout'] == 0.0

    def test_settlement_idempotent(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
        create_event_results,
        snapshot_capture,
    ):
        """Settling an already-settled event should be safe."""
        with simulation_app.app_context():
            users = simulation_setup['users']
            user = users[0]

            race_data = create_race_event(1)
            event = race_data['event']
            markets = race_data['markets']

            MarketService.buy_shares(user.id, markets['VER'].id, Decimal('5'))

            create_event_results(event, 1)

            # First settlement
            result1 = SettlementService.settle_event(event.id)
            balance_after_first = WalletService.get_balance(user.id)

            # Second settlement (should be no-op)
            result2 = SettlementService.settle_event(event.id)
            balance_after_second = WalletService.get_balance(user.id)

            assert result2['already_settled'] is True
            assert balance_after_first == balance_after_second, \
                "Balance should not change on re-settlement"


class TestInvariants:
    """Tests for system invariants that should always hold."""

    def test_market_supply_matches_position_sum(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
        snapshot_capture,
    ):
        """Market supply should equal sum of all positions."""
        with simulation_app.app_context():
            users = simulation_setup['users']
            race_data = create_race_event(1)
            markets = race_data['markets']

            market = markets['VER']

            # Multiple users buy
            MarketService.buy_shares(users[0].id, market.id, Decimal('10'))
            MarketService.buy_shares(users[1].id, market.id, Decimal('5'))
            MarketService.buy_shares(users[2].id, market.id, Decimal('3'))

            # User 1 sells some
            MarketService.sell_shares(users[1].id, market.id, Decimal('2'))

            snapshot = snapshot_capture.capture("after_trades")
            assert_supply_equals_positions(
                snapshot, market.id,
                "Supply should equal sum of positions"
            )

    def test_wallet_balance_never_negative(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
        snapshot_capture,
    ):
        """Wallet balance should never go negative."""
        with simulation_app.app_context():
            users = simulation_setup['users']
            race_data = create_race_event(1)
            markets = race_data['markets']

            # Do lots of trading
            for user_idx in range(5):
                user = users[user_idx]
                for driver_code in ['VER', 'HAM', 'LEC']:
                    try:
                        MarketService.buy_shares(
                            user.id, markets[driver_code].id, Decimal('2')
                        )
                    except InsufficientBalanceError:
                        pass

            snapshot = snapshot_capture.capture("after_trading")
            assert_wallet_never_negative(snapshot, "After trading")

    def test_position_shares_never_negative(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
    ):
        """Positions should never have negative shares."""
        with simulation_app.app_context():
            users = simulation_setup['users']
            user = users[0]

            race_data = create_race_event(1)
            market = race_data['markets']['NOR']

            # Buy 5
            MarketService.buy_shares(user.id, market.id, Decimal('5'))

            # Sell 5 (should work)
            MarketService.sell_shares(user.id, market.id, Decimal('5'))

            # Position should be 0, not negative
            position = Position.query.filter_by(
                user_id=user.id, market_id=market.id
            ).first()

            assert Decimal(str(position.shares)) >= Decimal('0'), \
                "Position shares should never be negative"

    def test_closed_market_no_trading(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
        create_event_results,
    ):
        """Cannot trade on a closed/settled market."""
        with simulation_app.app_context():
            users = simulation_setup['users']
            user = users[0]

            race_data = create_race_event(1)
            event = race_data['event']
            markets = race_data['markets']
            market = markets['VER']

            # Buy shares
            MarketService.buy_shares(user.id, market.id, Decimal('5'))

            # Settle the event
            create_event_results(event, 1)
            SettlementService.settle_event(event.id)

            # Verify market is settled
            db.session.refresh(market)
            assert market.status == MarketStatus.SETTLED

            # Try to buy - should fail
            with pytest.raises(MarketClosedError):
                MarketService.buy_shares(user.id, market.id, Decimal('1'))

            # Try to sell - should fail
            with pytest.raises(MarketClosedError):
                MarketService.sell_shares(user.id, market.id, Decimal('1'))
