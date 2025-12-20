"""Replay API routes for the Replay 2024 Season feature."""
import logging
from flask import Blueprint, request, jsonify
from decimal import Decimal, InvalidOperation

from auth.helpers import get_current_user_id
from services.replay_service import (
    ReplayService, ReplaySessionNotFoundError,
    ReplayMarketClosedError, ReplayInsufficientBalanceError,
    ReplayInsufficientSharesError
)
from services.replay_market_service import ReplayMarketService
from data.f1_2024 import RACES_2024, get_race_info

logger = logging.getLogger(__name__)

bp = Blueprint('replay', __name__, url_prefix='/api/replay')

# Quantity validation constants
MAX_QUANTITY = Decimal('1000000')
MIN_QUANTITY = Decimal('0.01')
MAX_DECIMALS = 8


def validate_quantity(quantity: Decimal) -> tuple[bool, str | None]:
    """Validate quantity is within acceptable bounds."""
    if quantity > MAX_QUANTITY:
        return False, f'Quantity exceeds maximum ({MAX_QUANTITY})'
    if quantity < MIN_QUANTITY:
        return False, f'Quantity below minimum ({MIN_QUANTITY})'
    sign, digits, exponent = quantity.as_tuple()
    if exponent < 0 and abs(exponent) > MAX_DECIMALS:
        return False, f'Too many decimal places (max {MAX_DECIMALS})'
    return True, None


# =============================================================================
# Session Management
# =============================================================================

@bp.route('/start', methods=['POST'])
def start_replay():
    """Start a new replay session.

    Creates a new replay session with $100 starting balance.
    If user already has an active session, returns that session.
    """
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        # Check for existing active session
        existing = ReplayService.get_active_session(user_id)
        if existing:
            return jsonify(ReplayService.get_session_state(existing.id)), 200

        # Create new session
        state = ReplayService.start_replay(user_id)
        return jsonify(state), 201

    except Exception as e:
        logger.error(f"Error in start_replay: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/session', methods=['GET'])
def get_session():
    """Get current replay session state."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        session = ReplayService.get_active_session(user_id)
        if not session:
            return jsonify({'error': 'No active replay session'}), 404

        state = ReplayService.get_session_state(session.id)
        return jsonify(state), 200

    except ReplaySessionNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error in get_session: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/reset', methods=['POST'])
def reset_replay():
    """Reset current replay session to start fresh."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        session = ReplayService.get_active_session(user_id)
        if not session:
            return jsonify({'error': 'No active replay session'}), 404

        state = ReplayService.reset_replay(session.id)
        return jsonify(state), 200

    except ReplaySessionNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error in reset_replay: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# =============================================================================
# Race Progression
# =============================================================================

@bp.route('/advance', methods=['POST'])
def advance_race():
    """Advance to the next race.

    If current race > 0, settles it using historical results.
    Creates markets for the next race, or marks session complete if done.
    """
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        session = ReplayService.get_active_session(user_id)
        if not session:
            return jsonify({'error': 'No active replay session'}), 404

        result = ReplayService.advance_to_next_race(session.id)
        return jsonify(result), 200

    except ReplaySessionNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in advance_race: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# =============================================================================
# Markets
# =============================================================================

@bp.route('/markets', methods=['GET'])
def get_markets():
    """Get markets for current race."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        session = ReplayService.get_active_session(user_id)
        if not session:
            return jsonify({'error': 'No active replay session'}), 404

        state = ReplayService.get_session_state(session.id)
        return jsonify({'markets': state['markets']}), 200

    except Exception as e:
        logger.error(f"Error in get_markets: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/markets/<int:market_id>', methods=['GET'])
def get_market(market_id):
    """Get specific market details."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        market_info = ReplayMarketService.get_market_info(market_id)
        if not market_info:
            return jsonify({'error': 'Market not found'}), 404

        # Get position if exists
        session = ReplayService.get_active_session(user_id)
        position = None
        if session:
            position = ReplayMarketService.get_position(session.id, market_id)

        return jsonify({
            'market': market_info,
            'position': position
        }), 200

    except Exception as e:
        logger.error(f"Error in get_market: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/markets/<int:market_id>/buy', methods=['POST'])
def buy_shares(market_id):
    """Buy shares in a replay market."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        session = ReplayService.get_active_session(user_id)
        if not session:
            return jsonify({'error': 'No active replay session'}), 404

        data = request.get_json()
        if not data or 'quantity' not in data:
            return jsonify({'error': 'quantity is required'}), 400

        try:
            quantity = Decimal(str(data['quantity']))
        except (ValueError, InvalidOperation):
            return jsonify({'error': 'Invalid quantity format'}), 400

        if quantity <= 0:
            return jsonify({'error': 'Quantity must be positive'}), 400

        is_valid, error_msg = validate_quantity(quantity)
        if not is_valid:
            return jsonify({'error': error_msg}), 400

        result = ReplayMarketService.buy_shares(session.id, market_id, quantity)
        return jsonify(result), 200

    except ReplayMarketClosedError as e:
        return jsonify({'error': str(e)}), 400
    except ReplayInsufficientBalanceError as e:
        return jsonify({'error': str(e)}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in buy_shares: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/markets/<int:market_id>/sell', methods=['POST'])
def sell_shares(market_id):
    """Sell shares in a replay market."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        session = ReplayService.get_active_session(user_id)
        if not session:
            return jsonify({'error': 'No active replay session'}), 404

        data = request.get_json()
        if not data or 'quantity' not in data:
            return jsonify({'error': 'quantity is required'}), 400

        try:
            quantity = Decimal(str(data['quantity']))
        except (ValueError, InvalidOperation):
            return jsonify({'error': 'Invalid quantity format'}), 400

        if quantity <= 0:
            return jsonify({'error': 'Quantity must be positive'}), 400

        is_valid, error_msg = validate_quantity(quantity)
        if not is_valid:
            return jsonify({'error': error_msg}), 400

        result = ReplayMarketService.sell_shares(session.id, market_id, quantity)
        return jsonify(result), 200

    except ReplayMarketClosedError as e:
        return jsonify({'error': str(e)}), 400
    except ReplayInsufficientSharesError as e:
        return jsonify({'error': str(e)}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in sell_shares: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/markets/<int:market_id>/estimate', methods=['POST'])
def estimate(market_id):
    """Estimate buy/sell cost for a replay market."""
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

        is_valid, error_msg = validate_quantity(quantity)
        if not is_valid:
            return jsonify({'error': error_msg}), 400

        side = data.get('side', 'buy').lower()
        if side not in ('buy', 'sell'):
            return jsonify({'error': 'side must be "buy" or "sell"'}), 400

        result = ReplayMarketService.estimate_cost(market_id, quantity, side)
        return jsonify(result), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in estimate: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/markets/<int:market_id>/price-history', methods=['GET'])
def get_price_history(market_id):
    """Get price history for a replay market."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        limit = request.args.get('limit', default=100, type=int)
        limit = max(1, min(limit, 500))

        history = ReplayMarketService.get_price_history(market_id, limit)
        return jsonify({
            'market_id': market_id,
            'history': history
        }), 200

    except Exception as e:
        logger.error(f"Error in get_price_history: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# =============================================================================
# Portfolio & Wallet
# =============================================================================

@bp.route('/portfolio', methods=['GET'])
def get_portfolio():
    """Get all positions in current replay session."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        session = ReplayService.get_active_session(user_id)
        if not session:
            return jsonify({'error': 'No active replay session'}), 404

        state = ReplayService.get_session_state(session.id)
        return jsonify({
            'positions': state['positions'],
            'total_pnl': state['total_pnl']
        }), 200

    except Exception as e:
        logger.error(f"Error in get_portfolio: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/wallet', methods=['GET'])
def get_wallet():
    """Get wallet balance for replay session."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        session = ReplayService.get_active_session(user_id)
        if not session:
            return jsonify({'error': 'No active replay session'}), 404

        state = ReplayService.get_session_state(session.id)
        return jsonify(state['wallet']), 200

    except Exception as e:
        logger.error(f"Error in get_wallet: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/wallet/ledger', methods=['GET'])
def get_ledger():
    """Get ledger history for replay session."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        from db.replay_models import ReplayLedgerEntry

        session = ReplayService.get_active_session(user_id)
        if not session:
            return jsonify({'error': 'No active replay session'}), 404

        limit = request.args.get('limit', default=100, type=int)
        limit = max(1, min(limit, 500))

        entries = ReplayLedgerEntry.query.filter_by(
            session_id=session.id
        ).order_by(
            ReplayLedgerEntry.created_at.desc()
        ).limit(limit).all()

        return jsonify({
            'ledger': [
                {
                    'id': e.id,
                    'amount': float(e.amount),
                    'transaction_type': e.transaction_type.value,
                    'description': e.description,
                    'created_at': e.created_at.isoformat() if e.created_at else None
                }
                for e in entries
            ]
        }), 200

    except Exception as e:
        logger.error(f"Error in get_ledger: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# =============================================================================
# Race Info
# =============================================================================

@bp.route('/races', methods=['GET'])
def get_races():
    """Get all 24 races info."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        session = ReplayService.get_active_session(user_id)
        current_race = session.current_race if session else 0

        races = []
        for race_num in range(1, 25):
            race_data = get_race_info(race_num)
            if race_data:
                if race_num < current_race:
                    status = "completed"
                elif race_num == current_race:
                    status = "current"
                else:
                    status = "upcoming"

                races.append({
                    "race_number": race_num,
                    "name": race_data["name"],
                    "venue": race_data["venue"],
                    "date": race_data["date"],
                    "status": status
                })

        return jsonify({'races': races}), 200

    except Exception as e:
        logger.error(f"Error in get_races: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/races/<int:race_number>/results', methods=['GET'])
def get_race_results(race_number):
    """Get results for a completed race."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        if race_number < 1 or race_number > 24:
            return jsonify({'error': 'Invalid race number (1-24)'}), 400

        race_data = get_race_info(race_number)
        if not race_data:
            return jsonify({'error': 'Race not found'}), 404

        from data.f1_2024 import get_points_for_position, get_driver_by_code

        results = []
        for driver_code, position in race_data["results"]:
            driver = get_driver_by_code(driver_code)
            points = get_points_for_position(position)
            results.append({
                "driver_code": driver_code,
                "driver_name": driver["name"] if driver else driver_code,
                "team": driver["team"] if driver else None,
                "position": position,
                "points": float(points)
            })

        return jsonify({
            "race_number": race_number,
            "name": race_data["name"],
            "venue": race_data["venue"],
            "date": race_data["date"],
            "results": results
        }), 200

    except Exception as e:
        logger.error(f"Error in get_race_results: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# =============================================================================
# Leaderboard
# =============================================================================

@bp.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get leaderboard of completed replays."""
    user_id = get_current_user_id()

    try:
        limit = request.args.get('limit', default=50, type=int)
        limit = max(1, min(limit, 100))

        result = ReplayService.get_leaderboard(limit=limit, user_id=user_id)
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error in get_leaderboard: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
