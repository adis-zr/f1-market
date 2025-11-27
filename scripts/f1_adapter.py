"""Adapter to sync F1 API data into generalized Event/EventResult models."""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, List
from db import (
    db, Sport, League, Season, Event, Participant, EventResult,
    ScoringRule, Asset, Market, MarketStatus, EventStatus, ResultStatus,
    SeasonStatus, AssetType, FormulaType
)
from f1.service import F1Service
from f1.utils import calculate_race_points, DEFAULT_F1_POINTS_RULES


class F1Adapter:
    """Adapter to sync F1 data into generalized market engine models."""
    
    F1_SPORT_CODE = "F1"
    F1_LEAGUE_NAME = "Formula 1"
    
    def __init__(self):
        """Initialize F1 adapter."""
        self.f1_service = F1Service()
    
    def get_or_create_sport(self) -> Sport:
        """Get or create F1 sport."""
        sport = Sport.query.filter_by(code=self.F1_SPORT_CODE).first()
        if not sport:
            sport = Sport(code=self.F1_SPORT_CODE, name="Formula 1")
            db.session.add(sport)
            db.session.commit()
        return sport
    
    def get_or_create_league(self, sport: Sport) -> League:
        """Get or create F1 league."""
        league = League.query.filter_by(
            sport_id=sport.id,
            name=self.F1_LEAGUE_NAME
        ).first()
        if not league:
            league = League(sport_id=sport.id, name=self.F1_LEAGUE_NAME)
            db.session.add(league)
            db.session.commit()
        return league
    
    def get_or_create_season(self, league: League, year: int) -> Season:
        """Get or create season."""
        season = Season.query.filter_by(league_id=league.id, year=year).first()
        if not season:
            season = Season(
                league_id=league.id,
                year=year,
                status=SeasonStatus.ACTIVE
            )
            db.session.add(season)
            db.session.commit()
        return season
    
    def sync_drivers(self, sport: Sport, season_year: int) -> Dict[int, Participant]:
        """
        Sync F1 drivers as Participants.
        
        Returns:
            Dict mapping driver_id (from F1 API) to Participant
        """
        standings = self.f1_service.get_driver_standings(season=season_year)
        if not standings:
            return {}
        
        driver_map = {}
        
        for driver_data in standings:
            if not isinstance(driver_data, dict):
                continue
            
            # Extract driver info
            driver_id = driver_data.get('id') or driver_data.get('driver_id')
            name = driver_data.get('name') or driver_data.get('full_name')
            
            if not driver_id or not name:
                continue
            
            # Check if participant already exists
            # We'll use metadata_json to store F1 driver_id
            participant = Participant.query.filter(
                Participant.sport_id == sport.id,
                Participant.metadata_json['f1_driver_id'].astext == str(driver_id)
            ).first()
            
            if not participant:
                # Create new participant
                short_code = driver_data.get('abbr') or name.split()[-1][:3].upper()
                participant = Participant(
                    sport_id=sport.id,
                    name=name,
                    short_code=short_code,
                    metadata_json={
                        'f1_driver_id': driver_id,
                        'team_id': driver_data.get('team_id'),
                        'nationality': driver_data.get('nationality'),
                        'date_of_birth': driver_data.get('date_of_birth')
                    }
                )
                db.session.add(participant)
            else:
                # Update existing participant
                participant.name = name
                if not participant.metadata_json:
                    participant.metadata_json = {}
                participant.metadata_json.update({
                    'f1_driver_id': driver_id,
                    'team_id': driver_data.get('team_id'),
                    'nationality': driver_data.get('nationality'),
                    'date_of_birth': driver_data.get('date_of_birth')
                })
            
            driver_map[driver_id] = participant
        
        db.session.commit()
        return driver_map
    
    def sync_race_to_event(
        self,
        season: Season,
        race_data: Dict,
        driver_map: Dict[int, Participant]
    ) -> Optional[Event]:
        """
        Sync a race from F1 API to Event model.
        
        Args:
            season: Season instance
            race_data: Race data from F1 API
            driver_map: Mapping of F1 driver_id to Participant
        
        Returns:
            Event instance or None
        """
        # Extract race info
        stage_id = race_data.get('id')
        name = race_data.get('name') or race_data.get('stage', {}).get('name')
        venue = race_data.get('venue') or race_data.get('stage', {}).get('venue')
        
        if not stage_id or not name:
            return None
        
        # Parse dates
        time_block = race_data.get('time') or {}
        start_at = None
        end_at = None
        
        if time_block.get('starting_at'):
            start_ts = time_block['starting_at'].get('timestamp')
            if start_ts:
                try:
                    start_at = datetime.utcfromtimestamp(int(start_ts))
                except Exception:
                    pass
        
        # Determine status
        status_str = (time_block.get('status') or '').lower()
        if status_str == 'finished':
            status = EventStatus.FINISHED
        elif status_str == 'live':
            status = EventStatus.LIVE
        else:
            status = EventStatus.UPCOMING
        
        # Get or create event
        # Use metadata_json to store F1 stage_id
        event = Event.query.filter(
            Event.season_id == season.id,
            Event.metadata_json['f1_stage_id'].astext == str(stage_id)
        ).first()
        
        if not event:
            event = Event(
                season_id=season.id,
                name=name,
                venue=venue,
                start_at=start_at,
                end_at=end_at,
                status=status,
                metadata_json={
                    'f1_stage_id': stage_id,
                    'round': race_data.get('round'),
                    'circuit': race_data.get('circuit') or race_data.get('stage', {}).get('venue')
                }
            )
            db.session.add(event)
        else:
            # Update existing event
            event.name = name
            event.venue = venue
            event.start_at = start_at
            event.end_at = end_at
            event.status = status
            if not event.metadata_json:
                event.metadata_json = {}
            event.metadata_json.update({
                'f1_stage_id': stage_id,
                'round': race_data.get('round'),
                'circuit': race_data.get('circuit') or race_data.get('stage', {}).get('venue')
            })
        
        db.session.commit()
        return event
    
    def sync_race_results(
        self,
        event: Event,
        race_data: Dict,
        driver_map: Dict[int, Participant]
    ) -> List[EventResult]:
        """
        Sync race results to EventResult models.
        
        Args:
            event: Event instance
            race_data: Race data from F1 API with results
            driver_map: Mapping of F1 driver_id to Participant
        
        Returns:
            List of EventResult instances
        """
        # Extract results
        results_block = race_data.get('results')
        if isinstance(results_block, dict) and isinstance(results_block.get('data'), list):
            results = results_block['data']
        elif isinstance(results_block, list):
            results = results_block
        else:
            return []
        
        # Calculate points for each result
        formatted_results = []
        for result in results:
            if not isinstance(result, dict):
                continue
            
            result_copy = result.copy()
            formatted_results.append(result_copy)
        
        # Calculate points using F1 utils
        calculate_race_points(formatted_results, DEFAULT_F1_POINTS_RULES)
        
        event_results = []
        
        for result in formatted_results:
            driver_id = result.get('driver_id') or result.get('id')
            if not driver_id:
                continue
            
            participant = driver_map.get(driver_id)
            if not participant:
                continue
            
            # Extract result data
            position = result.get('position')
            points = result.get('points', 0.0)
            retired = result.get('retired', False)
            
            # Determine status
            if retired:
                result_status = ResultStatus.DNF
            else:
                result_status = ResultStatus.FINISHED
            
            # Get or create EventResult
            event_result = EventResult.query.filter_by(
                event_id=event.id,
                participant_id=participant.id
            ).first()
            
            if not event_result:
                event_result = EventResult(
                    event_id=event.id,
                    participant_id=participant.id,
                    primary_score=Decimal(str(points)),
                    rank=position if position else None,
                    status=result_status,
                    metrics_json={
                        'f1_driver_id': driver_id,
                        'fastest_lap_time': result.get('fastest_lap_time') or result.get('best_lap_time'),
                        'retired': retired,
                        'laps': result.get('laps'),
                        'time': result.get('time')
                    }
                )
                db.session.add(event_result)
            else:
                # Update existing result
                event_result.primary_score = Decimal(str(points))
                event_result.rank = position if position else None
                event_result.status = result_status
                if not event_result.metrics_json:
                    event_result.metrics_json = {}
                event_result.metrics_json.update({
                    'f1_driver_id': driver_id,
                    'fastest_lap_time': result.get('fastest_lap_time') or result.get('best_lap_time'),
                    'retired': retired,
                    'laps': result.get('laps'),
                    'time': result.get('time')
                })
            
            event_results.append(event_result)
        
        db.session.commit()
        return event_results
    
    def get_or_create_scoring_rule(self, sport: Sport) -> ScoringRule:
        """Get or create default F1 scoring rule."""
        scoring_rule = ScoringRule.query.filter_by(
            sport_id=sport.id,
            code="F1_POINTS"
        ).first()
        
        if not scoring_rule:
            scoring_rule = ScoringRule(
                sport_id=sport.id,
                code="F1_POINTS",
                max_score=Decimal('25'),  # Max F1 points (1st place)
                alpha=Decimal('1.0'),  # Linear scaling
                beta=Decimal('0.0'),  # No baseline
                formula_type=FormulaType.LINEAR_NORMALIZED
            )
            db.session.add(scoring_rule)
            db.session.commit()
        
        return scoring_rule
    
    def sync_season(self, year: int) -> Dict:
        """
        Sync an entire F1 season.
        
        Args:
            year: Season year
        
        Returns:
            Dict with sync summary
        """
        try:
            # Get or create sport and league
            sport = self.get_or_create_sport()
            league = self.get_or_create_league(sport)
            season = self.get_or_create_season(league, year)
            
            # Sync drivers
            driver_map = self.sync_drivers(sport, year)
            
            # Get race results
            race_results = self.f1_service.get_last_race_results(season_year=year)
            # Note: This only gets the last race. For full sync, you'd need to
            # fetch all races for the season from the F1 API
            
            events_synced = 0
            results_synced = 0
            
            if race_results:
                # For now, we'll sync the last race
                # In production, you'd iterate through all races
                stage_data = race_results.get('stage') or {}
                if stage_data:
                    event = self.sync_race_to_event(season, stage_data, driver_map)
                    if event:
                        events_synced += 1
                        # Sync results if available
                        if race_results.get('results'):
                            results = self.sync_race_results(
                                event,
                                {'results': {'data': race_results['results']}},
                                driver_map
                            )
                            results_synced += len(results)
            
            return {
                'success': True,
                'season_year': year,
                'drivers_synced': len(driver_map),
                'events_synced': events_synced,
                'results_synced': results_synced
            }
        
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }

