"""F1 2024 driver and team definitions."""
from typing import Dict, Optional

# All 20 drivers from the 2024 F1 season
DRIVERS_2024 = [
    {"code": "VER", "name": "Max Verstappen", "number": 1, "team": "Red Bull Racing"},
    {"code": "PER", "name": "Sergio Perez", "number": 11, "team": "Red Bull Racing"},
    {"code": "HAM", "name": "Lewis Hamilton", "number": 44, "team": "Mercedes"},
    {"code": "RUS", "name": "George Russell", "number": 63, "team": "Mercedes"},
    {"code": "LEC", "name": "Charles Leclerc", "number": 16, "team": "Ferrari"},
    {"code": "SAI", "name": "Carlos Sainz", "number": 55, "team": "Ferrari"},
    {"code": "NOR", "name": "Lando Norris", "number": 4, "team": "McLaren"},
    {"code": "PIA", "name": "Oscar Piastri", "number": 81, "team": "McLaren"},
    {"code": "ALO", "name": "Fernando Alonso", "number": 14, "team": "Aston Martin"},
    {"code": "STR", "name": "Lance Stroll", "number": 18, "team": "Aston Martin"},
    {"code": "GAS", "name": "Pierre Gasly", "number": 10, "team": "Alpine"},
    {"code": "OCO", "name": "Esteban Ocon", "number": 31, "team": "Alpine"},
    {"code": "TSU", "name": "Yuki Tsunoda", "number": 22, "team": "RB"},
    {"code": "RIC", "name": "Daniel Ricciardo", "number": 3, "team": "RB"},
    {"code": "BOT", "name": "Valtteri Bottas", "number": 77, "team": "Sauber"},
    {"code": "ZHO", "name": "Zhou Guanyu", "number": 24, "team": "Sauber"},
    {"code": "MAG", "name": "Kevin Magnussen", "number": 20, "team": "Haas"},
    {"code": "HUL", "name": "Nico Hulkenberg", "number": 27, "team": "Haas"},
    {"code": "ALB", "name": "Alexander Albon", "number": 23, "team": "Williams"},
    {"code": "SAR", "name": "Logan Sargeant", "number": 2, "team": "Williams"},
]

# Teams in 2024
TEAMS_2024 = [
    {"code": "RBR", "name": "Red Bull Racing"},
    {"code": "MER", "name": "Mercedes"},
    {"code": "FER", "name": "Ferrari"},
    {"code": "MCL", "name": "McLaren"},
    {"code": "AMR", "name": "Aston Martin"},
    {"code": "ALP", "name": "Alpine"},
    {"code": "RB", "name": "RB"},
    {"code": "SAU", "name": "Sauber"},
    {"code": "HAS", "name": "Haas"},
    {"code": "WIL", "name": "Williams"},
]

# Quick lookup by driver code
_DRIVER_BY_CODE: Dict[str, dict] = {d["code"]: d for d in DRIVERS_2024}


def get_driver_by_code(code: str) -> Optional[dict]:
    """Get driver info by short code.

    Args:
        code: Driver short code (e.g., "VER", "HAM")

    Returns:
        Driver dict or None if not found
    """
    return _DRIVER_BY_CODE.get(code)


def get_all_driver_codes() -> list:
    """Get list of all driver codes."""
    return [d["code"] for d in DRIVERS_2024]
