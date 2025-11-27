import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatPrice, formatPnL } from '@/lib/formatters';
import { usePortfolio } from '@/hooks/usePortfolio';
import { useWallet } from '@/hooks/useWallet';

export function PortfolioSummary() {
  const { portfolioValue, totalPnL } = usePortfolio();
  const { data: wallet } = useWallet();

  const totalPnLFormatted = formatPnL(totalPnL);

  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Portfolio Value</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {portfolioValue ? formatPrice(portfolioValue) : '—'}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Total P&L</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            className={`text-2xl font-bold ${
              totalPnLFormatted.isPositive ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {totalPnLFormatted.value}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Available Balance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {wallet ? formatPrice(wallet.available_balance) : '—'}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

