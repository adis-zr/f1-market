import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Bot } from 'lucide-react';
import { formatPrice, formatDate } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import type { ReplayLeaderboardEntry, ReplayDifficulty } from '@/api/types';

interface LeaderboardTableProps {
  entries: ReplayLeaderboardEntry[];
  yourBest?: {
    rank: number;
    final_balance: number;
    return_pct: number;
    difficulty: ReplayDifficulty;
    completed_at: string | null;
  } | null;
  showTitle?: boolean;
  compact?: boolean;
  showDifficulty?: boolean;
}

const DIFFICULTY_COLORS: Record<ReplayDifficulty, string> = {
  easy: 'bg-green-500/20 text-green-700',
  medium: 'bg-yellow-500/20 text-yellow-700',
  hard: 'bg-red-500/20 text-red-700',
};

export function LeaderboardTable({
  entries,
  yourBest,
  showTitle = true,
  compact = false,
  showDifficulty = false,
}: LeaderboardTableProps) {
  const getRankBadge = (rank: number) => {
    if (rank === 1) return <Badge className="bg-yellow-500">1st</Badge>;
    if (rank === 2) return <Badge className="bg-gray-400">2nd</Badge>;
    if (rank === 3) return <Badge className="bg-amber-600">3rd</Badge>;
    return <Badge variant="outline">{rank}</Badge>;
  };

  return (
    <Card>
      {showTitle && (
        <CardHeader>
          <CardTitle>Leaderboard</CardTitle>
        </CardHeader>
      )}
      <CardContent className={!showTitle ? 'pt-6' : ''}>
        {yourBest && (
          <div className="mb-4 p-3 bg-primary/10 rounded-lg border border-primary/20">
            <div className="flex justify-between items-center">
              <div>
                <span className="text-sm text-muted-foreground">Your Best Run</span>
                <div className="flex items-center gap-2 mt-1">
                  {getRankBadge(yourBest.rank)}
                  <span className="font-semibold">{formatPrice(yourBest.final_balance)}</span>
                  <span
                    className={cn(
                      'text-sm',
                      yourBest.return_pct >= 0 ? 'text-green-600' : 'text-red-600'
                    )}
                  >
                    ({yourBest.return_pct >= 0 ? '+' : ''}{yourBest.return_pct.toFixed(1)}%)
                  </span>
                </div>
              </div>
              {yourBest.completed_at && (
                <span className="text-xs text-muted-foreground">
                  {formatDate(yourBest.completed_at)}
                </span>
              )}
            </div>
          </div>
        )}

        {entries.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            No completed replays yet. Be the first!
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-2">Rank</th>
                  <th className="text-left p-2">Player</th>
                  {showDifficulty && <th className="text-center p-2">Difficulty</th>}
                  <th className="text-right p-2">Final Balance</th>
                  {!compact && <th className="text-right p-2">Return</th>}
                  {!compact && <th className="text-right p-2">Date</th>}
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={`${entry.user_id ?? 'ai'}-${entry.username}-${entry.completed_at}`} className="border-b last:border-0">
                    <td className="p-2">{getRankBadge(entry.rank)}</td>
                    <td className="p-2 font-medium">
                      <span className="flex items-center gap-2">
                        {entry.username}
                        {entry.is_ai && (
                          <span title="AI Player">
                            <Bot className="h-4 w-4 text-muted-foreground" />
                          </span>
                        )}
                      </span>
                    </td>
                    {showDifficulty && (
                      <td className="p-2 text-center">
                        <Badge className={DIFFICULTY_COLORS[entry.difficulty]}>
                          {entry.difficulty.charAt(0).toUpperCase() + entry.difficulty.slice(1)}
                        </Badge>
                      </td>
                    )}
                    <td className="p-2 text-right font-semibold">
                      {formatPrice(entry.final_balance)}
                    </td>
                    {!compact && (
                      <td
                        className={cn(
                          'p-2 text-right',
                          entry.return_pct >= 0 ? 'text-green-600' : 'text-red-600'
                        )}
                      >
                        {entry.return_pct >= 0 ? '+' : ''}{entry.return_pct.toFixed(1)}%
                      </td>
                    )}
                    {!compact && (
                      <td className="p-2 text-right text-muted-foreground">
                        {entry.is_ai ? '-' : formatDate(entry.completed_at)}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
