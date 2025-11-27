"""Market API routes for buying and selling shares."""
from flask import Blueprint, request, jsonify, session
from decimal import Decimal, InvalidOperation
from services.market_service import (
    MarketService, MarketClosedError, InsufficientSharesError
)
from services.wallet_service import WalletService, InsufficientBalanceError
from db import Market

bp = Blueprint('market', __name__, url_prefix='/api/markets')


def get_current_user_id():
    """Get current user ID from session."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return user_id


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
        
        result = MarketService.buy_shares(user_id, market_id, quantity)
        return jsonify(result), 200
    
    except MarketClosedError as e:
        return jsonify({'error': str(e)}), 400
    except InsufficientBalanceError as e:
        return jsonify({'error': str(e)}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


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
        
        result = MarketService.sell_shares(user_id, market_id, quantity)
        return jsonify(result), 200
    
    except MarketClosedError as e:
        return jsonify({'error': str(e)}), 400
    except InsufficientSharesError as e:
        return jsonify({'error': str(e)}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


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


@bp.route('/<int:market_id>/price-history', methods=['GET'])
def get_price_history(market_id):
    """Get price history for a market."""
    try:
        # Verify market exists
        market = Market.query.get(market_id)
        if not market:
            return jsonify({'error': 'Market not found'}), 404
        
        # Get limit from query params
        limit = request.args.get('limit', default=100, type=int)
        if limit > 1000:
            limit = 1000
        
        price_history = market.price_history[:limit]
        
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

