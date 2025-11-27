"""Utility functions for F1 data processing (points + fastest lap)."""

from typing import Dict, List, Any, Optional


# Default F1 points system (2010+): positions 1-10
DEFAULT_F1_POINTS_RULES: Dict[int, float] = {
    1: 25.0,
    2: 18.0,
    3: 15.0,
    4: 12.0,
    5: 10.0,
    6: 8.0,
    7: 6.0,
    8: 4.0,
    9: 2.0,
    10: 1.0,
}


def _parse_lap_time(time_str: Optional[str]) -> Optional[float]:
    """
    Parse a lap time string like '1:33.365' into total seconds.

    Supports 'M:SS.mmm' or 'MM:SS.mmm' formats (e.g. '1:6.023' or '1:06.023').

    Args:
        time_str: Lap time string, or None/empty.

    Returns:
        Total seconds as float if parsing succeeds; otherwise None.
    """
    if not time_str:
        return None

    try:
        minutes_str, seconds_str = time_str.split(":")
        minutes = int(minutes_str)
        seconds = float(seconds_str)
        return minutes * 60.0 + seconds
    except Exception:
        return None


def calculate_race_points(
    results: List[Dict[str, Any]],
    points_rules: Dict[int, float] = DEFAULT_F1_POINTS_RULES,
    fastest_lap_bonus: float = 1.0,
    fastest_lap_top_n_only: int = 10,
) -> List[Dict[str, Any]]:
    """
    Calculate race points for each driver based on finishing position and fastest lap.

    This version computes the fastest lap itself from lap times and awards the
    bonus to a single driver only.

    Expected input per result dict:
        - 'position' (int or str): finishing position (1 = winner, etc.)
        - 'retired' (bool, optional): True if driver DNF/retired
        - 'fastest_lap_time' or 'best_lap_time' (str, optional):
              Lap time as 'M:SS.mmm', e.g. '1:33.365'

    Args:
        results:
            List of driver result dictionaries. This function mutates each dict
            in-place and also returns the same list.
        points_rules:
            Mapping from finishing position (int) to base points (float).
            Defaults to DEFAULT_F1_POINTS_RULES (2010+ F1 scoring).
        fastest_lap_bonus:
            Points awarded to the SINGLE driver with the fastest lap,
            provided they satisfy the position rule (see fastest_lap_top_n_only).
            Use 0.0 to disable the bonus entirely.
        fastest_lap_top_n_only:
            Only drivers finishing in positions <= this value are eligible
            for the fastest lap bonus (F1 rule: top 10).

    Returns:
        The same list of result dicts, each with a new 'points' field set.
    """
    # First pass: assign base points based on position and retirement.
    for result in results:
        # Retired drivers get 0 (you can change this if you want F1-style classification rules)
        if result.get("retired", False):
            result["points"] = 0.0
            continue

        # Normalize position to int
        position_raw = result.get("position")
        try:
            position = int(position_raw)
        except (TypeError, ValueError):
            result["points"] = 0.0
            continue

        # Store normalized position back (optional but convenient)
        result["position"] = position

        # Base points from finishing place
        result["points"] = float(points_rules.get(position, 0.0))

    # Second pass: compute fastest lap (single winner, top-N, not retired)
    best_idx: Optional[int] = None
    best_lap_secs: Optional[float] = None

    if fastest_lap_bonus != 0.0:
        for idx, result in enumerate(results):
            if result.get("retired", False):
                continue

            position = result.get("position")
            if not isinstance(position, int) or position > fastest_lap_top_n_only:
                continue

            # Support either 'fastest_lap_time' or 'best_lap_time'
            lap_str = result.get("fastest_lap_time") or result.get("best_lap_time")
            lap_secs = _parse_lap_time(lap_str)
            if lap_secs is None:
                continue

            if best_lap_secs is None or lap_secs < best_lap_secs:
                best_lap_secs = lap_secs
                best_idx = idx

        # Award bonus to the single fastest-lap driver, if found
        if best_idx is not None:
            results[best_idx]["points"] = results[best_idx].get("points", 0.0) + float(
                fastest_lap_bonus
            )

    return results
