import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
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
import { useReplay, useAdvanceRace, useResetReplay } from '@/hooks';
import { formatPrice, formatPnL } from '@/lib/formatters';
import { RaceTimeline } from '@/components/replay/RaceTimeline';
import { SettlementModal } from '@/components/replay/SettlementModal';
import type { ReplaySettlementSummary } from '@/api/types';
import {
  Play,
  RefreshCw,
  Wallet,
  TrendingUp,
  Flag,
  AlertTriangle,
} from 'lucide-react';

export function ReplayDashboardPage() {
  const navigate = useNavigate();
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

  const advanceRace = useAdvanceRace();
  const resetReplay = useResetReplay();

  const [showSettlement, setShowSettlement] = useState(false);
  const [settlementData, setSettlementData] = useState<ReplaySettlementSummary | null>(null);
  const [showResetDialog, setShowResetDialog] = useState(false);

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

  const handleReset = async () => {
    try {
      await resetReplay.mutateAsync();
      setShowResetDialog(false);
    } catch (error) {
      console.error('Failed to reset replay:', error);
    }
  };

  if (isLoading) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Loading replay session...
      </div>
    );
  }

  if (!hasActiveSession && !isCompleted) {
    return (
      <div className="text-center py-8">
        <p className="text-muted-foreground mb-4">No active replay session</p>
        <Button onClick={() => navigate('/replay')}>
          Start a Replay
        </Button>
      </div>
    );
  }

  if (isCompleted) {
    navigate('/replay/complete');
    return null;
  }

  const buttonText = currentRace === 0
    ? 'Start Race 1'
    : currentRace < 24
    ? 'Finish Race & Continue'
    : 'Finish Season';

  return (
    <div>
      <PageHeader
        title="Replay 2024 Season"
        description={currentRaceInfo ? `${currentRaceInfo.name}` : 'Ready to start'}
        breadcrumbs={[
          { label: 'Replay', href: '/replay' },
          { label: 'Dashboard' },
        ]}
      />

      <div className="space-y-6">
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
                    <Link
                      key={market.market_id}
                      to={`/replay/markets/${market.market_id}`}
                      className="block"
                    >
                      <Card className="hover:bg-accent transition-colors cursor-pointer">
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
                    </Link>
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

          <Button
            variant="outline"
            onClick={() => setShowResetDialog(true)}
            disabled={resetReplay.isPending}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Reset Replay
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
                      className="flex items-center justify-between py-2 border-b last:border-0"
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
      </div>

      {/* Settlement Modal */}
      <SettlementModal
        open={showSettlement}
        onClose={() => setShowSettlement(false)}
        settlement={settlementData}
      />

      {/* Reset Confirmation Dialog */}
      <Dialog open={showResetDialog} onOpenChange={setShowResetDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              Reset Replay?
            </DialogTitle>
            <DialogDescription>
              This will reset your replay session to the beginning. Your current progress
              (Race {currentRace}/24) will be lost. You'll start fresh with $100.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowResetDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleReset}
              disabled={resetReplay.isPending}
            >
              {resetReplay.isPending ? 'Resetting...' : 'Reset'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
