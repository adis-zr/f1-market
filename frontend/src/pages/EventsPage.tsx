import { useState } from 'react';
import { PageHeader } from '@/components/layout/PageHeader';
import { SportSelector } from '@/components/layout/SportSelector';
import { EventTable } from '@/components/event/EventTable';
import { useEvents } from '@/hooks';
import { Select } from '@/components/ui/select';

export function EventsPage() {
  const [sportId, setSportId] = useState<number | undefined>();
  const [status, setStatus] = useState<string>('');

  const filters = {
    sport_id: sportId,
    status: status || undefined,
  };

  const { data: events = [], isLoading } = useEvents(filters);

  return (
    <div>
      <PageHeader
        title="Events"
        description="Browse upcoming, live, and finished events"
        actions={
          <div className="flex gap-2">
            <SportSelector value={sportId} onChange={setSportId} />
            <Select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All Status</option>
              <option value="upcoming">Upcoming</option>
              <option value="live">Live</option>
              <option value="finished">Finished</option>
            </Select>
          </div>
        }
      />
      {isLoading ? (
        <div className="text-center py-8 text-muted-foreground">
          Loading events...
        </div>
      ) : (
        <EventTable events={events} />
      )}
    </div>
  );
}

