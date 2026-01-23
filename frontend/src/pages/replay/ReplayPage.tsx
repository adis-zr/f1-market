import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  useReplay,
  useStartReplay,
  useAdvanceRace,
  useResetReplay,
  useReplayLeaderboard,
} from '@/hooks';
import { formatPrice, formatPnL } from '@/lib/formatters';
import { RaceTimeline } from '@/components/replay/RaceTimeline';
import { SettlementModal } from '@/components/replay/SettlementModal';
import { DriverTradeModal } from '@/components/replay/DriverTradeModal';
import type { ReplaySettlementSummary, ReplayDifficulty } from '@/api/types';
import { cn } from '@/lib/utils';
import {
  Play,
  RefreshCw,
  Wallet,
  TrendingUp,
  Flag,
  AlertTriangle,
  Trophy,
  Bot,
  Plus,
} from 'lucide-react';

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

export function ReplayPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const {
    session,
    wallet,
    currentRaceInfo,
    markets,
    positions,
    totalPnL,
    allRaces,
    hasActiveSession,
    isCompleted,
    currentRace,
    isLoading,
  } = useReplay();

  const startReplay = useStartReplay();
  const advanceRace = useAdvanceRace();
  const resetReplay = useResetReplay();
  const { data: leaderboard } = useReplayLeaderboard(10);

  // Modal states
  const [selectedDifficulty, setSelectedDifficulty] = useState<ReplayDifficulty>('medium');
  const [showStartNewDialog, setShowStartNewDialog] = useState(false);
  const [showSettlement, setShowSettlement] = useState(false);
  const [settlementData, setSettlementData] = useState<ReplaySettlementSummary | null>(null);

  // Trade modal state - synced with URL
  const marketIdFromUrl = searchParams.get('market');
  const [selectedMarketId, setSelectedMarketId] = useState<number | null>(
    marketIdFromUrl ? parseInt(marketIdFromUrl, 10) : null
  );

  // Sync URL changes to state
  useEffect(() => {
    const urlMarketId = searchParams.get('market');
    if (urlMarketId) {
      setSelectedMarketId(parseInt(urlMarketId, 10));
    } else {
      setSelectedMarketId(null);
    }
  }, [searchParams]);

  const handleOpenTradeModal = (marketId: number) => {
    setSelectedMarketId(marketId);
    setSearchParams({ market: marketId.toString() });
  };

  const handleCloseTradeModal = () => {
    setSelectedMarketId(null);
    setSearchParams({});
  };

  const handleStartReplay = async () => {
    try {
      await startReplay.mutateAsync(selectedDifficulty);
    } catch (error) {
      console.error('Failed to start replay:', error);
    }
  };

  const handleStartNewReplay = async () => {
    try {
      // Reset with new difficulty in one call
      await resetReplay.mutateAsync(selectedDifficulty);
      setShowStartNewDialog(false);
    } catch (error) {
      console.error('Failed to start new replay:', error);
    }
  };

  const handleAdvanceRace = async () => {
    try {
      const result = await advanceRace.mutateAsync();
      if (result.settlement_summary) {
        setSettlementData(result.settlement_summary);
        setShowSettlement(true);
      }
      if (result.new_state.session.status === 'completed') {
        navigate('/replay/complete');
      }
    } catch (error) {
      console.error('Failed to advance race:', error);
    }
  };

  // Redirect to complete page if season is finished
  useEffect(() => {
    if (isCompleted) {
      navigate('/replay/complete');
    }
  }, [isCompleted, navigate]);

  const buttonText = currentRace === 0
    ? 'Start Race 1'
    : currentRace < 24
    ? 'Finish Race & Continue'
    : 'Finish Season';

  return (
    <div>
      <PageHeader
        title="Replay 2024 Season"
        description="Relive the 2024 F1 season and test your trading skills"
      />

      <div className="space-y-6">
        {/* Hero Section - Start/Continue Controls */}
        <Card>
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
                    Active session at Race {currentRace} of 24
                    {session?.difficulty && (
                      <span className="ml-2 font-medium">
                        ({DIFFICULTY_CONFIG[session.difficulty].label} difficulty)
                      </span>
                    )}
                  </div>
                  <div className="flex gap-3 justify-center">
                    <Button
                      variant="outline"
                      onClick={() => setShowStartNewDialog(true)}
                    >
                      <Plus className="mr-2 h-4 w-4" />
                      Start New Replay
                    </Button>
                  </div>
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
                    onClick={handleStartReplay}
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

        {/* Dashboard Section - Only show when session is active */}
        {hasActiveSession && (
          <>
            {/* Race Timeline */}
            <RaceTimeline races={allRaces} currentRace={currentRace} />

            {/* Summary Cards */}
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Balance</CardTitle>
                  <Wallet className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {wallet ? formatPrice(wallet.balance) : '$0.00'}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Available for trading
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total P&L</CardTitle>
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  {totalPnL ? (
                    <>
                      <div className={`text-2xl font-bold ${
                        totalPnL.total >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {totalPnL.total >= 0 ? '+' : ''}{formatPrice(totalPnL.total)}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Starting: $100.00
                      </p>
                    </>
                  ) : (
                    <div className="text-2xl font-bold">$0.00</div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Current Race</CardTitle>
                  <Flag className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {currentRace === 0 ? 'Not Started' : `Race ${currentRace}/24`}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {currentRaceInfo?.venue || 'Click Start to begin'}
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Race Info & Action */}
            {currentRaceInfo && (
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>{currentRaceInfo.name}</CardTitle>
                      <CardDescription>
                        {currentRaceInfo.venue} - {currentRaceInfo.date}
                      </CardDescription>
                    </div>
                    <Badge variant="secondary">Race {currentRace}</Badge>
                  </div>
                </CardHeader>
              </Card>
            )}

            {/* Driver Markets Grid */}
            {markets.length > 0 ? (
              <Card>
                <CardHeader>
                  <CardTitle>Driver Markets</CardTitle>
                  <CardDescription>
                    Buy shares of drivers you think will score points. Click to trade.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    {markets.map((market) => {
                      const position = positions.find(p => p.market_id === market.market_id);
                      return (
                        <Card
                          key={market.market_id}
                          className="hover:bg-accent transition-colors cursor-pointer"
                          onClick={() => handleOpenTradeModal(market.market_id)}
                        >
                          <CardContent className="p-4">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-mono font-bold text-lg">
                                {market.driver_code}
                              </span>
                              <Badge variant={market.status === 'open' ? 'default' : 'secondary'}>
                                {formatPrice(market.current_price)}
                              </Badge>
                            </div>
                            <div className="text-sm text-muted-foreground truncate">
                              {market.driver_name}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {market.team_name}
                            </div>
                            {position && position.shares > 0 && (
                              <div className="mt-2 pt-2 border-t">
                                <div className="text-xs text-muted-foreground">
                                  You own: {position.shares.toFixed(2)} shares
                                </div>
                              </div>
                            )}
                          </CardContent>
                        </Card>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            ) : currentRace === 0 ? (
              <Card>
                <CardContent className="text-center py-8">
                  <p className="text-muted-foreground mb-4">
                    Click "Start Race 1" to begin trading
                  </p>
                </CardContent>
              </Card>
            ) : null}

            {/* Action Buttons */}
            <div className="flex flex-wrap gap-4 justify-center">
              <Button
                size="lg"
                onClick={handleAdvanceRace}
                disabled={advanceRace.isPending}
              >
                {advanceRace.isPending ? (
                  <RefreshCw className="mr-2 h-5 w-5 animate-spin" />
                ) : (
                  <Play className="mr-2 h-5 w-5" />
                )}
                {buttonText}
              </Button>
            </div>

            {/* Active Positions */}
            {positions.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Your Positions</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {positions.filter(p => p.shares > 0).map((pos) => {
                      const pnl = formatPnL(pos.unrealized_pnl);
                      return (
                        <div
                          key={pos.position_id}
                          className="flex items-center justify-between py-2 border-b last:border-0 cursor-pointer hover:bg-accent/50 -mx-2 px-2 rounded"
                          onClick={() => handleOpenTradeModal(pos.market_id)}
                        >
                          <div>
                            <span className="font-mono font-bold">{pos.driver_code}</span>
                            <span className="text-muted-foreground ml-2">
                              {pos.shares.toFixed(2)} shares
                            </span>
                          </div>
                          <div className="text-right">
                            <div className={pnl?.isPositive ? 'text-green-600' : 'text-red-600'}>
                              {pnl?.value || '$0.00'}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              Avg: {formatPrice(pos.avg_entry_price)}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        )}

        {/* Leaderboard Preview - Always visible */}
        <div className="grid gap-6 lg:grid-cols-2">
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

      {/* Trade Modal */}
      <DriverTradeModal
        open={selectedMarketId !== null}
        onClose={handleCloseTradeModal}
        marketId={selectedMarketId}
      />

      {/* Settlement Modal */}
      <SettlementModal
        open={showSettlement}
        onClose={() => setShowSettlement(false)}
        settlement={settlementData}
      />

      {/* Start New Replay Confirmation Dialog */}
      <Dialog open={showStartNewDialog} onOpenChange={setShowStartNewDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              Start New Replay?
            </DialogTitle>
            <DialogDescription>
              This will end your current session at Race {currentRace}/24.
              Your progress will be lost and you'll start fresh with $100.
            </DialogDescription>
          </DialogHeader>

          {/* Difficulty Selection in Dialog */}
          <div className="space-y-3 py-4">
            <div className="text-sm font-medium">Select Difficulty</div>
            <div className="grid grid-cols-3 gap-3">
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
                    <CardContent className="pt-3 pb-3 text-center">
                      <div className="font-semibold">{config.label}</div>
                      <div className="flex items-center justify-center gap-1 text-xs text-muted-foreground mt-1">
                        <Bot className="h-3 w-3" />
                        <span>{config.aiCount} AI</span>
                      </div>
                    </CardContent>
                  </Card>
                )
              )}
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowStartNewDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleStartNewReplay}
              disabled={resetReplay.isPending || startReplay.isPending}
            >
              {(resetReplay.isPending || startReplay.isPending) ? 'Starting...' : 'Start New Replay'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
