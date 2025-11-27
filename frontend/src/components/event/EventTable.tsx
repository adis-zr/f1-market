import { Link } from 'react-router-dom';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { formatDateTime } from '@/lib/formatters';
import type { Event } from '@/api/types';

interface EventTableProps {
  events: Event[];
}

export function EventTable({ events }: EventTableProps) {
  if (events.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No events found
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Venue</TableHead>
          <TableHead>Start Time</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {events.map((event) => {
          const statusVariant =
            event.status === 'upcoming'
              ? 'default'
              : event.status === 'live'
              ? 'success'
              : 'warning';

          return (
            <TableRow key={event.id}>
              <TableCell className="font-medium">{event.name}</TableCell>
              <TableCell>{event.venue || '—'}</TableCell>
              <TableCell>
                {event.start_at ? formatDateTime(event.start_at) : 'TBD'}
              </TableCell>
              <TableCell>
                <Badge variant={statusVariant}>{event.status}</Badge>
              </TableCell>
              <TableCell>
                <Link to={`/events/${event.id}`}>
                  <Button variant="outline" size="sm">
                    View
                  </Button>
                </Link>
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

