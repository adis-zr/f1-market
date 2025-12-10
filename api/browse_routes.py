"""Browse API routes for sports, leagues, seasons, events, and markets."""
from decimal import Decimal
from typing import Dict, List
from flask import Blueprint, request, jsonify, session
from sqlalchemy import func
from db import (
    db, Sport, League, Season, Event, Market, Asset, Position, Wallet, LedgerEntry,
    EventResult, Participant
)
from sqlalchemy.orm import joinedload
from pricing.bonding_curve import price

bp = Blueprint('browse', __name__, url_prefix='/api')


def get_supplies_batch(market_ids: List[int]) -> Dict[int, Decimal]:
    """
    Get current supply for multiple markets in a single query.
    
    Args:
        market_ids: List of market IDs
    
    Returns:
        Dict mapping market_id to supply (Decimal)
    """
    if not market_ids:
        return {}
    
    supplies = db.session.query(
        Position.market_id,
        func.sum(Position.shares).label('total_supply')
    ).filter(
        Position.market_id.in_(market_ids)
    ).group_by(Position.market_id).all()
    
    # Build dict with default of 0 for markets with no positions
    supply_map = {market_id: Decimal('0') for market_id in market_ids}
    for row in supplies:
        supply_map[row.market_id] = Decimal(str(row.total_supply)) if row.total_supply else Decimal('0')
    
    return supply_map


def get_current_user_id():
    """Get current user ID from session."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return user_id


@bp.route('/sports', methods=['GET'])
def get_sports():
    """Get all sports."""
    try:
        sports = Sport.query.all()
        return jsonify([
            {
                'id': sport.id,
                'code': sport.code,
                'name': sport.name,
            }
            for sport in sports
        ]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/leagues', methods=['GET'])
def get_leagues():
    """Get leagues, optionally filtered by sport_id."""
    try:
        sport_id = request.args.get('sport_id', type=int)
        query = League.query
        if sport_id:
            query = query.filter_by(sport_id=sport_id)
        
        leagues = query.all()
        return jsonify([
            {
                'id': league.id,
                'sport_id': league.sport_id,
                'name': league.name,
            }
            for league in leagues
        ]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/seasons', methods=['GET'])
def get_seasons():
    """Get seasons, optionally filtered by league_id."""
    try:
        league_id = request.args.get('league_id', type=int)
        query = Season.query
        if league_id:
            query = query.filter_by(league_id=league_id)
        
        seasons = query.all()
        return jsonify([
            {
                'id': season.id,
                'league_id': season.league_id,
                'year': season.year,
                'status': season.status.value if hasattr(season.status, 'value') else str(season.status),
            }
            for season in seasons
        ]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/events', methods=['GET'])
def get_events():
    """Get events with optional filters."""
    try:
        sport_id = request.args.get('sport_id', type=int)
        season_id = request.args.get('season_id', type=int)
        status = request.args.get('status', type=str)
        
        query = Event.query
        if season_id:
            query = query.filter_by(season_id=season_id)
        elif sport_id:
            # Filter by sport through season -> league -> sport
            query = query.join(Season).join(League).filter(League.sport_id == sport_id)
        
        if status:
            from db import EventStatus
            try:
                status_enum = EventStatus[status.upper()]
                query = query.filter(Event.status == status_enum)
            except (KeyError, AttributeError):
                pass
        
        events = query.all()
        return jsonify([
            {
                'id': event.id,
                'season_id': event.season_id,
                'name': event.name,
                'venue': event.venue,
                'start_at': event.start_at.isoformat() if event.start_at else None,
                'end_at': event.end_at.isoformat() if event.end_at else None,
                'status': event.status.value if hasattr(event.status, 'value') else str(event.status),
                'metadata': event.metadata_json,
            }
            for event in events
        ]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/events/<int:event_id>/markets', methods=['GET'])
def get_event_markets(event_id):
    """Get markets for an event."""
    try:
        markets = Market.query.filter_by(event_id=event_id).options(
            joinedload(Market.asset).joinedload(Asset.participant),
            joinedload(Market.asset).joinedload(Asset.team),
            joinedload(Market.event),
        ).all()
        
        # Batch fetch supplies for all markets (single query instead of N queries)
        market_ids = [m.id for m in markets]
        supply_map = get_supplies_batch(market_ids)
        
        result = []
        for market in markets:
            current_supply = supply_map.get(market.id, Decimal('0'))
            current_price = price(
                current_supply,
                Decimal(str(market.a)),
                Decimal(str(market.b))
            )
            
            asset_data = None
            if market.asset:
                asset_data = {
                    'id': market.asset.id,
                    'type': market.asset.type.value if hasattr(market.asset.type, 'value') else str(market.asset.type),
                    'symbol': market.asset.symbol,
                    'display_name': market.asset.display_name,
                }
                if market.asset.participant:
                    asset_data['participant'] = {
                        'id': market.asset.participant.id,
                        'name': market.asset.participant.name,
                        'short_code': market.asset.participant.short_code,
                    }
                if market.asset.team:
                    asset_data['team'] = {
                        'id': market.asset.team.id,
                        'name': market.asset.team.name,
                        'short_code': market.asset.team.short_code,
                    }
            
            event_data = None
            if market.event:
                event_data = {
                    'id': market.event.id,
                    'name': market.event.name,
                    'venue': market.event.venue,
                    'start_at': market.event.start_at.isoformat() if market.event.start_at else None,
                    'end_at': market.event.end_at.isoformat() if market.event.end_at else None,
                    'status': market.event.status.value if hasattr(market.event.status, 'value') else str(market.event.status),
                }
            
            result.append({
                'market_id': market.id,
                'event_id': market.event_id,
                'asset_id': market.asset_id,
                'status': market.status.value if hasattr(market.status, 'value') else str(market.status),
                'current_price': float(current_price),
                'current_supply': float(current_supply),
                'market_type': market.market_type,
                'asset': asset_data,
                'event': event_data,
            })
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/events/<int:event_id>/results', methods=['GET'])
def get_event_results(event_id):
    """Get event results."""
    try:
        results = EventResult.query.filter_by(event_id=event_id).options(
            joinedload(EventResult.participant)
        ).all()
        
        return jsonify([
            {
                'id': result.id,
                'event_id': result.event_id,
                'participant_id': result.participant_id,
                'primary_score': float(result.primary_score),
                'rank': result.rank,
                'status': result.status.value if hasattr(result.status, 'value') else str(result.status),
                'participant': {
                    'id': result.participant.id,
                    'name': result.participant.name,
                    'short_code': result.participant.short_code,
                } if result.participant else None,
            }
            for result in results
        ]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/markets', methods=['GET'])
def get_markets():
    """Get markets with optional filters."""
    try:
        event_id = request.args.get('event_id', type=int)
        sport_id = request.args.get('sport_id', type=int)
        status = request.args.get('status', type=str)
        
        query = Market.query.options(
            joinedload(Market.asset).joinedload(Asset.participant),
            joinedload(Market.asset).joinedload(Asset.team),
            joinedload(Market.event),
        )
        
        if event_id:
            query = query.filter_by(event_id=event_id)
        elif sport_id:
            # Filter by sport through event -> season -> league -> sport
            query = query.join(Event).join(Season).join(League).filter(League.sport_id == sport_id)
        
        if status:
            from db import MarketStatus
            try:
                status_enum = MarketStatus[status.upper()]
                query = query.filter(Market.status == status_enum)
            except (KeyError, AttributeError):
                pass
        
        markets = query.all()
        
        # Batch fetch supplies for all markets (single query instead of N queries)
        market_ids = [m.id for m in markets]
        supply_map = get_supplies_batch(market_ids)
        
        result = []
        for market in markets:
            current_supply = supply_map.get(market.id, Decimal('0'))
            current_price = price(
                current_supply,
                Decimal(str(market.a)),
                Decimal(str(market.b))
            )
            
            asset_data = None
            if market.asset:
                asset_data = {
                    'id': market.asset.id,
                    'type': market.asset.type.value if hasattr(market.asset.type, 'value') else str(market.asset.type),
                    'symbol': market.asset.symbol,
                    'display_name': market.asset.display_name,
                }
                if market.asset.participant:
                    asset_data['participant'] = {
                        'id': market.asset.participant.id,
                        'name': market.asset.participant.name,
                        'short_code': market.asset.participant.short_code,
                    }
                if market.asset.team:
                    asset_data['team'] = {
                        'id': market.asset.team.id,
                        'name': market.asset.team.name,
                        'short_code': market.asset.team.short_code,
                    }
            
            event_data = None
            if market.event:
                event_data = {
                    'id': market.event.id,
                    'name': market.event.name,
                    'venue': market.event.venue,
                    'start_at': market.event.start_at.isoformat() if market.event.start_at else None,
                    'end_at': market.event.end_at.isoformat() if market.event.end_at else None,
                    'status': market.event.status.value if hasattr(market.event.status, 'value') else str(market.event.status),
                }
            
            result.append({
                'market_id': market.id,
                'event_id': market.event_id,
                'asset_id': market.asset_id,
                'status': market.status.value if hasattr(market.status, 'value') else str(market.status),
                'current_price': float(current_price),
                'current_supply': float(current_supply),
                'market_type': market.market_type,
                'bonding_curve_a': float(market.a),
                'bonding_curve_b': float(market.b),
                'created_at': market.created_at.isoformat() if market.created_at else None,
                'updated_at': market.updated_at.isoformat() if market.updated_at else None,
                'asset': asset_data,
                'event': event_data,
            })
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/portfolio', methods=['GET'])
def get_portfolio():
    """Get user's portfolio (all positions)."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        positions = Position.query.filter_by(user_id=user_id).options(
            joinedload(Position.market)
        ).all()
        
        # Batch fetch supplies for all markets (single query instead of N queries)
        market_ids = [p.market_id for p in positions if p.market_id]
        supply_map = get_supplies_batch(market_ids)
        
        result = []
        for position in positions:
            market = position.market
            if market:
                current_supply = supply_map.get(market.id, Decimal('0'))
                current_price = price(
                    current_supply,
                    Decimal(str(market.a)),
                    Decimal(str(market.b))
                )
                shares = float(position.shares)
                avg_entry = float(position.avg_entry_price)
                unrealized_pnl = (float(current_price) - avg_entry) * shares
            else:
                current_price = None
                unrealized_pnl = None
            
            result.append({
                'position_id': position.id,
                'market_id': position.market_id,
                'shares': float(position.shares),
                'avg_entry_price': float(position.avg_entry_price),
                'realized_pnl': float(position.realized_pnl),
                'current_price': float(current_price) if current_price else None,
                'unrealized_pnl': float(unrealized_pnl) if unrealized_pnl else None,
                'total_pnl': float(position.realized_pnl + (unrealized_pnl or 0)),
                'last_marked_at': position.last_marked_at.isoformat() if position.last_marked_at else None,
            })
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/wallet', methods=['GET'])
def get_wallet():
    """Get user's wallet balance."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        from services.wallet_service import WalletService
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


@bp.route('/wallet/ledger', methods=['GET'])
def get_ledger():
    """Get user's ledger history."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        limit = request.args.get('limit', default=100, type=int)
        transaction_type = request.args.get('type', type=str)
        
        from services.wallet_service import WalletService
        entries = WalletService.get_ledger_history(user_id, limit)
        
        if transaction_type:
            from db import TransactionType
            try:
                type_enum = TransactionType[transaction_type.upper()]
                entries = [e for e in entries if e.transaction_type == type_enum]
            except (KeyError, AttributeError):
                pass
        
        return jsonify([
            {
                'id': entry.id,
                'amount': float(entry.amount),
                'transaction_type': entry.transaction_type.value if hasattr(entry.transaction_type, 'value') else str(entry.transaction_type),
                'reference_type': entry.reference_type,
                'reference_id': entry.reference_id,
                'description': entry.description,
                'created_at': entry.created_at.isoformat() if entry.created_at else None,
            }
            for entry in entries
        ]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

