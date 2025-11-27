import { Link } from 'react-router-dom';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { formatPrice, formatShares, formatPnL } from '@/lib/formatters';
import type { Position } from '@/api/types';

interface PositionTableProps {
  positions: Position[];
}

export function PositionTable({ positions }: PositionTableProps) {
  if (positions.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No positions found
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Market</TableHead>
          <TableHead>Shares</TableHead>
          <TableHead>Avg Entry</TableHead>
          <TableHead>Current Price</TableHead>
          <TableHead>Current Value</TableHead>
          <TableHead>Unrealized PnL</TableHead>
          <TableHead>Realized PnL</TableHead>
          <TableHead>Total PnL</TableHead>
          <TableHead>Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {positions.map((position) => {
          const currentValue =
            position.current_price && position.shares
              ? position.current_price * position.shares
              : 0;
          const unrealizedPnL = formatPnL(position.unrealized_pnl);
          const realizedPnL = formatPnL(position.realized_pnl);
          const totalPnL = formatPnL(position.total_pnl);

          return (
            <TableRow key={position.position_id}>
              <TableCell className="font-medium">
                Market #{position.market_id}
              </TableCell>
              <TableCell>{formatShares(position.shares)}</TableCell>
              <TableCell>{formatPrice(position.avg_entry_price)}</TableCell>
              <TableCell>
                {position.current_price
                  ? formatPrice(position.current_price)
                  : '—'}
              </TableCell>
              <TableCell>{formatPrice(currentValue)}</TableCell>
              <TableCell>
                <span
                  className={
                    unrealizedPnL.isPositive ? 'text-green-600' : 'text-red-600'
                  }
                >
                  {unrealizedPnL.value}
                </span>
              </TableCell>
              <TableCell>
                <span
                  className={
                    realizedPnL.isPositive ? 'text-green-600' : 'text-red-600'
                  }
                >
                  {realizedPnL.value}
                </span>
              </TableCell>
              <TableCell>
                <span
                  className={
                    totalPnL.isPositive ? 'text-green-600' : 'text-red-600'
                  }
                >
                  {totalPnL.value}
                </span>
              </TableCell>
              <TableCell>
                <Link to={`/markets/${position.market_id}`}>
                  <span className="text-primary hover:underline text-sm">
                    View
                  </span>
                </Link>
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

