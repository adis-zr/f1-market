import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useReplay, useStartReplay, useReplayLeaderboard } from '@/hooks';
import { formatPrice } from '@/lib/formatters';
import { Play, Trophy, RefreshCw, TrendingUp, Users, Bot } from 'lucide-react';
import type { ReplayDifficulty } from '@/api/types';
import { cn } from '@/lib/utils';

const DIFFICULTY_CONFIG = {
  easy: {
    label: 'Easy',
    aiCount: 5,
    description: 'Fewer AI players with weaker strategies',
    color: 'border-green-500',
  },
  medium: {
    label: 'Medium',
    aiCount: 10,
    description: 'Balanced mix of AI strategies',
    color: 'border-yellow-500',
  },
  hard: {
    label: 'Hard',
    aiCount: 20,
    description: 'Many skilled AI competitors',
    color: 'border-red-500',
  },
} as const;

export function ReplayLandingPage() {
  const navigate = useNavigate();
  const { hasActiveSession, currentRace, isLoading, session } = useReplay();
  const startReplay = useStartReplay();
  const { data: leaderboard } = useReplayLeaderboard(10);
  const [selectedDifficulty, setSelectedDifficulty] = useState<ReplayDifficulty>('medium');

  const handleStartOrContinue = async () => {
    if (hasActiveSession) {
      navigate('/replay/dashboard');
    } else {
      try {
        await startReplay.mutateAsync(selectedDifficulty);
        navigate('/replay/dashboard');
      } catch (error) {
        console.error('Failed to start replay:', error);
      }
    }
  };

  return (
    <div>
      <PageHeader
        title="Replay 2024 Season"
        description="Relive the 2024 F1 season and test your trading skills"
      />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Hero Card */}
        <Card className="lg:col-span-2">
          <CardContent className="pt-6">
            <div className="text-center space-y-6">
              <div className="space-y-2">
                <h2 className="text-3xl font-bold">2024 Formula 1 World Championship</h2>
                <p className="text-muted-foreground max-w-2xl mx-auto">
                  Start with $100 and trade your way through all 24 races.
                  Buy and sell driver stocks before each race, then see how your predictions
                  perform based on actual race results.
                </p>
              </div>

              <div className="grid grid-cols-3 gap-4 max-w-xl mx-auto">
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">$100</div>
                  <div className="text-sm text-muted-foreground">Starting Balance</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">24</div>
                  <div className="text-sm text-muted-foreground">Races</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">20</div>
                  <div className="text-sm text-muted-foreground">Drivers</div>
                </div>
              </div>

              {isLoading ? (
                <div className="py-4 text-muted-foreground">Loading...</div>
              ) : hasActiveSession ? (
                <div className="space-y-4">
                  <div className="text-sm text-muted-foreground">
                    You have an active session at Race {currentRace} of 24
                    {session?.difficulty && (
                      <span className="ml-2 font-medium">
                        ({DIFFICULTY_CONFIG[session.difficulty].label} difficulty)
                      </span>
                    )}
                  </div>
                  <Button size="lg" onClick={handleStartOrContinue}>
                    <Play className="mr-2 h-5 w-5" />
                    Continue Replay
                  </Button>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Difficulty Selection */}
                  <div className="space-y-3">
                    <div className="text-sm font-medium text-muted-foreground">Select Difficulty</div>
                    <div className="grid grid-cols-3 gap-4 max-w-2xl mx-auto">
                      {(Object.entries(DIFFICULTY_CONFIG) as [ReplayDifficulty, typeof DIFFICULTY_CONFIG.easy][]).map(
                        ([key, config]) => (
                          <Card
                            key={key}
                            className={cn(
                              'cursor-pointer transition-all hover:shadow-md',
                              selectedDifficulty === key
                                ? `border-2 ${config.color} bg-accent/50`
                                : 'border'
                            )}
                            onClick={() => setSelectedDifficulty(key)}
                          >
                            <CardContent className="pt-4 pb-4 text-center">
                              <div className="font-semibold text-lg">{config.label}</div>
                              <div className="flex items-center justify-center gap-1 text-sm text-muted-foreground mt-1">
                                <Bot className="h-4 w-4" />
                                <span>{config.aiCount} AI players</span>
                              </div>
                              <div className="text-xs text-muted-foreground mt-2">
                                {config.description}
                              </div>
                            </CardContent>
                          </Card>
                        )
                      )}
                    </div>
                  </div>

                  <Button
                    size="lg"
                    onClick={handleStartOrContinue}
                    disabled={startReplay.isPending}
                  >
                    {startReplay.isPending ? (
                      <RefreshCw className="mr-2 h-5 w-5 animate-spin" />
                    ) : (
                      <Play className="mr-2 h-5 w-5" />
                    )}
                    Start Replay
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* How It Works */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              How It Works
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="space-y-4 list-decimal list-inside text-sm">
              <li className="text-muted-foreground">
                <span className="font-medium text-foreground">Start with $100</span> -
                Your virtual trading balance for the entire season
              </li>
              <li className="text-muted-foreground">
                <span className="font-medium text-foreground">Trade before each race</span> -
                Buy shares of drivers you think will score points
              </li>
              <li className="text-muted-foreground">
                <span className="font-medium text-foreground">Advance to see results</span> -
                Markets settle based on actual 2024 race outcomes
              </li>
              <li className="text-muted-foreground">
                <span className="font-medium text-foreground">Earn points-based payouts</span> -
                Higher finishing positions = more points = higher settlement
              </li>
              <li className="text-muted-foreground">
                <span className="font-medium text-foreground">Complete all 24 races</span> -
                Your final balance determines your leaderboard rank
              </li>
            </ol>
          </CardContent>
        </Card>

        {/* Leaderboard Preview */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Trophy className="h-5 w-5" />
              Leaderboard
            </CardTitle>
            <CardDescription>
              Top performers who completed the season
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!leaderboard?.entries.length ? (
              <div className="text-center py-6 text-muted-foreground">
                No completed replays yet. Be the first!
              </div>
            ) : (
              <div className="space-y-2">
                {leaderboard.entries.slice(0, 5).map((entry) => (
                  <div
                    key={`${entry.user_id}-${entry.completed_at}`}
                    className="flex items-center justify-between py-2 border-b last:border-0"
                  >
                    <div className="flex items-center gap-3">
                      <span className={`font-bold w-6 ${
                        entry.rank === 1 ? 'text-yellow-500' :
                        entry.rank === 2 ? 'text-gray-400' :
                        entry.rank === 3 ? 'text-amber-600' : ''
                      }`}>
                        #{entry.rank}
                      </span>
                      <span className="font-medium">{entry.username}</span>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold">{formatPrice(entry.final_balance)}</div>
                      <div className={`text-xs ${entry.return_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {entry.return_pct >= 0 ? '+' : ''}{entry.return_pct.toFixed(1)}%
                      </div>
                    </div>
                  </div>
                ))}
                {leaderboard.entries.length > 5 && (
                  <Button
                    variant="link"
                    className="w-full mt-2"
                    onClick={() => navigate('/replay/leaderboard')}
                  >
                    View Full Leaderboard
                  </Button>
                )}
              </div>
            )}
            {leaderboard?.your_best && (
              <div className="mt-4 pt-4 border-t">
                <div className="text-sm text-muted-foreground">Your Best Result</div>
                <div className="flex items-center justify-between mt-1">
                  <span className="font-medium">Rank #{leaderboard.your_best.rank}</span>
                  <span className="font-semibold">{formatPrice(leaderboard.your_best.final_balance)}</span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
