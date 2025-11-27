"""Settlement API routes (admin only)."""
from flask import Blueprint, request, jsonify, session
from services.settlement_service import SettlementService
from db import User, Event

bp = Blueprint('settlement', __name__, url_prefix='/api/events')


def get_current_user_id():
    """Get current user ID from session."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return user_id


def is_admin():
    """Check if current user is admin."""
    user_id = get_current_user_id()
    if not user_id:
        return False
    
    user = User.query.get(user_id)
    if not user:
        return False
    
    return user.is_admin()


@bp.route('/<int:event_id>/settle', methods=['POST'])
def settle_event(event_id):
    """Settle an event (admin only)."""
    if not is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        data = request.get_json() or {}
        source = data.get('source', 'event_result')
        
        result = SettlementService.settle_event(event_id, source=source)
        return jsonify(result), 200
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@bp.route('/<int:event_id>/settlement-preview', methods=['GET'])
def preview_settlement(event_id):
    """Preview what settlement would look like (admin only)."""
    if not is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        preview = SettlementService.preview_settlement(event_id)
        return jsonify(preview), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:event_id>', methods=['GET'])
def get_event(event_id):
    """Get event information."""
    try:
        event = Event.query.get(event_id)
        if not event:
            return jsonify({'error': 'Event not found'}), 404
        
        return jsonify({
            'event_id': event.id,
            'name': event.name,
            'venue': event.venue,
            'status': event.status.value if hasattr(event.status, 'value') else str(event.status),
            'start_at': event.start_at.isoformat() if event.start_at else None,
            'end_at': event.end_at.isoformat() if event.end_at else None,
            'season_id': event.season_id,
            'metadata': event.metadata_json
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

