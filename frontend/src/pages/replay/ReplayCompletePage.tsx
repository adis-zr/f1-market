import { Link, useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useReplay, useResetReplay, useReplayLeaderboard } from '@/hooks';
import { formatPrice, formatPnL } from '@/lib/formatters';
import { LeaderboardTable } from '@/components/replay/LeaderboardTable';

export function ReplayCompletePage() {
  const navigate = useNavigate();
  const { session, wallet, totalPnL, isLoading } = useReplay();
  const resetMutation = useResetReplay();
  const { data: leaderboard } = useReplayLeaderboard();

  if (isLoading) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Loading...
      </div>
    );
  }

  if (!session || session.status !== 'completed') {
    return (
      <div className="text-center py-8">
        <p className="text-muted-foreground">No completed replay found.</p>
        <Link to="/replay" className="text-primary hover:underline mt-4 inline-block">
          Start a new replay
        </Link>
      </div>
    );
  }

  const finalBalance = wallet?.balance || 0;
  const startingBalance = 100;
  const returnPct = ((finalBalance - startingBalance) / startingBalance) * 100;
  const totalPnLFormatted = totalPnL ? formatPnL(totalPnL.total) : null;

  const handlePlayAgain = async () => {
    try {
      await resetMutation.mutateAsync();
      navigate('/replay/dashboard');
    } catch {
      // Error handled by mutation
    }
  };

  return (
    <div>
      <PageHeader
        title="Season Complete!"
        description="Congratulations on completing the 2024 F1 season replay"
        breadcrumbs={[
          { label: 'Replay', href: '/replay' },
          { label: 'Complete' },
        ]}
      />

      {/* Final Results */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 mb-8">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Starting Balance
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatPrice(startingBalance)}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Final Balance
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatPrice(finalBalance)}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Return
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div
              className={`text-2xl font-bold ${
                returnPct >= 0 ? 'text-green-600' : 'text-red-600'
              }`}
            >
              {returnPct >= 0 ? '+' : ''}{returnPct.toFixed(1)}%
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

      {/* Your Ranking */}
      {leaderboard?.your_best && (
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Your Leaderboard Position</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <span className="text-4xl font-bold">#{leaderboard.your_best.rank}</span>
                <span className="text-muted-foreground ml-2">
                  out of {leaderboard.entries.length} players
                </span>
              </div>
              <Link to="/replay/leaderboard">
                <Button variant="outline">View Full Leaderboard</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Top 10 Leaderboard */}
      <div className="mb-8">
        <LeaderboardTable
          entries={leaderboard?.entries.slice(0, 10) || []}
          yourBest={leaderboard?.your_best}
        />
      </div>

      {/* Actions */}
      <div className="flex justify-center gap-4">
        <Button
          size="lg"
          onClick={handlePlayAgain}
          disabled={resetMutation.isPending}
        >
          {resetMutation.isPending ? 'Resetting...' : 'Play Again'}
        </Button>
        <Link to="/replay/leaderboard">
          <Button size="lg" variant="outline">
            Full Leaderboard
          </Button>
        </Link>
      </div>
    </div>
  );
}
