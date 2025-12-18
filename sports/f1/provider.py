"""F1 data provider implementation."""
from typing import Dict, List, Optional, Any
from ..base import DataProvider
from .service import F1Service


class F1DataProvider(DataProvider):
    """
    F1-specific implementation of the DataProvider interface.

    This class wraps the existing F1Service functionality and provides
    a consistent interface that can be used interchangeably with other
    sports data providers.
    """

    def __init__(self, provider: str = "sportmonks"):
        """
        Initialize F1 data provider.

        Args:
            provider: API provider (defaults to 'sportmonks')
        """
        self._service = F1Service(provider=provider)

    def get_driver_standings(self, season: Optional[int] = None) -> Optional[List[Dict]]:
        """
        Get current driver championship standings for a season.

        Args:
            season: Season year (defaults to current year)

        Returns:
            List of driver standings dicts or None if error
        """
        return self._service.get_driver_standings(season=season)

    def get_constructor_standings(self, season: Optional[int] = None) -> Optional[List[Dict]]:
        """
        Get current constructor championship standings.

        Args:
            season: Season year (defaults to current year)

        Returns:
            List of constructor standings dicts or None if error
        """
        return self._service.get_constructor_standings(season=season)

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
        return self._service.get_telemetry(session_key=session_key)

    def is_race_ongoing(self) -> bool:
        """
        Check if any race (stage) is currently live.

        Uses GET /livescores/now, which returns live stages with 'time.status'.

        Returns:
            True if a race is currently live, False otherwise
        """
        return self._service.is_race_ongoing()

    def get_current_session_key(self) -> Optional[int]:
        """
        Get the stage ID for the currently ongoing race, if any.

        Returns:
            Stage ID or None if no race is ongoing
        """
        return self._service.get_current_session_key()

    def get_last_race_results(self, season_year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get the last finished race with results formatted for display.

        - Uses _get_latest_finished_race to find the most recent finished stage.
        - Splits results into:
            * results: classified finishers (non-retired), positions 1..N
            * dnf_results: retired / DNF / DSQ entries

        Args:
            season_year: Season year (defaults to current year)

        Returns:
            Formatted race results dict or None if not found
        """
        return self._service.get_last_race_results(season_year=season_year)

    # Additional F1-specific methods can be exposed here if needed
    def get_team_by_id(self, team_id: int) -> Optional[Dict]:
        """
        Get team data by team ID.

        This is an F1-specific method not part of the general DataProvider interface.

        Args:
            team_id: Team ID

        Returns:
            Team data dict or None if not found
        """
        return self._service.get_team_by_id(team_id)
