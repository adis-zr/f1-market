import { PageHeader } from '@/components/layout/PageHeader';
import { WalletSummaryCard } from '@/components/wallet/WalletSummaryCard';
import { PortfolioSummary } from '@/components/portfolio/PortfolioSummary';
import { MarketCard } from '@/components/market/MarketCard';
import { useMarkets } from '@/hooks/useMarkets';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export function DashboardPage() {
  const { data: featuredMarkets = [], isLoading } = useMarkets({ status: 'open' });

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Overview of your portfolio and featured markets"
      />
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2">
          <WalletSummaryCard />
          <PortfolioSummary />
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Featured Markets</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="text-center py-8 text-muted-foreground">
                Loading markets...
              </div>
            ) : featuredMarkets.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No featured markets available
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {featuredMarkets.slice(0, 6).map((market) => (
                  <MarketCard key={market.market_id} market={market} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

