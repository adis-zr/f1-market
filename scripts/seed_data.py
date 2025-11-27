"""Seed script to create initial F1 data for the market engine."""
from datetime import datetime
from decimal import Decimal
from db import (
    db, Sport, League, Season, ScoringRule, SeasonStatus, FormulaType
)
from scripts.f1_adapter import F1Adapter


def seed_f1_data(year: int = None):
    """
    Seed F1 sport, league, season, and scoring rule.
    
    Args:
        year: Season year (defaults to current year)
    """
    if year is None:
        year = datetime.now().year
    
    print(f"Seeding F1 data for year {year}...")
    
    # Initialize adapter
    adapter = F1Adapter()
    
    # Sync F1 data
    result = adapter.sync_season(year)
    
    if result.get('success'):
        print(f"✓ Successfully seeded F1 data:")
        print(f"  - Drivers synced: {result.get('drivers_synced', 0)}")
        print(f"  - Events synced: {result.get('events_synced', 0)}")
        print(f"  - Results synced: {result.get('results_synced', 0)}")
    else:
        print(f"✗ Error seeding F1 data: {result.get('error')}")
    
    # Ensure scoring rule exists
    sport = adapter.get_or_create_sport()
    scoring_rule = adapter.get_or_create_scoring_rule(sport)
    print(f"✓ Scoring rule: {scoring_rule.code} (max_score={scoring_rule.max_score})")
    
    print("\nSeed complete!")


if __name__ == "__main__":
    import sys
    year = int(sys.argv[1]) if len(sys.argv) > 1 else None
    seed_f1_data(year)

