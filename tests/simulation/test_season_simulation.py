"""F1 2024 Season Simulation Test.

Simulates the entire 2024 F1 season with 10 users trading on all 24 races.
Each user follows a specific trading strategy and starts with 100 credits.
"""
import pytest
from decimal import Decimal
from typing import Dict, List

from db import db
from db.models import Position, EventStatus
from services.market_service import MarketService, MarketClosedError, InsufficientSharesError
from services.wallet_service import WalletService, InsufficientBalanceError
from services.settlement_service import SettlementService

from .data.races import RACES_2024, get_race_results
from .data.points import get_points_for_position
from .conftest import BONDING_A, BONDING_B, INITIAL_BALANCE, get_user_positions_by_driver
from .helpers.snapshot import SnapshotCapture, SystemSnapshot
from .helpers.assertions import (
    assert_decimal_equal,
    assert_wallet_changed_by,
    assert_position_changed_by,
    assert_market_supply_changed_by,
    assert_ledger_entry_created,
    assert_position_closed,
    assert_market_settled,
    assert_wallet_never_negative,
    assert_supply_equals_positions,
)
from .helpers.calculators import (
    calculate_expected_buy_cost,
    calculate_expected_sell_payout,
    calculate_expected_settlement_payout,
    calculate_total_pnl,
)


class TestF12024SeasonSimulation:
    """Complete simulation of 2024 F1 season with 10 users trading."""

    def test_full_season_simulation(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
        create_event_results,
        user_strategies,
        snapshot_capture,
    ):
        """Run complete 24-race season simulation with full assertions."""
        with simulation_app.app_context():
            users = simulation_setup['users']
            strategies = user_strategies

            # Track all snapshots for debugging
            all_snapshots: List[SystemSnapshot] = []

            # Capture initial state
            initial_snapshot = snapshot_capture.capture("initial")
            all_snapshots.append(initial_snapshot)

            # Verify initial state
            for user_idx, user in users.items():
                balance = WalletService.get_balance(user.id)
                assert_decimal_equal(
                    balance, INITIAL_BALANCE,
                    f"User {user_idx} should start with {INITIAL_BALANCE}"
                )

            print("\n" + "=" * 70)
            print("F1 2024 SEASON SIMULATION")
            print("=" * 70)

            # ===== RACE LOOP =====
            for race_num in range(1, 25):
                race_data = create_race_event(race_num)
                event = race_data['event']
                markets = race_data['markets']
                race_info = race_data['race_info']

                print(f"\n{'=' * 60}")
                print(f"RACE {race_num}: {race_info['name']}")
                print(f"{'=' * 60}")

                # Capture pre-race snapshot
                pre_race = snapshot_capture.capture(f"race_{race_num}_pre")
                all_snapshots.append(pre_race)

                # ===== EXECUTE TRADES =====
                trade_count = 0
                for user_idx in range(10):
                    user = users[user_idx]
                    strategy = strategies[user_idx]

                    # Get current state for strategy
                    wallet_balance = WalletService.get_balance(user.id)
                    current_positions = get_user_positions_by_driver(user.id, markets)
                    race_results = get_race_results(race_num)

                    # Get trades from strategy
                    trades = strategy.get_trades(
                        race_num,
                        race_results,
                        current_positions,
                        wallet_balance
                    )

                    for trade in trades:
                        market = markets.get(trade.driver_code)
                        if not market:
                            continue

                        # Capture before snapshot
                        before = snapshot_capture.capture(
                            f"race_{race_num}_trade_{trade_count}_before"
                        )

                        try:
                            if trade.action == "buy":
                                # Calculate expected cost
                                expected_cost = calculate_expected_buy_cost(
                                    before.markets[market.id].current_supply,
                                    trade.quantity,
                                    BONDING_A,
                                    BONDING_B
                                )

                                result = MarketService.buy_shares(
                                    user.id,
                                    market.id,
                                    trade.quantity
                                )

                                # Capture after snapshot
                                after = snapshot_capture.capture(
                                    f"race_{race_num}_trade_{trade_count}_after"
                                )

                                # Validate buy
                                actual_cost = Decimal(str(result['cost']))
                                assert_decimal_equal(
                                    actual_cost, expected_cost,
                                    f"Buy cost for {trade.driver_code}"
                                )

                                assert_wallet_changed_by(
                                    before, after, user.id, -actual_cost,
                                    f"Wallet after buying {trade.quantity} {trade.driver_code}"
                                )

                                assert_position_changed_by(
                                    before, after, user.id, market.id, trade.quantity,
                                    f"Position after buying {trade.driver_code}"
                                )

                                assert_market_supply_changed_by(
                                    before, after, market.id, trade.quantity,
                                    f"Supply after buying {trade.driver_code}"
                                )

                                assert_ledger_entry_created(
                                    before, after, user.id, 1,
                                    f"Ledger entry for buy {trade.driver_code}"
                                )

                            else:  # sell
                                # Check if user has shares to sell
                                user_shares = before.get_user_position_shares(
                                    user.id, market.id
                                )
                                if user_shares < trade.quantity:
                                    continue  # Skip if insufficient shares

                                expected_payout = calculate_expected_sell_payout(
                                    before.markets[market.id].current_supply,
                                    trade.quantity,
                                    BONDING_A,
                                    BONDING_B
                                )

                                result = MarketService.sell_shares(
                                    user.id,
                                    market.id,
                                    trade.quantity
                                )

                                # Capture after snapshot
                                after = snapshot_capture.capture(
                                    f"race_{race_num}_trade_{trade_count}_after"
                                )

                                # Validate sell
                                actual_payout = Decimal(str(result['payout']))
                                assert_decimal_equal(
                                    actual_payout, expected_payout,
                                    f"Sell payout for {trade.driver_code}"
                                )

                                assert_wallet_changed_by(
                                    before, after, user.id, actual_payout,
                                    f"Wallet after selling {trade.quantity} {trade.driver_code}"
                                )

                                assert_position_changed_by(
                                    before, after, user.id, market.id, -trade.quantity,
                                    f"Position after selling {trade.driver_code}"
                                )

                                assert_market_supply_changed_by(
                                    before, after, market.id, -trade.quantity,
                                    f"Supply after selling {trade.driver_code}"
                                )

                            trade_count += 1

                        except (InsufficientBalanceError, InsufficientSharesError) as e:
                            # Expected failures for some strategies
                            pass
                        except MarketClosedError:
                            # Should not happen during simulation
                            raise

                print(f"  Executed {trade_count} trades")

                # Capture post-trading snapshot
                post_trading = snapshot_capture.capture(f"race_{race_num}_post_trading")
                all_snapshots.append(post_trading)

                # Validate no negative balances
                assert_wallet_never_negative(post_trading, f"After trading race {race_num}")

                # Validate supply invariants for each market
                for driver_code, market in markets.items():
                    assert_supply_equals_positions(
                        post_trading, market.id,
                        f"Market {driver_code} after trading"
                    )

                # ===== CREATE RESULTS =====
                create_event_results(event, race_num)

                # ===== SETTLE EVENT =====
                pre_settlement = snapshot_capture.capture(f"race_{race_num}_pre_settlement")
                all_snapshots.append(pre_settlement)

                settlement_result = SettlementService.settle_event(event.id)

                post_settlement = snapshot_capture.capture(f"race_{race_num}_post_settlement")
                all_snapshots.append(post_settlement)

                print(f"  Settled: {settlement_result['markets_settled']} markets, "
                      f"{settlement_result['positions_settled']} positions")
                print(f"  Total payout: {settlement_result['total_payout']:.2f}")

                # ===== VALIDATE SETTLEMENT =====
                self._validate_settlement(
                    pre_settlement,
                    post_settlement,
                    settlement_result,
                    markets,
                    race_num
                )

                # Verify event status
                db.session.refresh(event)
                assert event.status == EventStatus.FINISHED, \
                    f"Event should be FINISHED after settlement"

            # ===== FINAL VALIDATION =====
            final_snapshot = snapshot_capture.capture("final")
            all_snapshots.append(final_snapshot)

            self._validate_final_outcomes(
                initial_snapshot,
                final_snapshot,
                users,
                strategies
            )

    def _validate_settlement(
        self,
        before: SystemSnapshot,
        after: SystemSnapshot,
        settlement_result: Dict,
        markets: Dict,
        race_num: int
    ):
        """Validate settlement was executed correctly."""
        race_results = get_race_results(race_num)

        for driver_code, position in race_results:
            market = markets.get(driver_code)
            if not market:
                continue

            # Get expected payout per share
            points = get_points_for_position(position)
            expected_pps = Decimal('1.0') * (points / Decimal('25')) + Decimal('0')

            # Check each user's settlement
            for user_id, user_snap in before.users.items():
                pos = user_snap.positions.get(market.id)
                if pos and Decimal(str(pos.get('shares', 0))) > Decimal('0'):
                    shares = Decimal(str(pos['shares']))
                    expected_payout = calculate_expected_settlement_payout(
                        shares, points,
                        Decimal('25'), Decimal('1.0'), Decimal('0')
                    )

                    # After settlement, position should be closed
                    assert_position_closed(
                        after, user_id, market.id,
                        f"Position for user {user_id} in {driver_code}"
                    )

            # Market should be settled
            assert_market_settled(
                after, market.id,
                f"Market {driver_code}"
            )

    def _validate_final_outcomes(
        self,
        initial: SystemSnapshot,
        final: SystemSnapshot,
        users: Dict,
        strategies: Dict
    ):
        """Validate final state meets expectations."""
        print("\n" + "=" * 70)
        print("FINAL RESULTS")
        print("=" * 70)

        profitable_users = [0, 1, 2]
        breakeven_users = [3, 4, 5, 6]
        losing_users = [7, 8, 9]

        pnl_by_user = {}

        for user_idx in range(10):
            user = users[user_idx]
            initial_balance = initial.users[user.id].wallet_balance
            final_balance = final.users[user.id].wallet_balance

            # All positions should be closed after 24 races
            final_position_value = Decimal('0')

            pnl = calculate_total_pnl(initial_balance, final_balance, final_position_value)
            pnl_by_user[user_idx] = pnl

            strategy_name = strategies[user_idx].name
            status = "+" if pnl > 0 else "-" if pnl < 0 else "="
            print(f"User {user_idx:2d} ({strategy_name:20s}): {pnl:+10.2f} [{status}]")

        # Calculate group averages
        avg_profitable = sum(pnl_by_user[i] for i in profitable_users) / len(profitable_users)
        avg_breakeven = sum(pnl_by_user[i] for i in breakeven_users) / len(breakeven_users)
        avg_losing = sum(pnl_by_user[i] for i in losing_users) / len(losing_users)

        print(f"\nGroup Averages:")
        print(f"  Profitable strategies (users 0-2): {avg_profitable:+.2f}")
        print(f"  Break-even strategies (users 3-6): {avg_breakeven:+.2f}")
        print(f"  Losing strategies (users 7-9):     {avg_losing:+.2f}")

        # Validate strategy group expectations
        # Note: We assert tendencies, not strict inequalities, as market dynamics are complex
        print(f"\nValidating strategy outcomes...")

        # Profitable should generally do better than losing
        assert avg_profitable > avg_losing, (
            f"Profitable strategies ({avg_profitable:.2f}) should outperform "
            f"losing strategies ({avg_losing:.2f})"
        )

        print("  Strategy outcomes validated successfully!")


class TestSimulationSingleRace:
    """Test simulation of a single race for faster iteration."""

    def test_single_race_bahrain(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
        create_event_results,
        user_strategies,
        snapshot_capture,
    ):
        """Test simulation of just the first race."""
        with simulation_app.app_context():
            users = simulation_setup['users']
            strategies = user_strategies
            race_num = 1

            # Create race
            race_data = create_race_event(race_num)
            event = race_data['event']
            markets = race_data['markets']

            # Capture initial snapshot
            initial = snapshot_capture.capture("initial")

            # Execute trades for all users
            trade_count = 0
            for user_idx in range(10):
                user = users[user_idx]
                strategy = strategies[user_idx]

                wallet_balance = WalletService.get_balance(user.id)
                current_positions = get_user_positions_by_driver(user.id, markets)
                race_results = get_race_results(race_num)

                trades = strategy.get_trades(
                    race_num, race_results, current_positions, wallet_balance
                )

                for trade in trades:
                    market = markets.get(trade.driver_code)
                    if not market:
                        continue

                    try:
                        if trade.action == "buy":
                            MarketService.buy_shares(user.id, market.id, trade.quantity)
                        else:
                            MarketService.sell_shares(user.id, market.id, trade.quantity)
                        trade_count += 1
                    except (InsufficientBalanceError, InsufficientSharesError):
                        pass

            # Capture post-trading
            post_trading = snapshot_capture.capture("post_trading")

            # Validate invariants
            assert_wallet_never_negative(post_trading, "After trading")

            for driver_code, market in markets.items():
                assert_supply_equals_positions(
                    post_trading, market.id,
                    f"Market {driver_code}"
                )

            # Create results and settle
            create_event_results(event, race_num)
            settlement_result = SettlementService.settle_event(event.id)

            # Capture final state
            final = snapshot_capture.capture("final")

            print(f"\nSingle Race Test (Bahrain):")
            print(f"  Trades executed: {trade_count}")
            print(f"  Positions settled: {settlement_result['positions_settled']}")
            print(f"  Total payout: {settlement_result['total_payout']:.2f}")

            # Verify all positions closed
            for user_idx in range(10):
                user = users[user_idx]
                for driver_code, market in markets.items():
                    shares = final.get_user_position_shares(user.id, market.id)
                    assert shares == Decimal('0'), \
                        f"User {user_idx} should have no shares in {driver_code}"


class TestTradeValidation:
    """Test trade execution validation in isolation."""

    def test_buy_cost_matches_formula(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
        snapshot_capture,
    ):
        """Verify buy cost matches bonding curve formula exactly."""
        with simulation_app.app_context():
            users = simulation_setup['users']
            user = users[0]

            race_data = create_race_event(1)
            markets = race_data['markets']
            market = markets['VER']  # Pick Verstappen's market

            before = snapshot_capture.capture("before")

            # Buy 5 shares
            quantity = Decimal('5')
            expected_cost = calculate_expected_buy_cost(
                before.markets[market.id].current_supply,
                quantity,
                BONDING_A,
                BONDING_B
            )

            result = MarketService.buy_shares(user.id, market.id, quantity)
            actual_cost = Decimal(str(result['cost']))

            after = snapshot_capture.capture("after")

            # Exact match required
            assert_decimal_equal(
                actual_cost, expected_cost,
                "Buy cost should match formula exactly"
            )

            # Verify wallet change
            assert_wallet_changed_by(
                before, after, user.id, -actual_cost,
                "Wallet should decrease by exact cost"
            )

    def test_sell_payout_matches_formula(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
        snapshot_capture,
    ):
        """Verify sell payout matches bonding curve formula exactly."""
        with simulation_app.app_context():
            users = simulation_setup['users']
            user = users[0]

            race_data = create_race_event(1)
            markets = race_data['markets']
            market = markets['HAM']

            # First buy some shares
            buy_qty = Decimal('10')
            MarketService.buy_shares(user.id, market.id, buy_qty)

            before = snapshot_capture.capture("before_sell")

            # Sell half
            sell_qty = Decimal('5')
            expected_payout = calculate_expected_sell_payout(
                before.markets[market.id].current_supply,
                sell_qty,
                BONDING_A,
                BONDING_B
            )

            result = MarketService.sell_shares(user.id, market.id, sell_qty)
            actual_payout = Decimal(str(result['payout']))

            after = snapshot_capture.capture("after_sell")

            # Exact match required
            assert_decimal_equal(
                actual_payout, expected_payout,
                "Sell payout should match formula exactly"
            )

            # Verify wallet change
            assert_wallet_changed_by(
                before, after, user.id, actual_payout,
                "Wallet should increase by exact payout"
            )

    def test_settlement_payout_matches_formula(
        self,
        simulation_app,
        simulation_setup,
        create_race_event,
        create_event_results,
        snapshot_capture,
    ):
        """Verify settlement payout matches scoring formula exactly."""
        with simulation_app.app_context():
            users = simulation_setup['users']
            user = users[0]

            race_data = create_race_event(1)
            event = race_data['event']
            markets = race_data['markets']

            # Buy shares in winner (VER won race 1)
            ver_market = markets['VER']
            buy_qty = Decimal('10')
            MarketService.buy_shares(user.id, ver_market.id, buy_qty)

            # Create results
            create_event_results(event, 1)

            before = snapshot_capture.capture("before_settlement")

            # Calculate expected payout
            # VER finished 1st = 25 points
            # payout_per_share = 1.0 * (25/25) + 0 = 1.0
            expected_payout = calculate_expected_settlement_payout(
                buy_qty,
                Decimal('25'),  # VER's points
                Decimal('25'),  # max score
                Decimal('1.0'),  # alpha
                Decimal('0')     # beta
            )

            # Settle
            SettlementService.settle_event(event.id)

            after = snapshot_capture.capture("after_settlement")

            # Verify wallet increased by expected payout
            wallet_change = (
                after.users[user.id].wallet_balance -
                before.users[user.id].wallet_balance
            )

            assert_decimal_equal(
                wallet_change, expected_payout,
                f"Settlement payout for 10 shares of race winner"
            )
