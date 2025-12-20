"""Assertion helpers for simulation tests.

Provides detailed assertion functions with clear error messages
for validating state changes during simulation.
"""
from decimal import Decimal
from typing import Optional

from .snapshot import SystemSnapshot

# Tolerance for decimal comparisons (8 decimal places)
TOLERANCE = Decimal('0.00000001')


def assert_decimal_equal(
    actual: Decimal,
    expected: Decimal,
    msg: str = "",
    tolerance: Decimal = TOLERANCE
):
    """Assert two decimals are equal within tolerance.

    Args:
        actual: Actual value
        expected: Expected value
        msg: Additional context message
        tolerance: Maximum allowed difference

    Raises:
        AssertionError: If values differ by more than tolerance
    """
    diff = abs(actual - expected)
    assert diff <= tolerance, (
        f"{msg}: expected {expected}, got {actual} (diff: {diff})"
    )


def assert_wallet_changed_by(
    before: SystemSnapshot,
    after: SystemSnapshot,
    user_id: int,
    expected_change: Decimal,
    msg: str = ""
):
    """Assert wallet balance changed by expected amount.

    Args:
        before: Snapshot before operation
        after: Snapshot after operation
        user_id: User to check
        expected_change: Expected balance change (negative for debits)
        msg: Additional context

    Raises:
        AssertionError: If balance change doesn't match
    """
    before_balance = before.users[user_id].wallet_balance
    after_balance = after.users[user_id].wallet_balance
    actual_change = after_balance - before_balance

    assert_decimal_equal(
        actual_change,
        expected_change,
        f"Wallet change for user {user_id}. {msg}"
    )


def assert_position_changed_by(
    before: SystemSnapshot,
    after: SystemSnapshot,
    user_id: int,
    market_id: int,
    expected_shares_change: Decimal,
    msg: str = ""
):
    """Assert position shares changed by expected amount.

    Args:
        before: Snapshot before operation
        after: Snapshot after operation
        user_id: User to check
        market_id: Market to check
        expected_shares_change: Expected shares change
        msg: Additional context

    Raises:
        AssertionError: If shares change doesn't match
    """
    before_shares = before.get_user_position_shares(user_id, market_id)
    after_shares = after.get_user_position_shares(user_id, market_id)
    actual_change = after_shares - before_shares

    assert_decimal_equal(
        actual_change,
        expected_shares_change,
        f"Position change for user {user_id} in market {market_id}. {msg}"
    )


def assert_market_supply_changed_by(
    before: SystemSnapshot,
    after: SystemSnapshot,
    market_id: int,
    expected_change: Decimal,
    msg: str = ""
):
    """Assert market supply changed by expected amount.

    Args:
        before: Snapshot before operation
        after: Snapshot after operation
        market_id: Market to check
        expected_change: Expected supply change
        msg: Additional context

    Raises:
        AssertionError: If supply change doesn't match
    """
    before_supply = before.markets[market_id].current_supply
    after_supply = after.markets[market_id].current_supply
    actual_change = after_supply - before_supply

    assert_decimal_equal(
        actual_change,
        expected_change,
        f"Supply change for market {market_id}. {msg}"
    )


def assert_ledger_entry_created(
    before: SystemSnapshot,
    after: SystemSnapshot,
    user_id: int,
    expected_new_entries: int = 1,
    msg: str = ""
):
    """Assert new ledger entries were created.

    Args:
        before: Snapshot before operation
        after: Snapshot after operation
        user_id: User to check
        expected_new_entries: Number of new entries expected
        msg: Additional context

    Raises:
        AssertionError: If entry count doesn't match
    """
    before_count = before.users[user_id].ledger_count
    after_count = after.users[user_id].ledger_count
    actual_new = after_count - before_count

    assert actual_new == expected_new_entries, (
        f"Expected {expected_new_entries} new ledger entries for user {user_id}, "
        f"got {actual_new}. {msg}"
    )


def assert_position_closed(
    after: SystemSnapshot,
    user_id: int,
    market_id: int,
    msg: str = ""
):
    """Assert position has zero shares (closed).

    Args:
        after: Snapshot after settlement
        user_id: User to check
        market_id: Market to check
        msg: Additional context

    Raises:
        AssertionError: If position not closed
    """
    shares = after.get_user_position_shares(user_id, market_id)
    assert shares == Decimal('0'), (
        f"Position for user {user_id} in market {market_id} should be closed, "
        f"but has {shares} shares. {msg}"
    )


def assert_market_settled(
    after: SystemSnapshot,
    market_id: int,
    msg: str = ""
):
    """Assert market status is SETTLED.

    Args:
        after: Snapshot after settlement
        market_id: Market to check
        msg: Additional context

    Raises:
        AssertionError: If market not settled
    """
    status = after.markets[market_id].status
    assert status == "settled", (
        f"Market {market_id} should be settled, but status is {status}. {msg}"
    )


def assert_wallet_never_negative(
    snapshot: SystemSnapshot,
    msg: str = ""
):
    """Assert no user has negative wallet balance.

    Args:
        snapshot: Current state snapshot
        msg: Additional context

    Raises:
        AssertionError: If any balance is negative
    """
    for user_id, user in snapshot.users.items():
        assert user.wallet_balance >= Decimal('0'), (
            f"User {user_id} has negative balance: {user.wallet_balance}. {msg}"
        )


def assert_supply_equals_positions(
    snapshot: SystemSnapshot,
    market_id: int,
    msg: str = ""
):
    """Assert market supply equals sum of all positions.

    Args:
        snapshot: Current state snapshot
        market_id: Market to check
        msg: Additional context

    Raises:
        AssertionError: If supply doesn't match positions
    """
    market_supply = snapshot.markets[market_id].current_supply

    total_position_shares = Decimal('0')
    for user in snapshot.users.values():
        pos = user.positions.get(market_id, {})
        total_position_shares += Decimal(str(pos.get('shares', 0)))

    assert_decimal_equal(
        market_supply,
        total_position_shares,
        f"Market {market_id} supply vs position sum. {msg}"
    )
