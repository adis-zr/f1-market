import { useState } from 'react';
import { Link } from 'react-router-dom';
import { PageHeader } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useReplayLeaderboard, useReplay } from '@/hooks';
import { LeaderboardTable } from '@/components/replay/LeaderboardTable';
import type { ReplayDifficulty } from '@/api/types';

type DifficultyFilter = ReplayDifficulty | 'all';

export function ReplayLeaderboardPage() {
  const [selectedDifficulty, setSelectedDifficulty] = useState<DifficultyFilter>('all');
  const { session } = useReplay();

  // Only pass difficulty to hook if not 'all'
  const difficultyParam = selectedDifficulty === 'all' ? undefined : selectedDifficulty;
  const { data: leaderboard, isLoading } = useReplayLeaderboard(50, difficultyParam);

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

      <div className="flex flex-col sm:flex-row sm:items-center gap-4 mb-6">
        <Link to="/replay">
          <Button>{hasActiveSession ? 'Back to Replay' : 'Start Your Replay'}</Button>
        </Link>

        <Tabs
          value={selectedDifficulty}
          onValueChange={(v) => setSelectedDifficulty(v as DifficultyFilter)}
          className="sm:ml-auto"
        >
          <TabsList>
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="easy">Easy</TabsTrigger>
            <TabsTrigger value="medium">Medium</TabsTrigger>
            <TabsTrigger value="hard">Hard</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <LeaderboardTable
        entries={leaderboard?.entries || []}
        yourBest={leaderboard?.your_best}
        showDifficulty={selectedDifficulty === 'all'}
      />
    </div>
  );
}
