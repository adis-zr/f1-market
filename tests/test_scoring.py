"""Tests for scoring strategies."""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock
from db import db, FormulaType
from services.scoring import (
    LinearNormalizedStrategy,
    SigmoidStrategy,
    PiecewiseStrategy,
    get_scoring_strategy,
)


class TestLinearNormalizedStrategy:
    """Tests for LinearNormalizedStrategy."""

    def test_compute_payout_max_score(self, app):
        """Test payout when score equals max_score."""
        with app.app_context():
            strategy = LinearNormalizedStrategy()

            # Mock event_result and scoring_rule
            event_result = MagicMock()
            event_result.primary_score = Decimal('25')

            scoring_rule = MagicMock()
            scoring_rule.max_score = Decimal('25')
            scoring_rule.alpha = Decimal('1.0')
            scoring_rule.beta = Decimal('0.0')

            payout = strategy.compute_payout(event_result, scoring_rule)

            # normalized = 25/25 = 1.0, payout = 1.0 * 1.0 + 0.0 = 1.0
            assert payout == Decimal('1.0')

    def test_compute_payout_zero_score(self, app):
        """Test payout when score is zero."""
        with app.app_context():
            strategy = LinearNormalizedStrategy()

            event_result = MagicMock()
            event_result.primary_score = Decimal('0')

            scoring_rule = MagicMock()
            scoring_rule.max_score = Decimal('25')
            scoring_rule.alpha = Decimal('1.0')
            scoring_rule.beta = Decimal('0.0')

            payout = strategy.compute_payout(event_result, scoring_rule)

            # normalized = 0/25 = 0.0, payout = 1.0 * 0.0 + 0.0 = 0.0
            assert payout == Decimal('0')

    def test_compute_payout_partial_score(self, app):
        """Test payout with partial score."""
        with app.app_context():
            strategy = LinearNormalizedStrategy()

            event_result = MagicMock()
            event_result.primary_score = Decimal('12.5')

            scoring_rule = MagicMock()
            scoring_rule.max_score = Decimal('25')
            scoring_rule.alpha = Decimal('1.0')
            scoring_rule.beta = Decimal('0.5')

            payout = strategy.compute_payout(event_result, scoring_rule)

            # normalized = 12.5/25 = 0.5, payout = 1.0 * 0.5 + 0.5 = 1.0
            assert payout == Decimal('1.0')

    def test_compute_payout_zero_max_score_raises(self, app):
        """Test that zero max_score raises ValueError."""
        with app.app_context():
            strategy = LinearNormalizedStrategy()

            event_result = MagicMock()
            event_result.primary_score = Decimal('10')

            scoring_rule = MagicMock()
            scoring_rule.max_score = Decimal('0')
            scoring_rule.alpha = Decimal('1.0')
            scoring_rule.beta = Decimal('0.0')

            with pytest.raises(ValueError, match="max_score cannot be zero"):
                strategy.compute_payout(event_result, scoring_rule)


class TestSigmoidStrategy:
    """Tests for SigmoidStrategy."""

    def test_compute_payout_with_default_k(self, app):
        """Test sigmoid payout with default k value."""
        with app.app_context():
            strategy = SigmoidStrategy()

            event_result = MagicMock()
            event_result.primary_score = Decimal('12.5')

            scoring_rule = MagicMock()
            scoring_rule.max_score = Decimal('25')
            scoring_rule.alpha = Decimal('1.0')
            scoring_rule.beta = Decimal('0.0')
            scoring_rule.config_json = None  # Default k=10

            payout = strategy.compute_payout(event_result, scoring_rule)

            # normalized = 0.5, sigmoid(0.5*10) = sigmoid(5) ~ 0.9933
            # payout = 1.0 * 0.9933 + 0.0 ~ 0.9933
            assert payout > Decimal('0.99')
            assert payout < Decimal('1.0')

    def test_compute_payout_with_custom_k(self, app):
        """Test sigmoid payout with custom k value."""
        with app.app_context():
            strategy = SigmoidStrategy()

            event_result = MagicMock()
            event_result.primary_score = Decimal('12.5')

            scoring_rule = MagicMock()
            scoring_rule.max_score = Decimal('25')
            scoring_rule.alpha = Decimal('1.0')
            scoring_rule.beta = Decimal('0.0')
            scoring_rule.config_json = {'k': 1}  # Less steep

            payout = strategy.compute_payout(event_result, scoring_rule)

            # normalized = 0.5, sigmoid(0.5*1) = sigmoid(0.5) ~ 0.622
            assert payout > Decimal('0.6')
            assert payout < Decimal('0.7')

    def test_sigmoid_produces_s_curve(self, app):
        """Test that sigmoid produces expected S-curve behavior."""
        with app.app_context():
            strategy = SigmoidStrategy()

            scoring_rule = MagicMock()
            scoring_rule.max_score = Decimal('100')
            scoring_rule.alpha = Decimal('1.0')
            scoring_rule.beta = Decimal('0.0')
            scoring_rule.config_json = {'k': 10}

            # Test low score
            event_result_low = MagicMock()
            event_result_low.primary_score = Decimal('10')
            payout_low = strategy.compute_payout(event_result_low, scoring_rule)

            # Test mid score
            event_result_mid = MagicMock()
            event_result_mid.primary_score = Decimal('50')
            payout_mid = strategy.compute_payout(event_result_mid, scoring_rule)

            # Test high score
            event_result_high = MagicMock()
            event_result_high.primary_score = Decimal('90')
            payout_high = strategy.compute_payout(event_result_high, scoring_rule)

            # S-curve: low < mid < high
            assert payout_low < payout_mid < payout_high
            # Mid should be around 0.5 for normalized=0.5 with high k
            assert payout_mid > Decimal('0.4')


class TestPiecewiseStrategy:
    """Tests for PiecewiseStrategy."""

    def test_compute_payout_first_breakpoint(self, app):
        """Test payout in first breakpoint range."""
        with app.app_context():
            strategy = PiecewiseStrategy()

            event_result = MagicMock()
            event_result.primary_score = Decimal('10')

            scoring_rule = MagicMock()
            scoring_rule.max_score = Decimal('100')
            scoring_rule.alpha = Decimal('0.5')  # Default fallback
            scoring_rule.beta = Decimal('0.0')
            scoring_rule.config_json = {
                'breakpoints': [
                    {'threshold': 0.0, 'alpha': 0.5, 'beta': 0.0},
                    {'threshold': 0.5, 'alpha': 1.0, 'beta': 0.1},
                    {'threshold': 0.8, 'alpha': 1.5, 'beta': 0.2},
                ]
            }

            payout = strategy.compute_payout(event_result, scoring_rule)

            # normalized = 0.1, in first breakpoint (0-0.5)
            # payout = 0.5 * 0.1 + 0.0 = 0.05
            assert payout == Decimal('0.05')

    def test_compute_payout_middle_breakpoint(self, app):
        """Test payout in middle breakpoint range."""
        with app.app_context():
            strategy = PiecewiseStrategy()

            event_result = MagicMock()
            event_result.primary_score = Decimal('60')

            scoring_rule = MagicMock()
            scoring_rule.max_score = Decimal('100')
            scoring_rule.alpha = Decimal('0.5')
            scoring_rule.beta = Decimal('0.0')
            scoring_rule.config_json = {
                'breakpoints': [
                    {'threshold': 0.0, 'alpha': 0.5, 'beta': 0.0},
                    {'threshold': 0.5, 'alpha': 1.0, 'beta': 0.1},
                    {'threshold': 0.8, 'alpha': 1.5, 'beta': 0.2},
                ]
            }

            payout = strategy.compute_payout(event_result, scoring_rule)

            # normalized = 0.6, in second breakpoint (0.5-0.8)
            # payout = 1.0 * 0.6 + 0.1 = 0.7
            assert payout == Decimal('0.7')

    def test_compute_payout_last_breakpoint(self, app):
        """Test payout in last (highest) breakpoint range."""
        with app.app_context():
            strategy = PiecewiseStrategy()

            event_result = MagicMock()
            event_result.primary_score = Decimal('90')

            scoring_rule = MagicMock()
            scoring_rule.max_score = Decimal('100')
            scoring_rule.alpha = Decimal('0.5')
            scoring_rule.beta = Decimal('0.0')
            scoring_rule.config_json = {
                'breakpoints': [
                    {'threshold': 0.0, 'alpha': 0.5, 'beta': 0.0},
                    {'threshold': 0.5, 'alpha': 1.0, 'beta': 0.1},
                    {'threshold': 0.8, 'alpha': 1.5, 'beta': 0.2},
                ]
            }

            payout = strategy.compute_payout(event_result, scoring_rule)

            # normalized = 0.9, in third breakpoint (>=0.8)
            # payout = 1.5 * 0.9 + 0.2 = 1.55
            assert payout == Decimal('1.55')

    def test_fallback_to_linear_no_breakpoints(self, app):
        """Test fallback to linear when no breakpoints configured."""
        with app.app_context():
            strategy = PiecewiseStrategy()

            event_result = MagicMock()
            event_result.primary_score = Decimal('50')

            scoring_rule = MagicMock()
            scoring_rule.id = 1
            scoring_rule.max_score = Decimal('100')
            scoring_rule.alpha = Decimal('1.0')
            scoring_rule.beta = Decimal('0.0')
            scoring_rule.config_json = {}  # No breakpoints

            payout = strategy.compute_payout(event_result, scoring_rule)

            # Falls back to linear: 1.0 * 0.5 + 0.0 = 0.5
            assert payout == Decimal('0.5')


class TestScoringStrategyFactory:
    """Tests for get_scoring_strategy factory function."""

    def test_get_linear_normalized_strategy(self):
        """Test getting LinearNormalizedStrategy."""
        strategy = get_scoring_strategy(FormulaType.LINEAR_NORMALIZED)

        assert isinstance(strategy, LinearNormalizedStrategy)

    def test_get_sigmoid_strategy(self):
        """Test getting SigmoidStrategy."""
        strategy = get_scoring_strategy(FormulaType.SIGMOID)

        assert isinstance(strategy, SigmoidStrategy)

    def test_get_piecewise_strategy(self):
        """Test getting PiecewiseStrategy."""
        strategy = get_scoring_strategy(FormulaType.PIECEWISE)

        assert isinstance(strategy, PiecewiseStrategy)

    def test_unknown_formula_type_defaults_to_linear(self):
        """Test that unknown formula type defaults to LinearNormalizedStrategy."""
        # Create a mock that's not in the strategies dict
        fake_type = MagicMock()
        fake_type.value = 'UNKNOWN'

        strategy = get_scoring_strategy(fake_type)

        assert isinstance(strategy, LinearNormalizedStrategy)
