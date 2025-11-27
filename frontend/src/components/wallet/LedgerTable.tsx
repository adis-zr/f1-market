import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { formatPrice, formatDateTime } from '@/lib/formatters';
import type { LedgerEntry } from '@/api/types';

interface LedgerTableProps {
  entries: LedgerEntry[];
}

const transactionTypeColors: Record<LedgerEntry['transaction_type'], string> = {
  deposit: 'success',
  withdrawal: 'destructive',
  buy: 'default',
  sell: 'default',
  settlement: 'success',
  fee: 'warning',
};

export function LedgerTable({ entries }: LedgerTableProps) {
  if (entries.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No transactions found
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Date</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Amount</TableHead>
          <TableHead>Description</TableHead>
          <TableHead>Reference</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {entries.map((entry) => {
          const isPositive = entry.amount >= 0;
          const variant =
            transactionTypeColors[entry.transaction_type] || 'default';

          return (
            <TableRow key={entry.id}>
              <TableCell>{formatDateTime(entry.created_at)}</TableCell>
              <TableCell>
                <Badge variant={variant as any}>{entry.transaction_type}</Badge>
              </TableCell>
              <TableCell>
                <span
                  className={
                    isPositive ? 'text-green-600' : 'text-red-600'
                  }
                >
                  {isPositive ? '+' : ''}
                  {formatPrice(entry.amount)}
                </span>
              </TableCell>
              <TableCell>{entry.description || '—'}</TableCell>
              <TableCell>
                {entry.reference_type && entry.reference_id
                  ? `${entry.reference_type} #${entry.reference_id}`
                  : '—'}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

