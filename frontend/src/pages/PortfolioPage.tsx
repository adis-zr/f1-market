import { PageHeader } from '@/components/layout/PageHeader';
import { PortfolioSummary } from '@/components/portfolio/PortfolioSummary';
import { PositionTable } from '@/components/portfolio/PositionTable';
import { usePortfolio } from '@/hooks/usePortfolio';

export function PortfolioPage() {
  const { positions, isLoading } = usePortfolio();

  return (
    <div>
      <PageHeader
        title="Portfolio"
        description="View your positions and portfolio performance"
      />
      <div className="space-y-6">
        <PortfolioSummary />
        <div>
          <h2 className="text-2xl font-bold mb-4">Positions</h2>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading positions...
            </div>
          ) : (
            <PositionTable positions={positions || []} />
          )}
        </div>
      </div>
    </div>
  );
}

