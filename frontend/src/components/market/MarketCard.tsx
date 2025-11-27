import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatPrice } from '@/lib/formatters';
import type { Market } from '@/api/types';

interface MarketCardProps {
  market: Market;
}

export function MarketCard({ market }: MarketCardProps) {
  const assetName = market.asset?.display_name || 'Unknown Asset';
  const eventName = market.event?.name || 'Unknown Event';
  const statusVariant =
    market.status === 'open'
      ? 'success'
      : market.status === 'closed'
      ? 'warning'
      : 'default';

  // Calculate price change (would need previous price from history)
  // For now, just show current price
  const priceChange = { value: '0.00%', isPositive: true };

  return (
    <Link to={`/markets/${market.market_id}`}>
      <Card className="transition-shadow hover:shadow-lg">
        <CardHeader>
          <div className="flex items-start justify-between">
            <CardTitle className="text-lg">{assetName}</CardTitle>
            <Badge variant={statusVariant}>{market.status}</Badge>
          </div>
          <p className="text-sm text-muted-foreground">{eventName}</p>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex items-baseline justify-between">
              <span className="text-2xl font-bold">{formatPrice(market.current_price)}</span>
              <span
                className={`text-sm ${
                  priceChange.isPositive ? 'text-green-600' : 'text-red-600'
                }`}
              >
                {priceChange.value}
              </span>
            </div>
            <div className="text-xs text-muted-foreground">
              Supply: {market.current_supply.toFixed(2)}
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

