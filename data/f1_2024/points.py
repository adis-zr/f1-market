"""F1 2024 points system."""
from decimal import Decimal

# F1 2024 points system (positions 1-10 score points)
F1_POINTS = {
    1: Decimal('25'),
    2: Decimal('18'),
    3: Decimal('15'),
    4: Decimal('12'),
    5: Decimal('10'),
    6: Decimal('8'),
    7: Decimal('6'),
    8: Decimal('4'),
    9: Decimal('2'),
    10: Decimal('1'),
}


def get_points_for_position(position: int) -> Decimal:
    """Get F1 points for a finishing position.

    Args:
        position: Finishing position (1-20, or 0 for DNF/DSQ)

    Returns:
        Points as Decimal (0 for positions outside top 10)
    """
    return F1_POINTS.get(position, Decimal('0'))
