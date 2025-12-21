import { Link } from 'react-router-dom';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Lock } from 'lucide-react';
import { useReplayPortfolio, useReplay, useReplaySellShares } from '@/hooks';
import { formatPrice, formatPnL } from '@/lib/formatters';
import { useState } from 'react';

export function ReplayPortfolioPage() {
  const { data: portfolio, isLoading } = useReplayPortfolio();
  const { currentRace } = useReplay();
  const sellShares = useReplaySellShares();
  const [sellingMarketId, setSellingMarketId] = useState<number | null>(null);

  const positions = portfolio?.positions || [];
  const totalPnL = portfolio?.total_pnl;

  // Group positions by settled status
  const activePositions = positions.filter(
    (p) => !p.is_settled && p.shares > 0
  );
  const settledPositions = positions.filter(
    (p) => p.is_settled && p.shares > 0
  );

  const handleSellSettled = async (marketId: number, shares: number) => {
    setSellingMarketId(marketId);
    try {
      await sellShares.mutateAsync({ marketId, quantity: shares });
    } finally {
      setSellingMarketId(null);
    }
  };

  if (isLoading) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Loading portfolio...
      </div>
    );
  }

  const unrealizedPnL = totalPnL ? formatPnL(totalPnL.unrealized) : null;
  const realizedPnL = totalPnL ? formatPnL(totalPnL.realized) : null;
  const totalPnLFormatted = totalPnL ? formatPnL(totalPnL.total) : null;

  return (
    <div>
      <PageHeader
        title="Replay Portfolio"
        description="Your positions across all races"
        breadcrumbs={[
          { label: 'Replay', href: '/replay' },
          { label: 'Dashboard', href: '/replay/dashboard' },
          { label: 'Portfolio' },
        ]}
      />

      {/* PnL Summary */}
      {totalPnL && (
        <div className="grid gap-4 md:grid-cols-3 mb-6">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Unrealized P&L
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div
                className={`text-2xl font-bold ${
                  unrealizedPnL?.isPositive ? 'text-green-600' : 'text-red-600'
                }`}
              >
                {unrealizedPnL?.value || '$0.00'}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Realized P&L
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div
                className={`text-2xl font-bold ${
                  realizedPnL?.isPositive ? 'text-green-600' : 'text-red-600'
                }`}
              >
                {realizedPnL?.value || '$0.00'}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total P&L
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div
                className={`text-2xl font-bold ${
                  totalPnLFormatted?.isPositive ? 'text-green-600' : 'text-red-600'
                }`}
              >
                {totalPnLFormatted?.value || '$0.00'}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Active Positions (Current Race) */}
      <Card>
        <CardHeader>
          <CardTitle>Active Positions</CardTitle>
          <CardDescription>
            Positions in the current race - trade on the bonding curve
          </CardDescription>
        </CardHeader>
        <CardContent>
          {activePositions.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <p>You don't have any active positions in the current race.</p>
              <Link
                to="/replay/dashboard"
                className="text-primary hover:underline mt-2 inline-block"
              >
                Browse markets to start trading
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-3">Driver</th>
                    <th className="text-left p-3">Race</th>
                    <th className="text-right p-3">Shares</th>
                    <th className="text-right p-3">Avg Entry</th>
                    <th className="text-right p-3">Current</th>
                    <th className="text-right p-3">Value</th>
                    <th className="text-right p-3">Unrealized P&L</th>
                    <th className="text-right p-3"></th>
                  </tr>
                </thead>
                <tbody>
                  {activePositions.map((position) => {
                    const unrealized = formatPnL(position.unrealized_pnl);
                    const isCurrentRace = position.race_number === currentRace;

                    return (
                      <tr key={position.position_id} className="border-b last:border-0">
                        <td className="p-3">
                          <div className="font-medium">{position.driver_code}</div>
                          <div className="text-sm text-muted-foreground">
                            {position.driver_name}
                          </div>
                        </td>
                        <td className="p-3">
                          <Badge variant={isCurrentRace ? 'default' : 'outline'}>
                            Race {position.race_number}
                          </Badge>
                        </td>
                        <td className="p-3 text-right">{position.shares.toFixed(4)}</td>
                        <td className="p-3 text-right">
                          {formatPrice(position.avg_entry_price)}
                        </td>
                        <td className="p-3 text-right">
                          {formatPrice(position.current_price)}
                        </td>
                        <td className="p-3 text-right font-medium">
                          {formatPrice(position.market_value)}
                        </td>
                        <td
                          className={`p-3 text-right ${
                            unrealized.isPositive ? 'text-green-600' : 'text-red-600'
                          }`}
                        >
                          {unrealized.value}
                        </td>
                        <td className="p-3 text-right">
                          {isCurrentRace && position.shares > 0 && (
                            <Link
                              to={`/replay/markets/${position.market_id}`}
                              className="text-primary hover:underline text-sm"
                            >
                              Trade
                            </Link>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Settled Positions (Past Races) */}
      {settledPositions.length > 0 && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lock className="h-4 w-4" />
              Settled Positions
            </CardTitle>
            <CardDescription>
              Positions from past races locked at their settlement value. Sell anytime to convert to cash.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-3">Driver</th>
                    <th className="text-left p-3">Race</th>
                    <th className="text-right p-3">Shares</th>
                    <th className="text-right p-3">Settlement Value</th>
                    <th className="text-right p-3">Total Value</th>
                    <th className="text-right p-3"></th>
                  </tr>
                </thead>
                <tbody>
                  {settledPositions.map((position) => {
                    const isSelling = sellingMarketId === position.market_id;

                    return (
                      <tr key={position.position_id} className="border-b last:border-0">
                        <td className="p-3">
                          <div className="font-medium">{position.driver_code}</div>
                          <div className="text-sm text-muted-foreground">
                            {position.driver_name}
                          </div>
                        </td>
                        <td className="p-3">
                          <Badge variant="outline">
                            Race {position.race_number}
                          </Badge>
                        </td>
                        <td className="p-3 text-right">{position.shares.toFixed(4)}</td>
                        <td className="p-3 text-right">
                          {formatPrice(position.current_price)} pts
                        </td>
                        <td className="p-3 text-right font-medium text-blue-600">
                          {formatPrice(position.market_value)}
                        </td>
                        <td className="p-3 text-right">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleSellSettled(position.market_id, position.shares)}
                            disabled={isSelling}
                          >
                            {isSelling ? 'Selling...' : 'Sell All'}
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-950 rounded-lg">
              <div className="flex justify-between items-center">
                <span className="font-medium">Total Settled Value</span>
                <span className="text-xl font-bold text-blue-600">
                  {formatPrice(settledPositions.reduce((sum, p) => sum + p.market_value, 0))}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
