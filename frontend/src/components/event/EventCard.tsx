import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatDateTime } from '@/lib/formatters';
import type { Event } from '@/api/types';

interface EventCardProps {
  event: Event;
}

export function EventCard({ event }: EventCardProps) {
  const statusVariant =
    event.status === 'upcoming'
      ? 'default'
      : event.status === 'live'
      ? 'success'
      : 'warning';

  return (
    <Link to={`/events/${event.id}`}>
      <Card className="transition-shadow hover:shadow-lg">
        <CardHeader>
          <div className="flex items-start justify-between">
            <CardTitle className="text-lg">{event.name}</CardTitle>
            <Badge variant={statusVariant}>{event.status}</Badge>
          </div>
          {event.venue && (
            <p className="text-sm text-muted-foreground">{event.venue}</p>
          )}
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">
            {event.start_at ? formatDateTime(event.start_at) : 'TBD'}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

