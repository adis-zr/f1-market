"""Tests for bonding curve pricing functions."""
import pytest
from decimal import Decimal
from pricing.bonding_curve import price, buy_cost, sell_payout


class TestPrice:
    """Tests for price() function."""
    
    def test_price_at_zero_supply(self):
        """Price at zero supply should equal baseline b."""
        a = Decimal('1.0')
        b = Decimal('0.5')
        assert price(Decimal('0'), a, b) == b
    
    def test_price_basic(self):
        """Test basic price calculation."""
        a = Decimal('2.0')
        b = Decimal('1.0')
        s = Decimal('4.0')
        # P(4) = 2 * sqrt(4) + 1 = 2 * 2 + 1 = 5
        expected = Decimal('5.0')
        result = price(s, a, b)
        assert abs(result - expected) < Decimal('0.0001')
    
    def test_price_negative_supply_raises_error(self):
        """Price with negative supply should raise ValueError."""
        with pytest.raises(ValueError, match="Supply cannot be negative"):
            price(Decimal('-1'), Decimal('1'), Decimal('0'))
    
    def test_price_different_parameters(self):
        """Test price with various parameter combinations."""
        # Test with a=0 (flat price)
        assert price(Decimal('100'), Decimal('0'), Decimal('10')) == Decimal('10')
        
        # Test with b=0 (no baseline)
        result = price(Decimal('9'), Decimal('1'), Decimal('0'))
        # sqrt(9) = 3, so price = 1 * 3 + 0 = 3
        assert abs(result - Decimal('3')) < Decimal('0.0001')


class TestBuyCost:
    """Tests for buy_cost() function."""
    
    def test_buy_cost_from_zero(self):
        """Cost to buy from zero supply."""
        a = Decimal('2.0')
        b = Decimal('1.0')
        delta_s = Decimal('4.0')
        # cost = (2*2/3) * (4)^(3/2) + 1 * 4
        #      = (4/3) * 8 + 4 = 32/3 + 4 ≈ 14.67
        result = buy_cost(Decimal('0'), delta_s, a, b)
        expected = Decimal('32') / Decimal('3') + Decimal('4')
        assert abs(result - expected) < Decimal('0.01')
    
    def test_buy_cost_basic(self):
        """Test basic buy cost calculation."""
        a = Decimal('1.0')
        b = Decimal('0.5')
        s = Decimal('1.0')
        delta_s = Decimal('1.0')
        # Buying 1 share when supply is 1
        # cost = (2*1/3) * [(2)^(3/2) - (1)^(3/2)] + 0.5 * 1
        #      = (2/3) * [2.828 - 1.0] + 0.5 ≈ 1.72
        result = buy_cost(s, delta_s, a, b)
        assert result > Decimal('0')
        assert result > delta_s * b  # Should be more than baseline cost
    
    def test_buy_cost_zero_quantity_raises_error(self):
        """Buy cost with zero quantity should raise ValueError."""
        with pytest.raises(ValueError, match="delta_s must be positive"):
            buy_cost(Decimal('10'), Decimal('0'), Decimal('1'), Decimal('0'))
    
    def test_buy_cost_negative_quantity_raises_error(self):
        """Buy cost with negative quantity should raise ValueError."""
        with pytest.raises(ValueError, match="delta_s must be positive"):
            buy_cost(Decimal('10'), Decimal('-1'), Decimal('1'), Decimal('0'))
    
    def test_buy_cost_negative_supply_raises_error(self):
        """Buy cost with negative supply should raise ValueError."""
        with pytest.raises(ValueError, match="Supply cannot be negative"):
            buy_cost(Decimal('-1'), Decimal('1'), Decimal('1'), Decimal('0'))
    
    def test_buy_cost_increases_with_quantity(self):
        """Buying more shares should cost more (but not linearly)."""
        a = Decimal('1.0')
        b = Decimal('0.5')
        s = Decimal('10.0')
        
        cost_1 = buy_cost(s, Decimal('1'), a, b)
        cost_2 = buy_cost(s, Decimal('2'), a, b)
        cost_5 = buy_cost(s, Decimal('5'), a, b)
        
        assert cost_2 > cost_1
        assert cost_5 > cost_2
        # Cost per share should increase (bonding curve effect)
        assert cost_5 / Decimal('5') > cost_1 / Decimal('1')


class TestSellPayout:
    """Tests for sell_payout() function."""
    
    def test_sell_payout_basic(self):
        """Test basic sell payout calculation."""
        a = Decimal('1.0')
        b = Decimal('0.5')
        s = Decimal('10.0')
        delta_s = Decimal('2.0')
        # Selling 2 shares when supply is 10
        result = sell_payout(s, delta_s, a, b)
        assert result > Decimal('0')
        assert result > delta_s * b  # Should be more than baseline
    
    def test_sell_payout_all_shares(self):
        """Selling all shares should work correctly."""
        a = Decimal('2.0')
        b = Decimal('1.0')
        s = Decimal('4.0')
        # Selling all 4 shares
        result = sell_payout(s, s, a, b)
        # Should equal the cost to buy from zero
        buy_cost_result = buy_cost(Decimal('0'), s, a, b)
        assert abs(result - buy_cost_result) < Decimal('0.01')
    
    def test_sell_payout_zero_quantity_raises_error(self):
        """Sell payout with zero quantity should raise ValueError."""
        with pytest.raises(ValueError, match="delta_s must be positive"):
            sell_payout(Decimal('10'), Decimal('0'), Decimal('1'), Decimal('0'))
    
    def test_sell_payout_negative_quantity_raises_error(self):
        """Sell payout with negative quantity should raise ValueError."""
        with pytest.raises(ValueError, match="delta_s must be positive"):
            sell_payout(Decimal('10'), Decimal('-1'), Decimal('1'), Decimal('0'))
    
    def test_sell_payout_exceeds_supply_raises_error(self):
        """Selling more than supply should raise ValueError."""
        with pytest.raises(ValueError, match="Cannot sell more shares than current supply"):
            sell_payout(Decimal('10'), Decimal('11'), Decimal('1'), Decimal('0'))
    
    def test_sell_payout_negative_supply_raises_error(self):
        """Sell payout with negative supply should raise ValueError."""
        with pytest.raises(ValueError, match="Supply cannot be negative"):
            sell_payout(Decimal('-1'), Decimal('1'), Decimal('1'), Decimal('0'))
    
    def test_sell_payout_decreases_with_remaining_supply(self):
        """Selling when more shares remain should give higher payout per share."""
        a = Decimal('1.0')
        b = Decimal('0.5')
        
        # Selling 1 share when supply is 10
        payout_high_supply = sell_payout(Decimal('10'), Decimal('1'), a, b)
        # Selling 1 share when supply is 2
        payout_low_supply = sell_payout(Decimal('2'), Decimal('1'), a, b)
        
        # Higher supply should give lower payout per share (bonding curve effect)
        assert payout_high_supply < payout_low_supply


class TestPricingConsistency:
    """Tests for consistency between buy and sell operations."""
    
    def test_buy_then_sell_round_trip(self):
        """Buying then selling the same quantity should result in a loss (due to curve)."""
        a = Decimal('1.0')
        b = Decimal('0.5')
        s = Decimal('10.0')
        delta_s = Decimal('2.0')
        
        cost = buy_cost(s, delta_s, a, b)
        payout = sell_payout(s + delta_s, delta_s, a, b)
        
        # Due to bonding curve, selling immediately after buying should result in loss
        # (This is the spread/AMM fee)
        assert payout < cost
    
    def test_price_matches_buy_cost_for_small_quantity(self):
        """For very small quantities, price should approximate buy_cost / quantity."""
        a = Decimal('1.0')
        b = Decimal('0.5')
        s = Decimal('10.0')
        delta_s = Decimal('0.001')  # Very small
        
        current_price = price(s, a, b)
        cost = buy_cost(s, delta_s, a, b)
        price_per_share = cost / delta_s
        
        # Price per share should be close to current price for small quantities
        assert abs(price_per_share - current_price) < Decimal('0.1')

