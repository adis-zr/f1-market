import { Link } from 'react-router-dom';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useReplayPortfolio, useReplay } from '@/hooks';
import { formatPrice, formatPnL } from '@/lib/formatters';

export function ReplayPortfolioPage() {
  const { data: portfolio, isLoading } = useReplayPortfolio();
  const { currentRace } = useReplay();

  const positions = portfolio?.positions || [];
  const totalPnL = portfolio?.total_pnl;

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

      {/* Positions */}
      <Card>
        <CardHeader>
          <CardTitle>Active Positions</CardTitle>
        </CardHeader>
        <CardContent>
          {positions.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <p>You don't have any positions yet.</p>
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
                    <th className="text-right p-3">Unrealized P&L</th>
                    <th className="text-right p-3">Realized P&L</th>
                    <th className="text-right p-3"></th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((position) => {
                    const unrealized = formatPnL(position.unrealized_pnl);
                    const realized = formatPnL(position.realized_pnl);
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
                        <td
                          className={`p-3 text-right ${
                            unrealized.isPositive ? 'text-green-600' : 'text-red-600'
                          }`}
                        >
                          {unrealized.value}
                        </td>
                        <td
                          className={`p-3 text-right ${
                            realized.isPositive ? 'text-green-600' : 'text-red-600'
                          }`}
                        >
                          {realized.value}
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
    </div>
  );
}
