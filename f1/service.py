"""F1 API service for fetching standings and live race data using SportMonks F1 API."""
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from flask import current_app


class F1Service:
    """Service for interacting with SportMonks F1 API."""

    def __init__(self, provider: str = "sportmonks"):
        """
        Initialize F1 service with SportMonks provider.

        Args:
            provider: API provider (defaults to 'sportmonks')
        """
        self.provider = provider
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        # Standings + seasons don't change during a session, so 10min cache is fine
        self._cache_ttl = timedelta(minutes=10)

    # -------------------------------------------------------------------------
    # Low-level HTTP + config
    # -------------------------------------------------------------------------
    def _get_sportmonks_base_url(self) -> str:
        """Get SportMonks F1 API base URL."""
        # Official base URL: https://f1.sportmonks.com/api/v1.0 :contentReference[oaicite:3]{index=3}
        return current_app.config.get(
            "F1_SPORTSMONK_BASE_URL",
            "https://f1.sportmonks.com/api/v1.0",
        )

    def _get_api_key(self) -> Optional[str]:
        """Get SportMonks API key from config."""
        return current_app.config.get("SPORTSMONK_API_KEY")

    def _make_request(
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
        api_key = self._get_api_key()
        if not api_key:
            print("SportMonks API key not configured")
            return None

        base_url = self._get_sportmonks_base_url()
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

    # -------------------------------------------------------------------------
    # Simple in-memory cache
    # -------------------------------------------------------------------------
    def _get_cache_key(self, key: str) -> str:
        return f"{self.provider}:{key}"

    def _get_cached(self, key: str) -> Optional[Any]:
        cache_key = self._get_cache_key(key)
        if cache_key in self._cache:
            ts = self._cache_timestamps.get(cache_key)
            if ts and datetime.utcnow() - ts < self._cache_ttl:
                return self._cache[cache_key]
            # expired
            self._cache.pop(cache_key, None)
            self._cache_timestamps.pop(cache_key, None)
        return None

    def _set_cached(self, key: str, value: Any):
        cache_key = self._get_cache_key(key)
        self._cache[cache_key] = value
        self._cache_timestamps[cache_key] = datetime.utcnow()

    # -------------------------------------------------------------------------
    # Seasons
    # -------------------------------------------------------------------------
    def _get_season_id(self, season_year: int) -> Optional[int]:
        """
        Map a year (e.g. 2025) to SportMonks season ID.

        Uses GET /seasons, then matches on 'name' == "2025". :contentReference[oaicite:4]{index=4}
        """
        cache_key = f"season_id:{season_year}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        seasons = self._make_request("/seasons")
        if not seasons:
            return None

        for season in seasons:
            # Example: { "id": 10, "name": "2025" }
            if str(season.get("name")) == str(season_year):
                season_id = season.get("id")
                if season_id is not None:
                    self._set_cached(cache_key, season_id)
                    return season_id

        return None

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
        if season is None:
            season = datetime.now().year

        cache_key = f"driver_standings:{season}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        result = self._get_driver_standings_sportmonks(season)
        if result:
            self._set_cached(cache_key, result)
        return result

    def _get_driver_standings_sportmonks(
        self, season: int
    ) -> Optional[List[Dict]]:
        """
        Get driver standings from SportMonks F1 API.

        Uses GET /drivers/season/{ID}, where ID is the season ID. :contentReference[oaicite:5]{index=5}
        """
        season_id = self._get_season_id(season)
        if not season_id:
            print(f"Could not resolve SportMonks season ID for {season}")
            return None

        # Optionally you can use 'include=driver' to enrich with full driver info.
        rows = self._make_request(f"/drivers/season/{season_id}", params={"include": "driver"})
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
        if season is None:
            season = datetime.now().year

        cache_key = f"constructor_standings:{season}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        result = self._get_constructor_standings_sportmonks(season)
        if result:
            self._set_cached(cache_key, result)
        return result

    def _get_constructor_standings_sportmonks(
        self, season: int
    ) -> Optional[List[Dict]]:
        """
        Get constructor standings from SportMonks F1 API.

        Uses GET /teams/season/{ID}, which returns 'points' and 'position'. :contentReference[oaicite:6]{index=6}
        """
        season_id = self._get_season_id(season)
        if not season_id:
            print(f"Could not resolve SportMonks season ID for {season}")
            return None

        rows = self._make_request(f"/teams/season/{season_id}")
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

    # -------------------------------------------------------------------------
    # Live race / "telemetry-ish" data
    # -------------------------------------------------------------------------
    def is_race_ongoing(self) -> bool:
        """
        Check if any race (stage) is currently live.

        Uses GET /livescores/now, which returns live stages with 'time.status'. :contentReference[oaicite:7]{index=7}
        """
        now = datetime.utcnow()
        livescores = self._make_request("/livescores/now")
        if not livescores:
            return False

        if not isinstance(livescores, list):
            livescores = [livescores]

        for stage in livescores:
            if self._is_stage_live(stage, now):
                return True

        return False

    def _is_stage_live(self, stage: Dict, now: datetime) -> bool:
        """Determine if a stage object from livescores is currently live."""
        if not isinstance(stage, dict):
            return False

        time_block = stage.get("time") or {}
        status = (time_block.get("status") or "").lower()
        if status == "live":
            return True

        # Fallback: check timestamps if present
        starting_at = time_block.get("starting_at") or {}
        ts = starting_at.get("timestamp")
        if ts is not None:
            try:
                start = datetime.utcfromtimestamp(int(ts))
                # Races are ~2h; treat 3h as a safe window
                if 0 <= (now - start).total_seconds() <= 3 * 3600:
                    return True
            except Exception:
                pass

        return False

    def _get_current_stage(self) -> Optional[Dict]:
        """
        Return the current live stage object (if any) from /livescores/now.
        """
        now = datetime.utcnow()
        livescores = self._make_request("/livescores/now")
        if not livescores:
            return None

        if not isinstance(livescores, list):
            livescores = [livescores]

        for stage in livescores:
            if self._is_stage_live(stage, now):
                return stage

        return None

    def _get_latest_finished_race(self, season_year: Optional[int] = None) -> Optional[Dict]:
        """
        Get the most recent finished race (stage with name 'Race' and status 'Finished')
        for the given season year (defaults to current year).

        Uses: GET /stages/season/{season_ID} with results included by default. :contentReference[oaicite:0]{index=0}
        """
        if season_year is None:
            season_year = datetime.utcnow().year

        season_id = self._get_season_id(season_year)
        if not season_id:
            print(f"Could not resolve SportMonks season ID for {season_year}")
            return None

        stages = self._make_request(f"/stages/season/{season_id}")
        if not stages:
            return None

        if not isinstance(stages, list):
            stages = [stages]

        latest_stage = None
        latest_ts = None

        for stage in stages:
            if not isinstance(stage, dict):
                continue

            # We only care about actual races
            if str(stage.get("name", "")).lower() != "race":
                continue

            time_block = stage.get("time") or {}
            status = str(time_block.get("status", "")).lower()
            if status != "finished":
                continue

            starting_at = time_block.get("starting_at") or {}
            ts = starting_at.get("timestamp")
            if ts is None:
                continue

            try:
                ts = int(ts)
            except (TypeError, ValueError):
                continue

            if latest_ts is None or ts > latest_ts:
                latest_ts = ts
                latest_stage = stage

        return latest_stage

    def get_current_session_key(self) -> Optional[int]:
        """Get the stage ID for the currently ongoing race, if any."""
        stage = self._get_current_stage()
        if not stage:
            return None
        return stage.get("id")

    def get_last_race_results(
        self, season_year: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Get the last finished race with results formatted for display.

        Args:
            season_year: Season year (defaults to current year)

        Returns:
            Dict containing race info and results, or None if no finished race found
        """
        stage = self._get_latest_finished_race(season_year)
        if not stage:
            return None

        # Extract results from stage
        results_block = stage.get("results")
        if isinstance(results_block, dict) and isinstance(results_block.get("data"), list):
            results = results_block["data"]
        elif isinstance(results_block, list):
            results = results_block
        else:
            results = []

        # Format results for display
        formatted_results = []
        for result in results:
            if not isinstance(result, dict):
                continue

            # Extract driver info
            driver_obj = result.get("driver")
            if isinstance(driver_obj, dict) and "data" in driver_obj:
                driver_obj = driver_obj["data"]
            
            driver_name = None
            if isinstance(driver_obj, dict):
                driver_name = (
                    driver_obj.get("name")
                    or driver_obj.get("full_name")
                    or f"{driver_obj.get('first_name', '')} {driver_obj.get('last_name', '')}".strip()
                )

            # Extract constructor info
            team_obj = result.get("team") or result.get("constructor")
            if isinstance(team_obj, dict) and "data" in team_obj:
                team_obj = team_obj["data"]
            
            constructor_name = None
            if isinstance(team_obj, dict):
                constructor_name = team_obj.get("name") or ""

            formatted_results.append({
                "position": result.get("position"),
                "driver_id": str(result.get("driver_id", "")),
                "driver_name": driver_name or "",
                "constructor_id": str(result.get("team_id", "")),
                "constructor_name": constructor_name or "",
                "points": float(result.get("points", 0)) if result.get("points") is not None else 0.0,
                "time": result.get("time") or result.get("race_time"),
            })

        # Sort by position
        formatted_results.sort(key=lambda r: (r["position"] if r["position"] is not None else 999))

        # Extract race metadata
        time_block = stage.get("time") or {}
        starting_at = time_block.get("starting_at") or {}

        return {
            "stage_id": stage.get("id"),
            "race_name": stage.get("name") or "Race",
            "track_id": stage.get("track_id"),
            "season_id": stage.get("season_id"),
            "date": starting_at.get("date") if isinstance(starting_at, dict) else None,
            "timestamp": starting_at.get("timestamp") if isinstance(starting_at, dict) else None,
            "results": formatted_results,
        }

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
        now = datetime.utcnow()
        livescores = self._make_request("/livescores/now")
        if not livescores:
            return None

        if not isinstance(livescores, list):
            livescores = [livescores]

        chosen_stage: Optional[Dict] = None
        for stage in livescores:
            if not isinstance(stage, dict):
                continue

            stage_id = stage.get("id")
            if session_key is not None and stage_id == session_key:
                chosen_stage = stage
                break

            if session_key is None and self._is_stage_live(stage, now):
                chosen_stage = stage
                break

        if not chosen_stage:
            return None

        # results are returned inside stage["results"]["data"] in docs :contentReference[oaicite:8]{index=8}
        results_block = chosen_stage.get("results")
        if isinstance(results_block, dict) and isinstance(results_block.get("data"), list):
            results = results_block["data"]
        else:
            results = results_block if isinstance(results_block, list) else []

        return {
            "stage_id": chosen_stage.get("id"),
            "race_name": chosen_stage.get("name"),
            "track_id": chosen_stage.get("track_id"),
            "season_id": chosen_stage.get("season_id"),
            "time": chosen_stage.get("time"),
            "results": results,
            "timestamp": datetime.utcnow().isoformat(),
        }
