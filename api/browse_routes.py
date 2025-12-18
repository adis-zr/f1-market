"""Browse API routes for sports, leagues, seasons, events, and markets."""
from decimal import Decimal
from typing import Dict, List
from flask import Blueprint, request, jsonify
from sqlalchemy import func
from db import (
    db, Sport, League, Season, Event, Market, Asset, Position, Wallet, LedgerEntry,
    EventResult, Participant
)
from sqlalchemy.orm import joinedload
from pricing.bonding_curve import price
from auth.helpers import get_current_user_id
from config import MAX_QUERY_LIMIT

bp = Blueprint('browse', __name__, url_prefix='/api')


def _serialize_enum(value):
    """
    Serialize enum values consistently.

    Args:
        value: An enum value or regular value

    Returns:
        The enum's value attribute if it exists, otherwise string representation
    """
    return value.value if hasattr(value, 'value') else str(value)


def _format_market_response(market, supply, current_price):
    """
    Format a market object into a response dictionary.

    Args:
        market: Market database object
        supply: Current supply (Decimal)
        current_price: Current price (Decimal)

    Returns:
        Dictionary containing formatted market data
    """
    asset_data = None
    if market.asset:
        asset_data = {
            'id': market.asset.id,
            'type': _serialize_enum(market.asset.type),
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
            'status': _serialize_enum(market.event.status),
        }

    return {
        'market_id': market.id,
        'event_id': market.event_id,
        'asset_id': market.asset_id,
        'status': _serialize_enum(market.status),
        'current_price': float(current_price),
        'current_supply': float(supply),
        'market_type': market.market_type,
        'asset': asset_data,
        'event': event_data,
    }


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
                'status': _serialize_enum(season.status),
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
        limit = request.args.get('limit', default=100, type=int)
        limit = max(1, min(limit, MAX_QUERY_LIMIT))

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
                valid_statuses = [s.name.lower() for s in EventStatus]
                return jsonify({
                    'error': f'Invalid status. Valid values: {", ".join(valid_statuses)}'
                }), 400

        events = query.limit(limit).all()
        return jsonify([
            {
                'id': event.id,
                'season_id': event.season_id,
                'name': event.name,
                'venue': event.venue,
                'start_at': event.start_at.isoformat() if event.start_at else None,
                'end_at': event.end_at.isoformat() if event.end_at else None,
                'status': _serialize_enum(event.status),
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

            result.append(_format_market_response(market, current_supply, current_price))

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
                'status': _serialize_enum(result.status),
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
        limit = request.args.get('limit', default=100, type=int)
        limit = max(1, min(limit, MAX_QUERY_LIMIT))

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
                valid_statuses = [s.name.lower() for s in MarketStatus]
                return jsonify({
                    'error': f'Invalid status. Valid values: {", ".join(valid_statuses)}'
                }), 400

        markets = query.limit(limit).all()

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

            # Get base market response and add additional fields
            market_data = _format_market_response(market, current_supply, current_price)
            market_data.update({
                'bonding_curve_a': float(market.a),
                'bonding_curve_b': float(market.b),
                'created_at': market.created_at.isoformat() if market.created_at else None,
                'updated_at': market.updated_at.isoformat() if market.updated_at else None,
            })

            result.append(market_data)

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
            
            realized = float(position.realized_pnl)
            unrealized = float(unrealized_pnl) if unrealized_pnl else 0.0
            result.append({
                'position_id': position.id,
                'market_id': position.market_id,
                'shares': float(position.shares),
                'avg_entry_price': float(position.avg_entry_price),
                'realized_pnl': realized,
                'current_price': float(current_price) if current_price else None,
                'unrealized_pnl': unrealized if unrealized_pnl else None,
                'total_pnl': realized + unrealized,
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
        limit = max(1, min(limit, MAX_QUERY_LIMIT))  # Ensure positive limit, cap to prevent excessive queries
        transaction_type = request.args.get('type', type=str)

        from services.wallet_service import WalletService
        entries = WalletService.get_ledger_history(user_id, limit)
        
        if transaction_type:
            from db import TransactionType
            try:
                type_enum = TransactionType[transaction_type.upper()]
                entries = [e for e in entries if e.transaction_type == type_enum]
            except (KeyError, AttributeError):
                valid_types = [t.name.lower() for t in TransactionType]
                return jsonify({
                    'error': f'Invalid transaction type. Valid values: {", ".join(valid_types)}'
                }), 400
        
        return jsonify([
            {
                'id': entry.id,
                'amount': float(entry.amount),
                'transaction_type': _serialize_enum(entry.transaction_type),
                'reference_type': entry.reference_type,
                'reference_id': entry.reference_id,
                'description': entry.description,
                'created_at': entry.created_at.isoformat() if entry.created_at else None,
            }
            for entry in entries
        ]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

