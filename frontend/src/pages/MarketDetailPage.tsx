import { useParams, Link } from 'react-router-dom';
import { PageHeader } from '@/components/layout/PageHeader';
import { PriceChart } from '@/components/market/PriceChart';
import { OrderPanel } from '@/components/market/OrderPanel';
import { useMarket } from '@/hooks/useMarkets';
import { usePosition } from '@/hooks/usePositions';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatPrice, formatShares, formatPnL } from '@/lib/formatters';

export function MarketDetailPage() {
  const { marketId } = useParams<{ marketId: string }>();
  const id = marketId ? parseInt(marketId, 10) : 0;
  const { data: market, isLoading: marketLoading } = useMarket(id);
  const { data: position, isLoading: positionLoading } = usePosition(id);

  if (marketLoading) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Loading market...
      </div>
    );
  }

  if (!market) {
    return (
      <div className="text-center py-8">
        <p className="text-muted-foreground">Market not found</p>
        <Link to="/markets" className="text-primary hover:underline mt-4 inline-block">
          Back to Markets
        </Link>
      </div>
    );
  }

  const assetName = market.asset?.display_name || 'Unknown Asset';
  const eventName = market.event?.name || 'Unknown Event';
  const statusVariant =
    market.status === 'open'
      ? 'success'
      : market.status === 'closed'
      ? 'warning'
      : 'default';

  const unrealizedPnL = position ? formatPnL(position.unrealized_pnl) : null;
  const totalPnL = position ? formatPnL(position.total_pnl) : null;

  return (
    <div>
      <PageHeader
        title={assetName}
        description={eventName}
        breadcrumbs={[
          { label: 'Markets', href: '/markets' },
          { label: assetName },
        ]}
      />
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Market Information</CardTitle>
                <Badge variant={statusVariant}>{market.status}</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-sm text-muted-foreground">Current Price</div>
                  <div className="text-2xl font-bold">
                    {formatPrice(market.current_price)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Supply</div>
                  <div className="text-xl font-semibold">
                    {market.current_supply.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Market Type</div>
                  <div className="text-lg">{market.market_type}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Event Status</div>
                  <div className="text-lg">
                    {market.event?.status || 'Unknown'}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
          <PriceChart marketId={id} />
          {position && !positionLoading && (
            <Card>
              <CardHeader>
                <CardTitle>Your Position</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-muted-foreground">Shares</div>
                    <div className="text-xl font-semibold">
                      {formatShares(position.shares)}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Avg Entry Price</div>
                    <div className="text-xl font-semibold">
                      {formatPrice(position.avg_entry_price)}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Unrealized P&L</div>
                    <div
                      className={`text-xl font-semibold ${
                        unrealizedPnL?.isPositive ? 'text-green-600' : 'text-red-600'
                      }`}
                    >
                      {unrealizedPnL?.value || '—'}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Total P&L</div>
                    <div
                      className={`text-xl font-semibold ${
                        totalPnL?.isPositive ? 'text-green-600' : 'text-red-600'
                      }`}
                    >
                      {totalPnL?.value || '—'}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
        <div>
          <OrderPanel marketId={id} />
        </div>
      </div>
    </div>
  );
}

