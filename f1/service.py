"""F1 API service for fetching standings and live race data using SportMonks F1 API."""
from typing import Dict, List, Optional, Any
from .client import F1APIClient
from .cache import Cache
from .seasons import SeasonService
from .standings import StandingsService
from .races import RaceService
from .teams import TeamService


class F1Service:
    """Service for interacting with SportMonks F1 API."""

    def __init__(self, provider: str = "sportmonks"):
        """
        Initialize F1 service with SportMonks provider.

        Args:
            provider: API provider (defaults to 'sportmonks')
        """
        self.provider = provider
        
        # Initialize core components
        self._client = F1APIClient()
        self._cache = Cache(provider=provider, ttl_minutes=10)
        self._season_service = SeasonService(self._client, self._cache)
        self._standings_service = StandingsService(
            self._client, self._cache, self._season_service
        )
        self._team_service = TeamService(self._client, self._cache)
        self._race_service = RaceService(self._client, self._season_service, self._team_service)

    # -------------------------------------------------------------------------
    # Standings: Drivers
    # -------------------------------------------------------------------------
    def get_driver_standings(
        self, season: Optional[int] = None
    ) -> Optional[List[Dict]]:
        """
        Get current driver championship standings for a season.

        Args:
            season: Season year (defaults to current year)

        Returns:
            List of driver standings dicts or None if error
        """
        return self._standings_service.get_driver_standings(season=season)

    # -------------------------------------------------------------------------
    # Standings: Constructors (Teams)
    # -------------------------------------------------------------------------
    def get_constructor_standings(
        self, season: Optional[int] = None
    ) -> Optional[List[Dict]]:
        """
        Get current constructor championship standings.

        Args:
            season: Season year (defaults to current year)

        Returns:
            List of constructor standings dicts or None if error
        """
        return self._standings_service.get_constructor_standings(season=season)

    # -------------------------------------------------------------------------
    # Teams
    # -------------------------------------------------------------------------
    def get_team_by_id(self, team_id: int) -> Optional[Dict]:
        """
        Get team data by team ID.

        Args:
            team_id: Team ID

        Returns:
            Team data dict or None if not found
        """
        return self._team_service.get_team_by_id(team_id)

    # -------------------------------------------------------------------------
    # Live race / "telemetry-ish" data
    # -------------------------------------------------------------------------
    def is_race_ongoing(self) -> bool:
        """
        Check if any race (stage) is currently live.

        Uses GET /livescores/now, which returns live stages with 'time.status'.
        """
        return self._race_service.is_race_ongoing()

    def get_current_session_key(self) -> Optional[int]:
        """Get the stage ID for the currently ongoing race, if any."""
        return self._race_service.get_current_session_key()

    def get_last_race_results(
        self, season_year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get the last finished race with results formatted for display.

        - Uses _get_latest_finished_race to find the most recent finished stage.
        - Splits results into:
            * results: classified finishers (non-retired), positions 1..N
            * dnf_results: retired / DNF / DSQ entries
        """
        return self._race_service.get_last_race_results(season_year=season_year)

    def get_telemetry(self, session_key: Optional[int] = None) -> Optional[Dict]:
        """
        Get live race snapshot for the ongoing race.

        This is NOT full car telemetry; SportMonks provides live 'results'
        per stage via /livescores/now. We expose that as a telemetry-like feed.

        Args:
            session_key: Optional explicit stage ID; if not provided, we use
                         the currently live stage from /livescores/now.

        Returns:
            Dict containing stage info + live results, or None if nothing live.
        """
        return self._race_service.get_telemetry(session_key=session_key)
