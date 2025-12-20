"""Expected value calculators for simulation tests.

These functions calculate expected values using the same formulas
as the production code, for comparison during assertions.
"""
from decimal import Decimal


def calculate_expected_buy_cost(
    current_supply: Decimal,
    quantity: Decimal,
    a: Decimal,
    b: Decimal
) -> Decimal:
    """Calculate expected cost using bonding curve formula.

    Formula: cost = (2a/3) * [(s+Δs)^(3/2) - s^(3/2)] + b * Δs

    Args:
        current_supply: Current supply before purchase
        quantity: Number of shares to buy
        a: Bonding curve slope parameter
        b: Bonding curve baseline

    Returns:
        Expected cost
    """
    from pricing.bonding_curve import buy_cost
    return buy_cost(current_supply, quantity, a, b)


def calculate_expected_sell_payout(
    current_supply: Decimal,
    quantity: Decimal,
    a: Decimal,
    b: Decimal
) -> Decimal:
    """Calculate expected payout using bonding curve formula.

    Formula: payout = (2a/3) * [s^(3/2) - (s-Δs)^(3/2)] + b * Δs

    Args:
        current_supply: Current supply before sale
        quantity: Number of shares to sell
        a: Bonding curve slope parameter
        b: Bonding curve baseline

    Returns:
        Expected payout
    """
    from pricing.bonding_curve import sell_payout
    return sell_payout(current_supply, quantity, a, b)


def calculate_expected_avg_entry_price(
    old_shares: Decimal,
    old_avg_price: Decimal,
    new_shares_bought: Decimal,
    buy_cost: Decimal
) -> Decimal:
    """Calculate expected weighted average entry price after a buy.

    Formula: avg = (old_shares * old_avg + cost) / new_total_shares

    Args:
        old_shares: Shares held before this buy
        old_avg_price: Average entry price before this buy
        new_shares_bought: Number of new shares bought
        buy_cost: Total cost of the new shares

    Returns:
        New weighted average entry price
    """
    total_shares = old_shares + new_shares_bought
    if total_shares == Decimal('0'):
        return Decimal('0')

    total_cost = old_shares * old_avg_price + buy_cost
    return total_cost / total_shares


def calculate_expected_realized_pnl(
    shares_sold: Decimal,
    sell_payout: Decimal,
    avg_entry_price: Decimal
) -> Decimal:
    """Calculate expected realized P&L from a sale.

    Formula: realized_pnl = (sale_price - avg_entry) * shares

    Args:
        shares_sold: Number of shares sold
        sell_payout: Total payout received
        avg_entry_price: Average entry price of the position

    Returns:
        Realized profit/loss
    """
    if shares_sold == Decimal('0'):
        return Decimal('0')

    sale_price_per_share = sell_payout / shares_sold
    return (sale_price_per_share - avg_entry_price) * shares_sold


def calculate_expected_settlement_payout(
    shares: Decimal,
    primary_score: Decimal,
    max_score: Decimal,
    alpha: Decimal,
    beta: Decimal
) -> Decimal:
    """Calculate expected settlement payout.

    Formula (LINEAR_NORMALIZED): payout = shares * (alpha * (score/max) + beta)

    Args:
        shares: Number of shares held
        primary_score: Score achieved (e.g., F1 points)
        max_score: Maximum possible score (e.g., 25 for F1)
        alpha: Scoring rule alpha parameter
        beta: Scoring rule beta parameter

    Returns:
        Expected gross payout
    """
    if max_score == Decimal('0'):
        return shares * beta

    payout_per_share = alpha * (primary_score / max_score) + beta
    return shares * payout_per_share


def calculate_expected_price(
    supply: Decimal,
    a: Decimal,
    b: Decimal
) -> Decimal:
    """Calculate expected price at given supply.

    Formula: P(s) = a * sqrt(s) + b

    Args:
        supply: Current supply
        a: Bonding curve slope
        b: Bonding curve baseline

    Returns:
        Expected price per share
    """
    from pricing.bonding_curve import price
    return price(supply, a, b)


def calculate_total_pnl(
    initial_balance: Decimal,
    final_balance: Decimal,
    final_position_value: Decimal
) -> Decimal:
    """Calculate total profit/loss for a user.

    Args:
        initial_balance: Starting wallet balance
        final_balance: Ending wallet balance
        final_position_value: Market value of remaining positions

    Returns:
        Total P&L (positive = profit, negative = loss)
    """
    total_final_value = final_balance + final_position_value
    return total_final_value - initial_balance
