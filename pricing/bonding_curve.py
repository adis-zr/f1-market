"""Bonding curve pricing functions for AMM market maker."""
from decimal import Decimal, getcontext
from db import db, Position

# Set high precision for financial calculations
getcontext().prec = 50


def decimal_sqrt(n: Decimal) -> Decimal:
    """
    Calculate square root of a Decimal with high precision.
    Uses Newton-Raphson method for arbitrary precision.

    Args:
        n: Non-negative Decimal

    Returns:
        Square root as Decimal
    """
    if n < 0:
        raise ValueError("Cannot compute square root of negative number")
    if n == 0:
        return Decimal('0')

    # Initial guess using float sqrt (good enough for Newton-Raphson start)
    from math import sqrt as math_sqrt
    x = Decimal(str(math_sqrt(float(n))))

    # Newton-Raphson iterations for precision refinement
    # x_new = (x + n/x) / 2
    two = Decimal('2')
    for _ in range(10):  # 10 iterations provides very high precision
        x = (x + n / x) / two

    return x


def decimal_pow_3_2(n: Decimal) -> Decimal:
    """
    Calculate n^(3/2) = n * sqrt(n) with high precision.

    Args:
        n: Non-negative Decimal

    Returns:
        n^(3/2) as Decimal
    """
    if n < 0:
        raise ValueError("Cannot compute power of negative number")
    if n == 0:
        return Decimal('0')

    return n * decimal_sqrt(n)


def price(s: Decimal, a: Decimal, b: Decimal) -> Decimal:
    """
    Current price given supply s.

    Formula: P(s) = a * sqrt(s) + b

    Args:
        s: Current supply (total shares outstanding)
        a: Bonding curve parameter (slope)
        b: Bonding curve baseline (y-intercept)

    Returns:
        Current price per share
    """
    if s < 0:
        raise ValueError("Supply cannot be negative")
    if s == 0:
        # At zero supply, price is just the baseline
        return b

    return a * decimal_sqrt(s) + b


def buy_cost(s: Decimal, delta_s: Decimal, a: Decimal, b: Decimal) -> Decimal:
    """
    Cost to buy delta_s shares from current supply s.

    Formula: cost = (2a/3) * [(s+Δs)^(3/2) - s^(3/2)] + b * Δs

    This is the integral of the price function from s to s+Δs.

    Args:
        s: Current supply before purchase
        delta_s: Number of shares to buy
        a: Bonding curve parameter
        b: Bonding curve baseline

    Returns:
        Total cost to buy delta_s shares
    """
    if delta_s <= 0:
        raise ValueError("delta_s must be positive")
    if s < 0:
        raise ValueError("Supply cannot be negative")

    two_thirds = Decimal('2') / Decimal('3')

    # Handle zero supply case
    if s == 0:
        # Integral from 0 to delta_s: (2a/3) * (delta_s)^(3/2) + b * delta_s
        integral_part = two_thirds * a * decimal_pow_3_2(delta_s)
        baseline_part = b * delta_s
        return integral_part + baseline_part

    # Calculate integral part: (2a/3) * [(s+Δs)^(3/2) - s^(3/2)]
    s_plus_delta = s + delta_s
    integral_part = two_thirds * a * (decimal_pow_3_2(s_plus_delta) - decimal_pow_3_2(s))

    # Baseline part: b * Δs
    baseline_part = b * delta_s

    return integral_part + baseline_part


def sell_payout(s: Decimal, delta_s: Decimal, a: Decimal, b: Decimal) -> Decimal:
    """
    Payout for selling delta_s shares from current supply s.

    Formula: payout = (2a/3) * [s^(3/2) - (s-Δs)^(3/2)] + b * Δs

    This is the integral of the price function from s-Δs to s.

    Args:
        s: Current supply before sale
        delta_s: Number of shares to sell
        a: Bonding curve parameter
        b: Bonding curve baseline

    Returns:
        Total payout for selling delta_s shares
    """
    if delta_s <= 0:
        raise ValueError("delta_s must be positive")
    if s < 0:
        raise ValueError("Supply cannot be negative")
    if delta_s > s:
        raise ValueError("Cannot sell more shares than current supply")

    two_thirds = Decimal('2') / Decimal('3')

    # Handle case where selling all shares
    if s == delta_s:
        # Selling all shares: integral from 0 to s
        integral_part = two_thirds * a * decimal_pow_3_2(s)
        baseline_part = b * delta_s
        return integral_part + baseline_part

    # Calculate integral part: (2a/3) * [s^(3/2) - (s-Δs)^(3/2)]
    s_minus_delta = s - delta_s
    integral_part = two_thirds * a * (decimal_pow_3_2(s) - decimal_pow_3_2(s_minus_delta))

    # Baseline part: b * Δs
    baseline_part = b * delta_s

    return integral_part + baseline_part


def get_current_supply(market_id: int) -> Decimal:
    """
    Get current supply (total shares outstanding) for a market.
    
    Supply is the sum of all Position.shares for the market.
    
    Args:
        market_id: Market ID
    
    Returns:
        Current supply as Decimal (0 if no positions exist)
    """
    from sqlalchemy import func
    
    result = db.session.query(func.sum(Position.shares)).filter(
        Position.market_id == market_id
    ).scalar()
    
    if result is None:
        return Decimal('0')
    
    return Decimal(str(result))

