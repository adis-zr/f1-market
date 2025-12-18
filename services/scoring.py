"""Scoring strategies for market settlement.

This module implements the strategy pattern for different scoring formulas,
making it easy to add sport-specific scoring strategies.
"""
import math
import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from db import EventResult, ScoringRule

from db import FormulaType

logger = logging.getLogger(__name__)


class ScoringStrategy(ABC):
    """Abstract base class for scoring strategies."""

    @abstractmethod
    def compute_payout(self, event_result: 'EventResult', scoring_rule: 'ScoringRule') -> Decimal:
        """
        Compute payout per share based on event result and scoring rule.

        Args:
            event_result: EventResult instance containing the actual performance data
            scoring_rule: ScoringRule instance containing the scoring parameters

        Returns:
            Payout per share as Decimal
        """
        pass


class LinearNormalizedStrategy(ScoringStrategy):
    """
    Linear normalized scoring strategy.

    Formula: payout = alpha * (primary_score / max_score) + beta

    This is the most straightforward scoring method, providing a linear
    relationship between performance (normalized score) and payout.
    """

    def compute_payout(self, event_result: 'EventResult', scoring_rule: 'ScoringRule') -> Decimal:
        """
        Compute payout using linear normalized formula.

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

        # Normalize score to [0, 1] range
        normalized = primary_score / max_score

        # Apply linear formula
        payout = alpha * normalized + beta

        # Ensure payout is non-negative
        return max(payout, Decimal('0'))


class SigmoidStrategy(ScoringStrategy):
    """
    Sigmoid scoring strategy.

    Formula: payout = alpha * (1 / (1 + exp(-k * normalized))) + beta

    The sigmoid function creates an S-curve, which can be useful for:
    - Rewarding excellence more than mediocrity
    - Creating smooth transitions between performance levels
    - Implementing non-linear scoring that still respects bounds

    The 'k' parameter controls the steepness of the curve. Higher k values
    create steeper transitions around the midpoint.
    """

    def compute_payout(self, event_result: 'EventResult', scoring_rule: 'ScoringRule') -> Decimal:
        """
        Compute payout using sigmoid formula.

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

        # Normalize score to [0, 1] range
        normalized = primary_score / max_score

        # Get k parameter from config, default to 10
        k = scoring_rule.config_json.get('k', 10) if scoring_rule.config_json else 10

        # Apply sigmoid: 1 / (1 + exp(-k * normalized))
        sigmoid_value = Decimal(str(1 / (1 + math.exp(-k * float(normalized)))))

        # Apply alpha and beta
        payout = alpha * sigmoid_value + beta

        # Ensure payout is non-negative
        return max(payout, Decimal('0'))


class PiecewiseStrategy(ScoringStrategy):
    """
    Piecewise linear scoring strategy.

    This strategy allows defining different linear formulas for different
    performance ranges (breakpoints). This is useful for:
    - Implementing tiered reward structures (e.g., podium finishes get bonus)
    - Sport-specific scoring (e.g., F1 points: 25 for 1st, 18 for 2nd, etc.)
    - Creating custom reward curves

    Configuration example in scoring_rule.config_json:
    {
        "breakpoints": [
            {"threshold": 0, "alpha": 0.5, "beta": 0},
            {"threshold": 0.5, "alpha": 1.0, "beta": 0.1},
            {"threshold": 0.8, "alpha": 1.5, "beta": 0.2}
        ]
    }

    The strategy finds the appropriate breakpoint based on the normalized score
    and applies the corresponding alpha and beta values.
    """

    def compute_payout(self, event_result: 'EventResult', scoring_rule: 'ScoringRule') -> Decimal:
        """
        Compute payout using piecewise linear formula.

        Args:
            event_result: EventResult instance
            scoring_rule: ScoringRule instance

        Returns:
            Payout per share as Decimal
        """
        primary_score = Decimal(str(event_result.primary_score))
        max_score = Decimal(str(scoring_rule.max_score))

        if max_score == 0:
            raise ValueError("Scoring rule max_score cannot be zero")

        # Normalize score to [0, 1] range
        normalized = primary_score / max_score

        # Get breakpoints from config
        if scoring_rule.config_json and 'breakpoints' in scoring_rule.config_json:
            breakpoints = scoring_rule.config_json['breakpoints']

            # Sort breakpoints by threshold (lowest to highest)
            sorted_breakpoints = sorted(breakpoints, key=lambda x: x.get('threshold', 0))

            # Find the appropriate breakpoint
            # Use the last breakpoint where normalized >= threshold
            selected_breakpoint = sorted_breakpoints[0]  # Default to first
            for bp in sorted_breakpoints:
                if float(normalized) >= bp.get('threshold', 0):
                    selected_breakpoint = bp
                else:
                    break

            # Get alpha and beta from the selected breakpoint
            alpha = Decimal(str(selected_breakpoint.get('alpha', scoring_rule.alpha)))
            beta = Decimal(str(selected_breakpoint.get('beta', scoring_rule.beta)))
        else:
            # Fallback to linear if no breakpoints configured
            logger.warning(
                f"Piecewise strategy used for scoring rule {scoring_rule.id} "
                "but no breakpoints configured. Falling back to linear formula."
            )
            alpha = Decimal(str(scoring_rule.alpha))
            beta = Decimal(str(scoring_rule.beta))

        # Apply linear formula with selected parameters
        payout = alpha * normalized + beta

        # Ensure payout is non-negative
        return max(payout, Decimal('0'))


def get_scoring_strategy(formula_type: FormulaType) -> ScoringStrategy:
    """
    Factory function to get the appropriate scoring strategy.

    This function maps FormulaType enum values to their corresponding
    strategy implementations. This makes it easy to add new formula types
    by creating a new strategy class and adding it to the mapping.

    Args:
        formula_type: FormulaType enum value

    Returns:
        ScoringStrategy instance

    Raises:
        ValueError: If formula_type is not recognized

    Example:
        >>> from db import FormulaType
        >>> strategy = get_scoring_strategy(FormulaType.LINEAR_NORMALIZED)
        >>> payout = strategy.compute_payout(event_result, scoring_rule)
    """
    strategies = {
        FormulaType.LINEAR_NORMALIZED: LinearNormalizedStrategy(),
        FormulaType.SIGMOID: SigmoidStrategy(),
        FormulaType.PIECEWISE: PiecewiseStrategy(),
    }

    strategy = strategies.get(formula_type)
    if strategy is None:
        # Default to linear if formula type is not recognized
        logger.warning(
            f"Unknown formula type: {formula_type}. "
            f"Defaulting to LINEAR_NORMALIZED strategy."
        )
        return LinearNormalizedStrategy()

    return strategy
