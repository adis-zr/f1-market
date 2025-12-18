"""Abstract base class for sports data providers."""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class DataProvider(ABC):
    """
    Abstract interface for sports data providers.

    This interface defines the contract that all sports data providers must implement.
    Each sport (F1, NBA, etc.) should create a concrete implementation of this interface.
    """

    @abstractmethod
    def get_driver_standings(self, season: Optional[int] = None) -> Optional[List[Dict]]:
        """
        Get current driver/player championship standings for a season.

        Args:
            season: Season year (defaults to current year)

        Returns:
            List of driver/player standings dicts or None if error
        """
        pass

    @abstractmethod
    def get_constructor_standings(self, season: Optional[int] = None) -> Optional[List[Dict]]:
        """
        Get current constructor/team championship standings.

        Args:
            season: Season year (defaults to current year)

        Returns:
            List of constructor/team standings dicts or None if error
        """
        pass

    @abstractmethod
    def get_telemetry(self, session_key: Optional[int] = None) -> Optional[Dict]:
        """
        Get live event snapshot for the ongoing event (race/game).

        Args:
            session_key: Optional explicit session/game ID; if not provided,
                        uses the currently live session

        Returns:
            Dict containing event info + live data, or None if nothing live
        """
        pass

    @abstractmethod
    def is_race_ongoing(self) -> bool:
        """
        Check if any event (race/game) is currently live.

        Returns:
            True if an event is currently live, False otherwise
        """
        pass

    @abstractmethod
    def get_current_session_key(self) -> Optional[int]:
        """
        Get the session/game ID for the currently ongoing event, if any.

        Returns:
            Session/game ID or None if no event is ongoing
        """
        pass

    @abstractmethod
    def get_last_race_results(self, season_year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get the last finished event (race/game) with results.

        Args:
            season_year: Season year (defaults to current year)

        Returns:
            Formatted event results dict or None if not found
        """
        pass
