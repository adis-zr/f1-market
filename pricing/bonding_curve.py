"""Bonding curve pricing functions for AMM market maker."""
from decimal import Decimal
from math import sqrt
from db import db, Position


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
    
    sqrt_s = Decimal(str(sqrt(float(s))))
    return a * sqrt_s + b


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
    
    # Handle zero supply case
    if s == 0:
        # Integral from 0 to delta_s: (2a/3) * (delta_s)^(3/2) + b * delta_s
        delta_s_float = float(delta_s)
        integral_part = Decimal(str((2 * float(a) / 3) * (delta_s_float ** 1.5)))
        baseline_part = b * delta_s
        return integral_part + baseline_part
    
    # Calculate integral part: (2a/3) * [(s+Δs)^(3/2) - s^(3/2)]
    s_float = float(s)
    s_plus_delta_float = float(s + delta_s)
    
    integral_part = Decimal(str((2 * float(a) / 3) * (s_plus_delta_float ** 1.5 - s_float ** 1.5)))
    
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
    
    # Handle case where selling all shares
    if s == delta_s:
        # Selling all shares: integral from 0 to s
        s_float = float(s)
        integral_part = Decimal(str((2 * float(a) / 3) * (s_float ** 1.5)))
        baseline_part = b * delta_s
        return integral_part + baseline_part
    
    # Calculate integral part: (2a/3) * [s^(3/2) - (s-Δs)^(3/2)]
    s_float = float(s)
    s_minus_delta_float = float(s - delta_s)
    
    integral_part = Decimal(str((2 * float(a) / 3) * (s_float ** 1.5 - s_minus_delta_float ** 1.5)))
    
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

