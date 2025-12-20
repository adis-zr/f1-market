import { Link } from 'react-router-dom';
import { PageHeader } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/button';
import { useReplayLeaderboard, useReplay } from '@/hooks';
import { LeaderboardTable } from '@/components/replay/LeaderboardTable';

export function ReplayLeaderboardPage() {
  const { data: leaderboard, isLoading } = useReplayLeaderboard();
  const { session } = useReplay();

  const hasActiveSession = session && session.status === 'active';

  if (isLoading) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Loading leaderboard...
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Leaderboard"
        description="Top performers in the 2024 F1 season replay challenge"
        breadcrumbs={[
          { label: 'Replay', href: '/replay' },
          { label: 'Leaderboard' },
        ]}
      />

      <div className="mb-6">
        {hasActiveSession ? (
          <Link to="/replay/dashboard">
            <Button>Back to Dashboard</Button>
          </Link>
        ) : (
          <Link to="/replay">
            <Button>Start Your Replay</Button>
          </Link>
        )}
      </div>

      <LeaderboardTable
        entries={leaderboard?.entries || []}
        yourBest={leaderboard?.your_best}
      />
    </div>
  );
}
