import { useParams, Link } from 'react-router-dom';
import { PageHeader } from '@/components/layout/PageHeader';
import { MarketTable } from '@/components/market/MarketTable';
import { useEvent, useEventMarkets } from '@/hooks/useEvents';
import { useEventResults } from '@/hooks/useEventResults';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatDateTime } from '@/lib/formatters';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

export function EventDetailPage() {
  const { eventId } = useParams<{ eventId: string }>();
  const id = eventId ? parseInt(eventId, 10) : 0;
  const { data: event, isLoading: eventLoading } = useEvent(id);
  const { data: markets = [], isLoading: marketsLoading } = useEventMarkets(id);
  const { data: results = [], isLoading: resultsLoading } = useEventResults(id);

  if (eventLoading) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Loading event...
      </div>
    );
  }

  if (!event) {
    return (
      <div className="text-center py-8">
        <p className="text-muted-foreground">Event not found</p>
        <Link to="/events" className="text-primary hover:underline mt-4 inline-block">
          Back to Events
        </Link>
      </div>
    );
  }

  const statusVariant =
    event.status === 'upcoming'
      ? 'default'
      : event.status === 'live'
      ? 'success'
      : 'warning';

  return (
    <div>
      <PageHeader
        title={event.name}
        description={event.venue || undefined}
        breadcrumbs={[
          { label: 'Events', href: '/events' },
          { label: event.name },
        ]}
      />
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Event Information</CardTitle>
              <Badge variant={statusVariant}>{event.status}</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            {event.start_at && (
              <div>
                <span className="text-sm text-muted-foreground">Start Time: </span>
                <span>{formatDateTime(event.start_at)}</span>
              </div>
            )}
            {event.end_at && (
              <div>
                <span className="text-sm text-muted-foreground">End Time: </span>
                <span>{formatDateTime(event.end_at)}</span>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Markets</CardTitle>
          </CardHeader>
          <CardContent>
            {marketsLoading ? (
              <div className="text-center py-8 text-muted-foreground">
                Loading markets...
              </div>
            ) : (
              <MarketTable markets={markets} />
            )}
          </CardContent>
        </Card>

        {event.status === 'finished' && (
          <Card>
            <CardHeader>
              <CardTitle>Results</CardTitle>
            </CardHeader>
            <CardContent>
              {resultsLoading ? (
                <div className="text-center py-8 text-muted-foreground">
                  Loading results...
                </div>
              ) : results.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No results available
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Rank</TableHead>
                      <TableHead>Participant</TableHead>
                      <TableHead>Score</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {results
                      .sort((a, b) => (a.rank || 999) - (b.rank || 999))
                      .map((result) => (
                        <TableRow key={result.id}>
                          <TableCell>{result.rank || '—'}</TableCell>
                          <TableCell>
                            {result.participant?.name || 'Unknown'}
                          </TableCell>
                          <TableCell>{result.primary_score.toFixed(2)}</TableCell>
                          <TableCell>
                            <Badge
                              variant={
                                result.status === 'finished'
                                  ? 'success'
                                  : result.status === 'dnf'
                                  ? 'warning'
                                  : 'destructive'
                              }
                            >
                              {result.status}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

