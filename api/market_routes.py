"""Market API routes for buying and selling shares."""
import logging
from flask import Blueprint, request, jsonify
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)
from services.market_service import (
    MarketService, MarketClosedError, InsufficientSharesError
)
from services.wallet_service import WalletService, InsufficientBalanceError
from db import db, Market, PriceHistory
from auth.helpers import get_current_user_id
from config import MAX_QUERY_LIMIT
from pricing.bonding_curve import buy_cost, sell_payout, get_current_supply

bp = Blueprint('market', __name__, url_prefix='/api/markets')

# Quantity validation constants
MAX_QUANTITY = Decimal('1000000')  # 1 million shares max
MIN_QUANTITY = Decimal('0.01')     # Minimum 0.01 shares
MAX_DECIMALS = 8


def validate_quantity(quantity: Decimal) -> tuple[bool, str | None]:
    """Validate quantity is within acceptable bounds.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if quantity > MAX_QUANTITY:
        return False, f'Quantity exceeds maximum ({MAX_QUANTITY})'
    if quantity < MIN_QUANTITY:
        return False, f'Quantity below minimum ({MIN_QUANTITY})'
    # Check decimal places
    sign, digits, exponent = quantity.as_tuple()
    if exponent < 0 and abs(exponent) > MAX_DECIMALS:
        return False, f'Too many decimal places (max {MAX_DECIMALS})'
    return True, None


@bp.route('/<int:market_id>', methods=['GET'])
def get_market(market_id):
    """Get market information including current price and supply."""
    try:
        market_info = MarketService.get_market_info(market_id)
        if not market_info:
            return jsonify({'error': 'Market not found'}), 404
        
        return jsonify(market_info), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:market_id>/buy', methods=['POST'])
def buy_shares(market_id):
    """Buy shares in a market."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = request.get_json()
        if not data or 'quantity' not in data:
            return jsonify({'error': 'quantity is required'}), 400

        try:
            quantity = Decimal(str(data['quantity']))
        except (ValueError, InvalidOperation):
            return jsonify({'error': 'Invalid quantity format'}), 400

        if quantity <= 0:
            return jsonify({'error': 'Quantity must be positive'}), 400

        # Validate quantity bounds
        is_valid, error_msg = validate_quantity(quantity)
        if not is_valid:
            return jsonify({'error': error_msg}), 400

        result = MarketService.buy_shares(user_id, market_id, quantity)
        return jsonify(result), 200
    
    except MarketClosedError as e:
        return jsonify({'error': str(e)}), 400
    except InsufficientBalanceError as e:
        return jsonify({'error': str(e)}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in buy_shares: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/<int:market_id>/sell', methods=['POST'])
def sell_shares(market_id):
    """Sell shares in a market."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = request.get_json()
        if not data or 'quantity' not in data:
            return jsonify({'error': 'quantity is required'}), 400

        try:
            quantity = Decimal(str(data['quantity']))
        except (ValueError, InvalidOperation):
            return jsonify({'error': 'Invalid quantity format'}), 400

        if quantity <= 0:
            return jsonify({'error': 'Quantity must be positive'}), 400

        # Validate quantity bounds
        is_valid, error_msg = validate_quantity(quantity)
        if not is_valid:
            return jsonify({'error': error_msg}), 400

        result = MarketService.sell_shares(user_id, market_id, quantity)
        return jsonify(result), 200
    
    except MarketClosedError as e:
        return jsonify({'error': str(e)}), 400
    except InsufficientSharesError as e:
        return jsonify({'error': str(e)}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in sell_shares: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/<int:market_id>/positions', methods=['GET'])
def get_position(market_id):
    """Get user's position in a market."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        position = MarketService.get_user_position(user_id, market_id)
        if position is None:
            return jsonify({'shares': 0, 'avg_entry_price': 0, 'realized_pnl': 0}), 200
        
        return jsonify(position), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:market_id>/estimate', methods=['POST'])
def estimate_cost(market_id):
    """Estimate cost/payout for a buy or sell order using bonding curve math."""
    try:
        data = request.get_json()
        if not data or 'quantity' not in data:
            return jsonify({'error': 'quantity is required'}), 400

        try:
            quantity = Decimal(str(data['quantity']))
        except (ValueError, InvalidOperation):
            return jsonify({'error': 'Invalid quantity format'}), 400

        if quantity <= 0:
            return jsonify({'error': 'Quantity must be positive'}), 400

        # Validate quantity bounds
        is_valid, error_msg = validate_quantity(quantity)
        if not is_valid:
            return jsonify({'error': error_msg}), 400

        side = data.get('side', 'buy').lower()
        if side not in ('buy', 'sell'):
            return jsonify({'error': 'side must be "buy" or "sell"'}), 400

        # Get market
        market = db.session.get(Market, market_id)
        if not market:
            return jsonify({'error': 'Market not found'}), 404

        current_supply = get_current_supply(market_id)
        a = Decimal(str(market.a))
        b = Decimal(str(market.b))

        if side == 'buy':
            cost = buy_cost(current_supply, quantity, a, b)
            return jsonify({
                'side': 'buy',
                'quantity': float(quantity),
                'estimated_cost': float(cost),
                'price_per_share': float(cost / quantity),
                'current_supply': float(current_supply)
            }), 200
        else:
            # Check if there's enough supply to sell
            if quantity > current_supply:
                return jsonify({'error': 'Insufficient supply in market'}), 400
            payout = sell_payout(current_supply, quantity, a, b)
            return jsonify({
                'side': 'sell',
                'quantity': float(quantity),
                'estimated_payout': float(payout),
                'price_per_share': float(payout / quantity),
                'current_supply': float(current_supply)
            }), 200

    except Exception as e:
        logger.error(f"Error in estimate_cost: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/<int:market_id>/price-history', methods=['GET'])
def get_price_history(market_id):
    """Get price history for a market."""
    try:
        # Verify market exists
        market = db.session.get(Market, market_id)
        if not market:
            return jsonify({'error': 'Market not found'}), 404
        
        # Get limit from query params
        limit = request.args.get('limit', default=100, type=int)
        limit = max(1, min(limit, MAX_QUERY_LIMIT))

        # Use direct query with limit instead of loading all via relationship
        price_history = PriceHistory.query.filter_by(market_id=market_id)\
            .order_by(PriceHistory.timestamp.desc())\
            .limit(limit).all()

        return jsonify({
            'market_id': market_id,
            'history': [
                {
                    'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
                    'price': float(entry.price),
                    'reason': entry.reason
                }
                for entry in price_history
            ]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:market_id>/wallet', methods=['GET'])
def get_wallet_info(market_id):
    """Get wallet information for current user (for market context)."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        balance = WalletService.get_balance(user_id)
        total_balance = WalletService.get_total_balance(user_id)
        locked_balance = WalletService.get_locked_balance(user_id)
        
        return jsonify({
            'user_id': user_id,
            'available_balance': float(balance),
            'total_balance': float(total_balance),
            'locked_balance': float(locked_balance)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

