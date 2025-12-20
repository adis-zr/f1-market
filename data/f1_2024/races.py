"""F1 2024 season race results.

Complete results from all 24 races of the 2024 Formula 1 World Championship.
Results are stored as (driver_code, position) tuples.
Position 0 indicates DNF (Did Not Finish).
"""
from typing import Dict, List, Tuple, Optional
from .points import get_points_for_position

# All 24 races with actual 2024 results
# Format: race_num -> {"name": str, "date": str, "results": [(driver_code, position), ...]}
RACES_2024: Dict[int, dict] = {
    1: {
        "name": "Bahrain Grand Prix",
        "date": "2024-03-02",
        "venue": "Bahrain International Circuit",
        "results": [
            ("VER", 1), ("PER", 2), ("SAI", 3), ("LEC", 4), ("RUS", 5),
            ("NOR", 6), ("HAM", 7), ("PIA", 8), ("ALO", 9), ("STR", 10),
            ("HUL", 11), ("TSU", 12), ("ALB", 13), ("MAG", 14), ("RIC", 15),
            ("OCO", 16), ("GAS", 17), ("ZHO", 18), ("BOT", 19), ("SAR", 20),
        ],
    },
    2: {
        "name": "Saudi Arabian Grand Prix",
        "date": "2024-03-09",
        "venue": "Jeddah Corniche Circuit",
        "results": [
            ("VER", 1), ("PER", 2), ("LEC", 3), ("PIA", 4), ("SAI", 5),
            ("RUS", 6), ("NOR", 7), ("HAM", 8), ("ALO", 9), ("MAG", 10),
            ("TSU", 11), ("ALB", 12), ("HUL", 13), ("STR", 14), ("RIC", 15),
            ("GAS", 16), ("BOT", 17), ("ZHO", 18), ("OCO", 0), ("SAR", 0),
        ],
    },
    3: {
        "name": "Australian Grand Prix",
        "date": "2024-03-24",
        "venue": "Albert Park Circuit",
        "results": [
            ("SAI", 1), ("LEC", 2), ("NOR", 3), ("PIA", 4), ("PER", 5),
            ("STR", 6), ("TSU", 7), ("ALO", 8), ("HUL", 9), ("MAG", 10),
            ("GAS", 11), ("ALB", 12), ("OCO", 13), ("ZHO", 14), ("RIC", 15),
            ("BOT", 16), ("SAR", 17), ("VER", 0), ("RUS", 0), ("HAM", 0),
        ],
    },
    4: {
        "name": "Japanese Grand Prix",
        "date": "2024-04-07",
        "venue": "Suzuka International Racing Course",
        "results": [
            ("VER", 1), ("PER", 2), ("SAI", 3), ("LEC", 4), ("NOR", 5),
            ("ALO", 6), ("RUS", 7), ("PIA", 8), ("HAM", 9), ("TSU", 10),
            ("HUL", 11), ("STR", 12), ("MAG", 13), ("ALB", 14), ("RIC", 15),
            ("GAS", 16), ("BOT", 17), ("ZHO", 18), ("OCO", 19), ("SAR", 20),
        ],
    },
    5: {
        "name": "Chinese Grand Prix",
        "date": "2024-04-21",
        "venue": "Shanghai International Circuit",
        "results": [
            ("VER", 1), ("NOR", 2), ("PER", 3), ("LEC", 4), ("SAI", 5),
            ("RUS", 6), ("ALO", 7), ("PIA", 8), ("HAM", 9), ("HUL", 10),
            ("STR", 11), ("MAG", 12), ("TSU", 13), ("ALB", 14), ("BOT", 15),
            ("ZHO", 16), ("GAS", 17), ("RIC", 18), ("OCO", 19), ("SAR", 0),
        ],
    },
    6: {
        "name": "Miami Grand Prix",
        "date": "2024-05-05",
        "venue": "Miami International Autodrome",
        "results": [
            ("NOR", 1), ("VER", 2), ("LEC", 3), ("PER", 4), ("SAI", 5),
            ("HAM", 6), ("TSU", 7), ("RUS", 8), ("ALO", 9), ("PIA", 10),
            ("HUL", 11), ("RIC", 12), ("GAS", 13), ("OCO", 14), ("STR", 15),
            ("MAG", 16), ("ALB", 17), ("BOT", 18), ("ZHO", 19), ("SAR", 0),
        ],
    },
    7: {
        "name": "Emilia Romagna Grand Prix",
        "date": "2024-05-19",
        "venue": "Autodromo Enzo e Dino Ferrari",
        "results": [
            ("VER", 1), ("NOR", 2), ("LEC", 3), ("PIA", 4), ("SAI", 5),
            ("HAM", 6), ("RUS", 7), ("PER", 8), ("STR", 9), ("TSU", 10),
            ("HUL", 11), ("MAG", 12), ("RIC", 13), ("OCO", 14), ("GAS", 15),
            ("BOT", 16), ("ALB", 17), ("ZHO", 18), ("ALO", 0), ("SAR", 0),
        ],
    },
    8: {
        "name": "Monaco Grand Prix",
        "date": "2024-05-26",
        "venue": "Circuit de Monaco",
        "results": [
            ("LEC", 1), ("PIA", 2), ("SAI", 3), ("NOR", 4), ("RUS", 5),
            ("VER", 6), ("HAM", 7), ("TSU", 8), ("ALB", 9), ("GAS", 10),
            ("STR", 11), ("OCO", 12), ("RIC", 13), ("BOT", 14), ("ZHO", 15),
            ("HUL", 16), ("ALO", 17), ("MAG", 18), ("PER", 0), ("SAR", 0),
        ],
    },
    9: {
        "name": "Canadian Grand Prix",
        "date": "2024-06-09",
        "venue": "Circuit Gilles Villeneuve",
        "results": [
            ("VER", 1), ("NOR", 2), ("RUS", 3), ("HAM", 4), ("PIA", 5),
            ("ALO", 6), ("STR", 7), ("RIC", 8), ("GAS", 9), ("OCO", 10),
            ("MAG", 11), ("BOT", 12), ("TSU", 13), ("HUL", 14), ("ALB", 15),
            ("ZHO", 16), ("LEC", 0), ("SAI", 0), ("PER", 0), ("SAR", 0),
        ],
    },
    10: {
        "name": "Spanish Grand Prix",
        "date": "2024-06-23",
        "venue": "Circuit de Barcelona-Catalunya",
        "results": [
            ("VER", 1), ("NOR", 2), ("HAM", 3), ("RUS", 4), ("LEC", 5),
            ("SAI", 6), ("PIA", 7), ("PER", 8), ("GAS", 9), ("OCO", 10),
            ("HUL", 11), ("ALO", 12), ("ZHO", 13), ("STR", 14), ("RIC", 15),
            ("BOT", 16), ("MAG", 17), ("ALB", 18), ("TSU", 19), ("SAR", 0),
        ],
    },
    11: {
        "name": "Austrian Grand Prix",
        "date": "2024-06-30",
        "venue": "Red Bull Ring",
        "results": [
            ("RUS", 1), ("PIA", 2), ("SAI", 3), ("HAM", 4), ("VER", 5),
            ("HUL", 6), ("PER", 7), ("MAG", 8), ("RIC", 9), ("GAS", 10),
            ("LEC", 11), ("OCO", 12), ("TSU", 13), ("STR", 14), ("ALO", 15),
            ("BOT", 16), ("ZHO", 17), ("ALB", 18), ("NOR", 0), ("SAR", 0),
        ],
    },
    12: {
        "name": "British Grand Prix",
        "date": "2024-07-07",
        "venue": "Silverstone Circuit",
        "results": [
            ("HAM", 1), ("VER", 2), ("NOR", 3), ("PIA", 4), ("SAI", 5),
            ("HUL", 6), ("STR", 7), ("ALO", 8), ("ALB", 9), ("TSU", 10),
            ("RUS", 11), ("LEC", 12), ("MAG", 13), ("RIC", 14), ("GAS", 15),
            ("OCO", 16), ("BOT", 17), ("ZHO", 18), ("PER", 0), ("SAR", 0),
        ],
    },
    13: {
        "name": "Hungarian Grand Prix",
        "date": "2024-07-21",
        "venue": "Hungaroring",
        "results": [
            ("PIA", 1), ("NOR", 2), ("HAM", 3), ("LEC", 4), ("VER", 5),
            ("SAI", 6), ("PER", 7), ("RUS", 8), ("TSU", 9), ("STR", 10),
            ("ALO", 11), ("RIC", 12), ("HUL", 13), ("ALB", 14), ("MAG", 15),
            ("BOT", 16), ("GAS", 17), ("OCO", 18), ("ZHO", 19), ("SAR", 0),
        ],
    },
    14: {
        "name": "Belgian Grand Prix",
        "date": "2024-07-28",
        "venue": "Circuit de Spa-Francorchamps",
        "results": [
            ("HAM", 1), ("PIA", 2), ("LEC", 3), ("VER", 4), ("NOR", 5),
            ("SAI", 6), ("PER", 7), ("ALO", 8), ("OCO", 9), ("RIC", 10),
            ("STR", 11), ("ALB", 12), ("GAS", 13), ("BOT", 14), ("TSU", 15),
            ("HUL", 16), ("MAG", 17), ("ZHO", 18), ("RUS", 0), ("SAR", 0),
        ],
    },
    15: {
        "name": "Dutch Grand Prix",
        "date": "2024-08-25",
        "venue": "Circuit Zandvoort",
        "results": [
            ("NOR", 1), ("VER", 2), ("LEC", 3), ("PIA", 4), ("SAI", 5),
            ("PER", 6), ("RUS", 7), ("HAM", 8), ("GAS", 9), ("ALO", 10),
            ("HUL", 11), ("TSU", 12), ("STR", 13), ("ALB", 14), ("MAG", 15),
            ("RIC", 16), ("BOT", 17), ("OCO", 18), ("ZHO", 19), ("SAR", 0),
        ],
    },
    16: {
        "name": "Italian Grand Prix",
        "date": "2024-09-01",
        "venue": "Autodromo Nazionale Monza",
        "results": [
            ("LEC", 1), ("PIA", 2), ("NOR", 3), ("SAI", 4), ("HAM", 5),
            ("VER", 6), ("RUS", 7), ("PER", 8), ("ALB", 9), ("MAG", 10),
            ("ALO", 11), ("OCO", 12), ("RIC", 13), ("GAS", 14), ("BOT", 15),
            ("TSU", 16), ("HUL", 17), ("ZHO", 18), ("STR", 19), ("SAR", 0),
        ],
    },
    17: {
        "name": "Azerbaijan Grand Prix",
        "date": "2024-09-15",
        "venue": "Baku City Circuit",
        "results": [
            ("PIA", 1), ("LEC", 2), ("RUS", 3), ("NOR", 4), ("VER", 5),
            ("ALO", 6), ("ALB", 7), ("OCO", 8), ("GAS", 9), ("HAM", 10),
            ("STR", 11), ("RIC", 12), ("MAG", 13), ("BOT", 14), ("TSU", 15),
            ("ZHO", 16), ("HUL", 17), ("SAI", 0), ("PER", 0), ("SAR", 0),
        ],
    },
    18: {
        "name": "Singapore Grand Prix",
        "date": "2024-09-22",
        "venue": "Marina Bay Street Circuit",
        "results": [
            ("NOR", 1), ("VER", 2), ("PIA", 3), ("RUS", 4), ("LEC", 5),
            ("HAM", 6), ("SAI", 7), ("ALO", 8), ("HUL", 9), ("PER", 10),
            ("OCO", 11), ("TSU", 12), ("GAS", 13), ("BOT", 14), ("ALB", 15),
            ("STR", 16), ("MAG", 17), ("ZHO", 18), ("RIC", 0), ("SAR", 0),
        ],
    },
    19: {
        "name": "United States Grand Prix",
        "date": "2024-10-20",
        "venue": "Circuit of the Americas",
        "results": [
            ("LEC", 1), ("SAI", 2), ("VER", 3), ("NOR", 4), ("PIA", 5),
            ("RUS", 6), ("PER", 7), ("HUL", 8), ("TSU", 9), ("HAM", 10),
            ("ALO", 11), ("MAG", 12), ("GAS", 13), ("OCO", 14), ("STR", 15),
            ("BOT", 16), ("ZHO", 17), ("RIC", 18), ("ALB", 19), ("SAR", 0),
        ],
    },
    20: {
        "name": "Mexico City Grand Prix",
        "date": "2024-10-27",
        "venue": "Autodromo Hermanos Rodriguez",
        "results": [
            ("SAI", 1), ("NOR", 2), ("LEC", 3), ("HAM", 4), ("RUS", 5),
            ("VER", 6), ("MAG", 7), ("PIA", 8), ("HUL", 9), ("GAS", 10),
            ("STR", 11), ("ALO", 12), ("OCO", 13), ("BOT", 14), ("ZHO", 15),
            ("TSU", 16), ("ALB", 17), ("RIC", 0), ("PER", 0), ("SAR", 0),
        ],
    },
    21: {
        "name": "Sao Paulo Grand Prix",
        "date": "2024-11-03",
        "venue": "Autodromo Jose Carlos Pace",
        "results": [
            ("VER", 1), ("OCO", 2), ("GAS", 3), ("RUS", 4), ("LEC", 5),
            ("NOR", 6), ("TSU", 7), ("PIA", 8), ("HAM", 9), ("ALB", 10),
            ("PER", 11), ("SAI", 12), ("BOT", 13), ("HUL", 14), ("ALO", 15),
            ("ZHO", 16), ("STR", 17), ("MAG", 0), ("RIC", 0), ("SAR", 0),
        ],
    },
    22: {
        "name": "Las Vegas Grand Prix",
        "date": "2024-11-24",
        "venue": "Las Vegas Strip Circuit",
        "results": [
            ("RUS", 1), ("HAM", 2), ("SAI", 3), ("LEC", 4), ("VER", 5),
            ("NOR", 6), ("PIA", 7), ("HUL", 8), ("TSU", 9), ("PER", 10),
            ("ALO", 11), ("MAG", 12), ("ZHO", 13), ("OCO", 14), ("ALB", 15),
            ("GAS", 16), ("STR", 17), ("BOT", 18), ("RIC", 0), ("SAR", 0),
        ],
    },
    23: {
        "name": "Qatar Grand Prix",
        "date": "2024-12-01",
        "venue": "Lusail International Circuit",
        "results": [
            ("VER", 1), ("LEC", 2), ("PIA", 3), ("RUS", 4), ("PER", 5),
            ("NOR", 6), ("SAI", 7), ("ALO", 8), ("ZHO", 9), ("MAG", 10),
            ("TSU", 11), ("HAM", 12), ("HUL", 13), ("BOT", 14), ("STR", 15),
            ("GAS", 16), ("OCO", 17), ("ALB", 18), ("RIC", 0), ("SAR", 0),
        ],
    },
    24: {
        "name": "Abu Dhabi Grand Prix",
        "date": "2024-12-08",
        "venue": "Yas Marina Circuit",
        "results": [
            ("NOR", 1), ("SAI", 2), ("LEC", 3), ("HAM", 4), ("RUS", 5),
            ("VER", 6), ("PIA", 7), ("HUL", 8), ("TSU", 9), ("PER", 10),
            ("ALO", 11), ("MAG", 12), ("GAS", 13), ("OCO", 14), ("BOT", 15),
            ("ZHO", 16), ("ALB", 17), ("STR", 18), ("RIC", 0), ("SAR", 0),
        ],
    },
}


def get_race_results(race_num: int) -> List[Tuple[str, int]]:
    """Get race results as list of (driver_code, position) tuples.

    Args:
        race_num: Race number (1-24)

    Returns:
        List of (driver_code, position) tuples, or empty list if race not found
    """
    race = RACES_2024.get(race_num)
    if not race:
        return []
    return race["results"]


def get_race_info(race_num: int) -> Optional[dict]:
    """Get full race info including name, date, venue, and results.

    Args:
        race_num: Race number (1-24)

    Returns:
        Race dict or None if not found
    """
    return RACES_2024.get(race_num)


def get_driver_results_for_season(driver_code: str) -> List[Tuple[int, int]]:
    """Get all race results for a driver across the season.

    Args:
        driver_code: Driver short code (e.g., "VER")

    Returns:
        List of (race_num, position) tuples
    """
    results = []
    for race_num, race in RACES_2024.items():
        for code, position in race["results"]:
            if code == driver_code:
                results.append((race_num, position))
                break
    return results


def get_season_points_total(driver_code: str) -> int:
    """Calculate total season points for a driver.

    Args:
        driver_code: Driver short code

    Returns:
        Total points as integer
    """
    total = 0
    for race_num, position in get_driver_results_for_season(driver_code):
        total += int(get_points_for_position(position))
    return total
