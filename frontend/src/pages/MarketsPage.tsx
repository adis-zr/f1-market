import { useState } from 'react';
import { PageHeader } from '@/components/layout/PageHeader';
import { SportSelector } from '@/components/layout/SportSelector';
import { MarketTable } from '@/components/market/MarketTable';
import { useMarkets } from '@/hooks/useMarkets';
import { Select } from '@/components/ui/select';

export function MarketsPage() {
  const [sportId, setSportId] = useState<number | undefined>();
  const [status, setStatus] = useState<string>('');

  const filters = {
    sport_id: sportId,
    status: status || undefined,
  };

  const { data: markets = [], isLoading } = useMarkets(filters);

  return (
    <div>
      <PageHeader
        title="Markets"
        description="Browse and explore all available markets"
        actions={
          <div className="flex gap-2">
            <SportSelector value={sportId} onChange={setSportId} />
            <Select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All Status</option>
              <option value="open">Open</option>
              <option value="closed">Closed</option>
              <option value="settled">Settled</option>
            </Select>
          </div>
        }
      />
      {isLoading ? (
        <div className="text-center py-8 text-muted-foreground">
          Loading markets...
        </div>
      ) : (
        <MarketTable markets={markets} />
      )}
    </div>
  );
}

