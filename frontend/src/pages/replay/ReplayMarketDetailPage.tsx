import { useParams, Link } from 'react-router-dom';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useReplayMarket, useReplayPriceHistory, useReplay } from '@/hooks';
import { ReplayOrderPanel } from '@/components/replay/ReplayOrderPanel';
import { ReplayPriceChart } from '@/components/replay/ReplayPriceChart';
import { formatPrice, formatPnL } from '@/lib/formatters';

export function ReplayMarketDetailPage() {
  const { marketId } = useParams<{ marketId: string }>();
  const id = marketId ? parseInt(marketId, 10) : 0;

  const { data, isLoading: marketLoading } = useReplayMarket(id);
  const { data: priceHistory = [] } = useReplayPriceHistory(id);
  const { currentRace, wallet } = useReplay();

  const market = data?.market;
  const position = data?.position;

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
        <Link to="/replay/dashboard" className="text-primary hover:underline mt-4 inline-block">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  const isCurrentRace = market.race_number === currentRace;
  const statusVariant =
    market.status === 'open' && isCurrentRace
      ? 'default'
      : market.status === 'settled'
      ? 'secondary'
      : 'outline';

  const unrealizedPnL = position ? formatPnL(position.unrealized_pnl) : null;
  const totalPnL = position ? formatPnL(position.realized_pnl + position.unrealized_pnl) : null;

  return (
    <div>
      <PageHeader
        title={`${market.driver_code} - ${market.driver_name}`}
        description={market.team_name || 'F1 Driver'}
        breadcrumbs={[
          { label: 'Replay', href: '/replay' },
          { label: 'Dashboard', href: '/replay/dashboard' },
          { label: market.driver_code },
        ]}
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          {/* Market Information */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Market Information</CardTitle>
                <div className="flex items-center gap-2">
                  <Badge variant="outline">Race {market.race_number}</Badge>
                  <Badge variant={statusVariant}>{market.status}</Badge>
                </div>
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
                {market.settlement_price !== null && (
                  <>
                    <div>
                      <div className="text-sm text-muted-foreground">Settlement (Points)</div>
                      <div className="text-xl font-semibold">
                        {market.settlement_price}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Payout per Share</div>
                      <div className="text-xl font-semibold">
                        {formatPrice(market.payout_per_share || 0)}
                      </div>
                    </div>
                  </>
                )}
              </div>

              {!isCurrentRace && market.status !== 'settled' && (
                <div className="text-sm text-yellow-600 bg-yellow-50 dark:bg-yellow-950 p-3 rounded">
                  This market is for Race {market.race_number}. You are currently on Race {currentRace}.
                  You can only trade markets for the current race.
                </div>
              )}
            </CardContent>
          </Card>

          {/* Price Chart */}
          <ReplayPriceChart
            history={priceHistory}
            driverCode={market.driver_code}
          />

          {/* Position Card */}
          {position && position.shares > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Your Position</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-muted-foreground">Shares</div>
                    <div className="text-xl font-semibold">
                      {position.shares.toFixed(4)}
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
                      {unrealizedPnL?.value || '$0.00'}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Total P&L</div>
                    <div
                      className={`text-xl font-semibold ${
                        totalPnL?.isPositive ? 'text-green-600' : 'text-red-600'
                      }`}
                    >
                      {totalPnL?.value || '$0.00'}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Order Panel */}
        <div>
          <ReplayOrderPanel
            marketId={id}
            market={market}
            position={position}
            balance={wallet?.balance || 0}
            disabled={!isCurrentRace || market.status !== 'open'}
          />
        </div>
      </div>
    </div>
  );
}
