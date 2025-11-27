"""Race-related functionality for F1 API."""
from typing import Dict, List, Optional, Any
from datetime import datetime
from .client import F1APIClient
from .seasons import SeasonService
from .teams import TeamService
from .utils import calculate_race_points, DEFAULT_F1_POINTS_RULES


class RaceService:
    """Service for race data, telemetry, and live race detection."""

    def __init__(self, client: F1APIClient, season_service: SeasonService, team_service: TeamService):
        """
        Initialize race service.

        Args:
            client: F1 API client instance
            season_service: Season service instance
            team_service: Team service instance
        """
        self.client = client
        self.season_service = season_service
        self.team_service = team_service

    def is_race_ongoing(self) -> bool:
        """
        Check if any race (stage) is currently live.

        Uses GET /livescores/now, which returns live stages with 'time.status'.

        Returns:
            True if a race is currently live, False otherwise
        """
        now = datetime.utcnow()
        livescores = self.client.make_request("/livescores/now")
        if not livescores:
            return False

        if not isinstance(livescores, list):
            livescores = [livescores]

        for stage in livescores:
            if self._is_stage_live(stage, now):
                return True

        return False

    def _is_stage_live(self, stage: Dict, now: datetime) -> bool:
        """
        Determine if a stage object from livescores is currently live.

        Args:
            stage: Stage object from API
            now: Current UTC datetime

        Returns:
            True if stage is live, False otherwise
        """
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

        Returns:
            Current live stage dict or None if no live stage
        """
        now = datetime.utcnow()
        livescores = self.client.make_request("/livescores/now")
        if not livescores:
            return None

        if not isinstance(livescores, list):
            livescores = [livescores]

        for stage in livescores:
            if self._is_stage_live(stage, now):
                return stage

        return None

    def get_current_session_key(self) -> Optional[int]:
        """
        Get the stage ID for the currently ongoing race, if any.

        Returns:
            Stage ID or None if no race is ongoing
        """
        stage = self._get_current_stage()
        if not stage:
            return None
        return stage.get("id")

    def _get_latest_finished_race(self, season_year: Optional[int] = None) -> Optional[Dict]:
        """
        Get the latest finished race stage.

        Args:
            season_year: Season year (defaults to current year)

        Returns:
            Latest finished race stage dict or None if not found
        """
        if season_year is None:
            season_year = datetime.utcnow().year

        season_id = self.season_service.get_season_id(season_year)
        if not season_id:
            return None

        stages = self.client.make_request(
            f"/stages/season/{season_id}", params={"include": "results"}
        )
        if not stages:
            return None

        if isinstance(stages, dict) and "data" in stages:
            stages = stages["data"] or []

        if not isinstance(stages, list):
            stages = [stages]

        latest_stage = None
        latest_ts = None

        for stage in stages:
            if not isinstance(stage, dict):
                continue

            stage_name = str(stage.get("name", "")).lower()

            # We only care about actual races
            if stage_name != "race":
                continue

            time_block = stage.get("time") or {}
            status_raw = time_block.get("status", "")
            status = str(status_raw).lower()

            finished_statuses = ["finished", "ft", "completed", "done", "closed"]
            is_finished = status in finished_statuses

            starting_at = time_block.get("starting_at") or {}
            ts = starting_at.get("timestamp")
            ts_int = None
            has_past_timestamp = False

            if ts is not None:
                try:
                    ts_int = int(ts)
                    race_time = datetime.utcfromtimestamp(ts_int)
                    if (datetime.utcnow() - race_time).total_seconds() > 2 * 3600:
                        has_past_timestamp = True
                except (TypeError, ValueError):
                    pass

            has_results = False
            results_data = stage.get("results")
            if isinstance(results_data, dict):
                has_results = bool((results_data.get("data") or []))
            elif isinstance(results_data, list):
                has_results = len(results_data) > 0

            # Consider it finished if status says so, OR if it's in the past and has results
            if not is_finished and not (has_past_timestamp and has_results):
                continue

            if ts_int is None:
                continue

            print("Stage: ", stage.get('city'), " ts_int: ", ts_int)

            if latest_ts is None or ts_int > latest_ts:
                latest_ts = ts_int
                latest_stage = stage

        return latest_stage

    def get_last_race_results(
        self, season_year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
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
        stage = self._get_latest_finished_race(season_year)
        if not stage:
            return None

        # Extract results from stage
        results_block = stage.get("results")
        if isinstance(results_block, dict) and isinstance(results_block.get("data"), list):
            results: List[Dict[str, Any]] = results_block["data"]
        elif isinstance(results_block, list):
            results = results_block
        else:
            results = []

        # Collect unique team_ids and fetch team data
        unique_team_ids = set()
        for result in results:
            if isinstance(result, dict):
                team_id = result.get("team_id")
                if team_id is not None:
                    unique_team_ids.add(team_id)

        # Fetch team data for all unique team_ids and create mapping
        team_name_map: Dict[int, str] = {}
        for team_id in unique_team_ids:
            team_data = self.team_service.get_team_by_id(team_id)
            if team_data and isinstance(team_data, dict):
                team_name = team_data.get("name") or ""
                team_name_map[team_id] = team_name

        formatted_results: List[Dict[str, Any]] = []

        for result in results:
            if not isinstance(result, dict):
                continue

            # Extract driver info from driver.data
            driver_obj = result.get("driver")
            if isinstance(driver_obj, dict) and "data" in driver_obj:
                driver_obj = driver_obj["data"]

            driver_name = ""
            if isinstance(driver_obj, dict):
                raw_name = driver_obj.get("name") or driver_obj.get("full_name") or ""
                if raw_name and "(" in raw_name:
                    raw_name = raw_name.split("(")[0].strip()
                driver_name = raw_name

            team_id = result.get("team_id")
            driver_id = result.get("driver_id")
            retired = bool(result.get("retired"))
            laps = result.get("laps")
            raw_position = result.get("position")

            # Get constructor name from team mapping
            constructor_name = ""
            if team_id is not None and team_id in team_name_map:
                constructor_name = team_name_map[team_id]

            # Extract fastest lap information (check various possible field names)
            fastest_lap = result.get("fastest_lap", False)
            has_fastest_lap = result.get("has_fastest_lap", False)
            fastest_lap_time = result.get("fastest_lap_time")
            best_lap_time = result.get("best_lap_time")

            formatted_results.append({
                # Raw provider-supplied position
                "position_raw": raw_position,
                # Final display position (we'll overwrite for classified finishers)
                "position": raw_position,
                "driver_id": str(driver_id) if driver_id is not None else "",
                "driver_name": driver_name,
                "constructor_id": str(team_id) if team_id is not None else "",
                "constructor_name": constructor_name,
                "points": 0.0,  # Will be calculated by calculate_race_points
                "time": result.get("driver_time") or result.get("driver_time_int"),
                "retired": retired,
                "laps": laps,
                # Fastest lap indicators (for points calculation)
                "fastest_lap": fastest_lap,
                "has_fastest_lap": has_fastest_lap or fastest_lap,
                "fastest_lap_time": fastest_lap_time,
                "best_lap_time": best_lap_time,
            })

        # Split into classified vs DNF/retired
        classified = [r for r in formatted_results if not r["retired"]]
        dnfs = [r for r in formatted_results if r["retired"]]

        # --- Classified (finishers) ---
        if classified:
            # Sort by provider raw position
            classified.sort(
                key=lambda r: r["position_raw"] if r["position_raw"] is not None else 999
            )
            # Renumber 1..N for clean table
            for idx, r in enumerate(classified, start=1):
                r["position"] = idx

            # Calculate points based on position and fastest lap
            classified = calculate_race_points(classified, DEFAULT_F1_POINTS_RULES)
        # else: leave empty; no finishers somehow

        # --- DNFs / DSQs / retired ---
        # Sort DNFs in a sensible way:
        #   - first by laps (desc: those who ran further appear earlier)
        #   - then by raw position as secondary tie-breaker
        if dnfs:
            dnfs.sort(
                key=lambda r: (
                    -(r["laps"] or 0),
                    r["position_raw"] if r["position_raw"] is not None else 999
                )
            )

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
            # Main classified results table
            "results": classified,
            # Separate DNF / retired / DSQ block for display at the bottom
            "dnf_results": dnfs,
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
        livescores = self.client.make_request("/livescores/now")
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

        # results are returned inside stage["results"]["data"] in docs
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

