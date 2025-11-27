"""Championship standings for F1 API."""
from typing import Dict, List, Optional
from datetime import datetime
from .client import F1APIClient
from .cache import Cache
from .seasons import SeasonService


class StandingsService:
    """Service for fetching driver and constructor championship standings."""

    def __init__(self, client: F1APIClient, cache: Cache, season_service: SeasonService):
        """
        Initialize standings service.

        Args:
            client: F1 API client instance
            cache: Cache instance
            season_service: Season service instance
        """
        self.client = client
        self.cache = cache
        self.season_service = season_service

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
        if season is None:
            season = datetime.now().year

        cache_key = f"driver_standings:{season}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        result = self._get_driver_standings_sportmonks(season)
        if result:
            self.cache.set(cache_key, result)
        return result

    def _get_driver_standings_sportmonks(
        self, season: int
    ) -> Optional[List[Dict]]:
        """
        Get driver standings from SportMonks F1 API.

        Uses GET /drivers/season/{ID}, where ID is the season ID.

        Args:
            season: Season year

        Returns:
            List of driver standings or None if error
        """
        season_id = self.season_service.get_season_id(season)
        if not season_id:
            print(f"Could not resolve SportMonks season ID for {season}")
            return None

        # Optionally you can use 'include=driver' to enrich with full driver info.
        rows = self.client.make_request(
            f"/drivers/season/{season_id}", params={"include": "driver"}
        )
        if not rows:
            return None

        standings: List[Dict] = []
        for row in rows:
            if not isinstance(row, dict):
                continue

            driver_id = row.get("driver_id")
            team_id = row.get("team_id")
            position = row.get("position")
            points = row.get("points")

            # Try to get driver name if included
            driver_obj = row.get("driver")
            if isinstance(driver_obj, dict) and "data" in driver_obj and isinstance(driver_obj["data"], dict):
                driver_obj = driver_obj["data"]

            if isinstance(driver_obj, dict):
                driver_name = (
                    driver_obj.get("name")
                    or driver_obj.get("full_name")
                    or f"{driver_obj.get('first_name', '')} {driver_obj.get('last_name', '')}".strip()
                )
            else:
                driver_name = None

            standings.append(
                {
                    "position": int(position) if position is not None else None,
                    "driver_id": str(driver_id) if driver_id is not None else "",
                    "driver_name": driver_name or "",
                    "points": float(points) if points is not None else 0.0,
                    "wins": None,  # SportMonks doesn't expose wins directly here
                    "constructor_id": str(team_id) if team_id is not None else "",
                }
            )

        # Sort by position just to be safe
        standings.sort(key=lambda s: (s["position"] if s["position"] is not None else 999))
        return standings or None

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
        if season is None:
            season = datetime.now().year

        cache_key = f"constructor_standings:{season}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        result = self._get_constructor_standings_sportmonks(season)
        if result:
            self.cache.set(cache_key, result)
        return result

    def _get_constructor_standings_sportmonks(
        self, season: int
    ) -> Optional[List[Dict]]:
        """
        Get constructor standings from SportMonks F1 API.

        Uses GET /teams/season/{ID}, which returns 'points' and 'position'.

        Args:
            season: Season year

        Returns:
            List of constructor standings or None if error
        """
        season_id = self.season_service.get_season_id(season)
        if not season_id:
            print(f"Could not resolve SportMonks season ID for {season}")
            return None

        rows = self.client.make_request(f"/teams/season/{season_id}")
        if not rows:
            return None

        standings: List[Dict] = []
        for row in rows:
            if not isinstance(row, dict):
                continue

            constructor_id = row.get("team_id") or row.get("id")
            constructor_name = row.get("name") or ""
            position = row.get("position")
            points = row.get("points")

            standings.append(
                {
                    "position": int(position) if position is not None else None,
                    "constructor_id": str(constructor_id) if constructor_id is not None else "",
                    "constructor_name": constructor_name,
                    "points": float(points) if points is not None else 0.0,
                    "wins": None,  # not directly exposed here
                }
            )

        standings.sort(key=lambda s: (s["position"] if s["position"] is not None else 999))
        return standings or None

