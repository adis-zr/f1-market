"""Team management for F1 API."""
from typing import Dict, Optional
from .client import F1APIClient
from .cache import Cache


class TeamService:
    """Service for managing F1 teams."""

    def __init__(self, client: F1APIClient, cache: Cache):
        """
        Initialize team service.

        Args:
            client: F1 API client instance
            cache: Cache instance
        """
        self.client = client
        self.cache = cache

    def get_team_by_id(self, team_id: int) -> Optional[Dict]:
        """
        Get team data by team ID.

        Uses GET /teams/{ID} endpoint.

        Args:
            team_id: Team ID

        Returns:
            Team data dict with fields: id, name, engine, chassis, color_code,
            base, team_lead, technical_lead, image_path, or None if not found
        """
        if team_id is None:
            return None

        cache_key = f"team:{team_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        team_data = self.client.make_request(f"/teams/{team_id}")
        if not team_data:
            return None

        # Cache the result if we got valid data
        if isinstance(team_data, dict):
            self.cache.set(cache_key, team_data)
            return team_data

        return None

