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
import { formatPrice, formatDateTime } from '@/lib/formatters';
import type { Market } from '@/api/types';

interface MarketTableProps {
  markets: Market[];
}

export function MarketTable({ markets }: MarketTableProps) {
  if (markets.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No markets found
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Asset</TableHead>
          <TableHead>Event</TableHead>
          <TableHead>Price</TableHead>
          <TableHead>Supply</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Event Time</TableHead>
          <TableHead>Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {markets.map((market) => {
          const assetName = market.asset?.display_name || 'Unknown';
          const eventName = market.event?.name || 'Unknown';
          const statusVariant =
            market.status === 'open'
              ? 'success'
              : market.status === 'closed'
              ? 'warning'
              : 'default';

          return (
            <TableRow key={market.market_id}>
              <TableCell className="font-medium">{assetName}</TableCell>
              <TableCell>{eventName}</TableCell>
              <TableCell>{formatPrice(market.current_price)}</TableCell>
              <TableCell>{market.current_supply.toFixed(2)}</TableCell>
              <TableCell>
                <Badge variant={statusVariant}>{market.status}</Badge>
              </TableCell>
              <TableCell>
                {market.event?.start_at
                  ? formatDateTime(market.event.start_at)
                  : '—'}
              </TableCell>
              <TableCell>
                <Link to={`/markets/${market.market_id}`}>
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

