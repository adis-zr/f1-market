"""CLI tool to simulate event settlement."""
import sys
from decimal import Decimal
from datetime import datetime
from app import app
from db import db, Event, EventResult, Participant, ResultStatus
from services.settlement_service import SettlementService


def simulate_event(event_id: int):
    """
    Simulate an event by creating mock EventResult records and settling.
    
    Args:
        event_id: Event ID to simulate
    """
    with app.app_context():
        # Get event
        event = Event.query.get(event_id)
        if not event:
            print(f"Error: Event {event_id} not found")
            return
        
        print(f"Simulating event: {event.name}")
        print(f"Event ID: {event_id}")
        
        # Get all participants for this event's sport
        # For simplicity, we'll get participants from markets
        from db import Market, Asset
        
        markets = Market.query.filter_by(event_id=event_id).all()
        if not markets:
            print("Error: No markets found for this event")
            return
        
        participants_processed = set()
        
        for market in markets:
            asset = market.asset
            if not asset or not asset.participant_id:
                continue
            
            participant_id = asset.participant_id
            if participant_id in participants_processed:
                continue
            
            participant = Participant.query.get(participant_id)
            if not participant:
                continue
            
            # Check if result already exists
            existing_result = EventResult.query.filter_by(
                event_id=event_id,
                participant_id=participant_id
            ).first()
            
            if existing_result:
                print(f"  Result already exists for {participant.name}, skipping...")
                continue
            
            # Create mock result
            # For demo, assign random scores (1-25 points)
            import random
            score = Decimal(str(random.randint(1, 25)))
            rank = random.randint(1, 20)
            
            event_result = EventResult(
                event_id=event_id,
                participant_id=participant_id,
                primary_score=score,
                rank=rank,
                status=ResultStatus.FINISHED,
                metrics_json={
                    'simulated': True,
                    'simulated_at': datetime.utcnow().isoformat()
                }
            )
            db.session.add(event_result)
            participants_processed.add(participant_id)
            
            print(f"  Created result for {participant.name}: {score} points (rank {rank})")
        
        db.session.commit()
        
        # Preview settlement
        print("\nPreviewing settlement...")
        preview = SettlementService.preview_settlement(event_id)
        print(f"  Markets to settle: {preview['markets_previewed']}")
        for p in preview['previews']:
            print(f"    Market {p['market_id']}: {p['payout_per_share']:.4f} per share")
        
        # Ask for confirmation
        print("\nProceed with settlement? (y/n): ", end='')
        response = input().strip().lower()
        
        if response == 'y':
            print("\nSettling event...")
            result = SettlementService.settle_event(event_id, source="simulation")
            
            if result['success']:
                print(f"✓ Successfully settled event!")
                print(f"  Markets settled: {result['markets_settled']}")
                print(f"  Positions settled: {result['positions_settled']}")
                print(f"  Total payout: {result['total_payout']:.2f}")
            else:
                print(f"✗ Error: {result.get('error', 'Unknown error')}")
        else:
            print("Settlement cancelled.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/simulate_event.py <event_id>")
        sys.exit(1)
    
    try:
        event_id = int(sys.argv[1])
        simulate_event(event_id)
    except ValueError:
        print("Error: event_id must be an integer")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

