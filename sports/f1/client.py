"""HTTP client for SportMonks F1 API."""
import requests
from typing import Dict, Optional, Any
from flask import current_app


class F1APIClient:
    """HTTP client for making requests to SportMonks F1 API."""

    def __init__(self):
        """Initialize the API client."""
        pass

    def get_base_url(self) -> str:
        """Get SportMonks F1 API base URL."""
        # Official base URL: https://f1.sportmonks.com/api/v1.0
        return current_app.config.get(
            "F1_SPORTSMONK_BASE_URL",
            "https://f1.sportmonks.com/api/v1.0",
        )

    def get_api_key(self) -> Optional[str]:
        """Get SportMonks API key from config."""
        return current_app.config.get("SPORTSMONK_API_KEY")

    def make_request(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        include_data: bool = True,
    ) -> Optional[Any]:
        """
        Make HTTP request to SportMonks F1 API.

        Args:
            endpoint: API endpoint path (e.g., '/drivers/season/10')
            params: Query parameters (API key will be added automatically)
            include_data: If True, extract 'data' field from response

        Returns:
            JSON response (usually the 'data' field) or None if error
        """
        api_key = self.get_api_key()
        if not api_key:
            print("SportMonks API key not configured")
            return None

        base_url = self.get_base_url()
        # Ensure endpoint starts with '/'
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
        url = f"{base_url}{endpoint}"

        if params is None:
            params = {}
        params["api_token"] = api_key

        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if include_data and isinstance(data, dict) and "data" in data:
                return data["data"]
            return data
        except requests.exceptions.RequestException as e:
            print(f"SportMonks API request error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    print("Error response:", e.response.json())
                except Exception:
                    print("Error response text:", e.response.text)
            return None

