"""Season management for F1 API."""
from typing import Optional
from .client import F1APIClient
from .cache import Cache


class SeasonService:
    """Service for managing F1 seasons."""

    def __init__(self, client: F1APIClient, cache: Cache):
        """
        Initialize season service.

        Args:
            client: F1 API client instance
            cache: Cache instance
        """
        self.client = client
        self.cache = cache

    def get_season_id(self, season_year: int) -> Optional[int]:
        """
        Map a year (e.g. 2025) to SportMonks season ID.

        Uses GET /seasons, then matches on 'name' == "2025".

        Args:
            season_year: Year of the season (e.g., 2025)

        Returns:
            Season ID or None if not found
        """
        cache_key = f"season_id:{season_year}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        seasons = self.client.make_request("/seasons")
        if not seasons:
            return None

        for season in seasons:
            # Example: { "id": 10, "name": "2025" }
            if str(season.get("name")) == str(season_year):
                season_id = season.get("id")
                if season_id is not None:
                    self.cache.set(cache_key, season_id)
                    return season_id

        return None

