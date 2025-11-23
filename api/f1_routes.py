"""F1 API routes for standings and telemetry."""
from flask import Blueprint, jsonify, session, request, current_app
from f1 import F1Service
from functools import wraps

bp = Blueprint('f1', __name__, url_prefix='/api/f1')


def require_auth(f):
    """Decorator to require authentication for F1 routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'message': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def get_f1_service() -> F1Service:
    """Get F1Service instance configured from app config."""
    provider = current_app.config.get('F1_PROVIDER', 'sportmonks')
    return F1Service(provider=provider)


@bp.route('/standings', methods=['GET'])
@require_auth
def get_standings():
    """Get current driver and constructor championship standings."""
    try:
        service = get_f1_service()
        season = request.args.get('season', type=int)
        
        driver_standings = service.get_driver_standings(season=season)
        constructor_standings = service.get_constructor_standings(season=season)
        
        if driver_standings is None or constructor_standings is None:
            return jsonify({
                'message': 'Failed to fetch standings from F1 API',
                'driver_standings': driver_standings,
                'constructor_standings': constructor_standings,
            }), 503
        
        return jsonify({
            'driver_standings': driver_standings,
            'constructor_standings': constructor_standings,
            'season': season or current_app.config.get('F1_CURRENT_SEASON', None),
        }), 200
        
    except Exception as e:
        print(f"Error in get_standings: {e}")
        return jsonify({'message': 'Server error occurred'}), 500


@bp.route('/race-status', methods=['GET'])
@require_auth
def get_race_status():
    """Check if a race is currently ongoing."""
    try:
        service = get_f1_service()
        is_ongoing = service.is_race_ongoing()
        
        response_data = {
            'race_ongoing': is_ongoing,
        }
        
        # If race is ongoing, include race ID for telemetry requests
        if is_ongoing:
            race_id = service.get_current_session_key()  # Returns race_id for SportsMonk
            if race_id:
                response_data['race_id'] = race_id
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"Error in get_race_status: {e}")
        return jsonify({'message': 'Server error occurred'}), 500


@bp.route('/telemetry', methods=['GET'])
@require_auth
def get_telemetry():
    """Get real-time telemetry data for ongoing race."""
    try:
        service = get_f1_service()
        race_id = request.args.get('race_id', type=int) or request.args.get('session_key', type=int)
        
        telemetry = service.get_telemetry(session_key=race_id)
        
        if telemetry is None:
            # Check if race is ongoing
            if not service.is_race_ongoing():
                return jsonify({
                    'message': 'No race is currently ongoing',
                    'race_ongoing': False,
                }), 404
            else:
                return jsonify({
                    'message': 'Failed to fetch telemetry data',
                    'race_ongoing': True,
                }), 503
        
        return jsonify(telemetry), 200
        
    except Exception as e:
        print(f"Error in get_telemetry: {e}")
        return jsonify({'message': 'Server error occurred'}), 500


@bp.route('/last-race', methods=['GET'])
@require_auth
def get_last_race():
    """Get the last finished race with results."""
    try:
        service = get_f1_service()
        season = request.args.get('season', type=int)
        
        last_race = service.get_last_race_results(season_year=season)
        
        if last_race is None:
            return jsonify({
                'message': 'No finished race found',
                'race_found': False,
            }), 404
        
        return jsonify({
            'race_found': True,
            **last_race,
        }), 200
        
    except Exception as e:
        print(f"Error in get_last_race: {e}")
        return jsonify({'message': 'Server error occurred'}), 500

