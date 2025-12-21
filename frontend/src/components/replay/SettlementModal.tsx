import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Bot, Trophy } from 'lucide-react';
import { formatPrice } from '@/lib/formatters';
import type { ReplaySettlementSummary } from '@/api/types';
import { cn } from '@/lib/utils';

interface SettlementModalProps {
  open: boolean;
  onClose: () => void;
  settlement: ReplaySettlementSummary | null;
  isSeasonComplete?: boolean;
}

export function SettlementModal({
  open,
  onClose,
  settlement,
  isSeasonComplete,
}: SettlementModalProps) {
  if (!settlement) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            Race {settlement.race_number} Results
          </DialogTitle>
          <DialogDescription>
            {settlement.race_name}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Race Results */}
          <div>
            <h4 className="text-sm font-medium mb-3">Race Results</h4>
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted">
                  <tr>
                    <th className="text-left p-2">Pos</th>
                    <th className="text-left p-2">Driver</th>
                    <th className="text-right p-2">Points</th>
                    <th className="text-right p-2">Payout/Share</th>
                  </tr>
                </thead>
                <tbody>
                  {settlement.results.slice(0, 10).map((result) => (
                    <tr key={result.driver_code} className="border-t">
                      <td className="p-2">
                        <Badge variant={result.position <= 3 ? 'default' : 'outline'}>
                          P{result.position}
                        </Badge>
                      </td>
                      <td className="p-2">
                        <span className="font-medium">{result.driver_code}</span>
                        <span className="text-muted-foreground ml-2">
                          {result.driver_name}
                        </span>
                      </td>
                      <td className="p-2 text-right">{result.points}</td>
                      <td className="p-2 text-right">
                        {formatPrice(result.payout_per_share)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Your Settled Positions */}
          {settlement.your_settled_positions.length > 0 && (
            <div>
              <h4 className="text-sm font-medium mb-2">Your Settled Positions</h4>
              <p className="text-xs text-muted-foreground mb-3">
                Your shares are now locked at their settlement value. Sell to convert to cash.
              </p>
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-muted">
                    <tr>
                      <th className="text-left p-2">Driver</th>
                      <th className="text-right p-2">Shares</th>
                      <th className="text-right p-2">Pts/Share</th>
                      <th className="text-right p-2">Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {settlement.your_settled_positions.map((pos) => (
                      <tr key={pos.driver_code} className="border-t">
                        <td className="p-2 font-medium">{pos.driver_code}</td>
                        <td className="p-2 text-right">{pos.shares.toFixed(4)}</td>
                        <td className="p-2 text-right">{pos.points_per_share}</td>
                        <td className="p-2 text-right text-blue-600 font-medium">
                          {formatPrice(pos.settlement_value)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-950 rounded-lg">
                <div className="flex justify-between items-center">
                  <span className="font-medium">Total Settled Value</span>
                  <span className="text-xl font-bold text-blue-600">
                    {formatPrice(settlement.total_settled_value)}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Sell these positions anytime to add to your cash balance
                </p>
              </div>
            </div>
          )}

          {settlement.your_settled_positions.length === 0 && (
            <div className="text-center py-4 text-muted-foreground">
              You had no positions to settle for this race.
            </div>
          )}

          {/* Mini-Leaderboard */}
          {settlement.mini_leaderboard && (
            <div>
              <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                <Trophy className="h-4 w-4" />
                Current Standings
              </h4>
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-muted">
                    <tr>
                      <th className="text-left p-2 w-12">Rank</th>
                      <th className="text-left p-2">Player</th>
                      <th className="text-right p-2">Balance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {settlement.mini_leaderboard.entries.map((entry, idx) => {
                      // Add separator before user context entries (after top 3)
                      const showSeparator = idx === 3;
                      return (
                        <>
                          {showSeparator && (
                            <tr key="separator">
                              <td colSpan={3} className="text-center text-xs text-muted-foreground py-1 bg-muted/50">
                                ⋯
                              </td>
                            </tr>
                          )}
                          <tr
                            key={`${entry.name}-${entry.rank}`}
                            className={cn(
                              'border-t',
                              !entry.is_ai && 'bg-primary/10 font-medium'
                            )}
                          >
                            <td className="p-2">
                              {entry.rank <= 3 ? (
                                <Badge
                                  variant={entry.rank === 1 ? 'default' : 'outline'}
                                  className={cn(
                                    entry.rank === 1 && 'bg-yellow-500 hover:bg-yellow-500',
                                    entry.rank === 2 && 'border-gray-400 text-gray-600',
                                    entry.rank === 3 && 'border-orange-400 text-orange-600'
                                  )}
                                >
                                  #{entry.rank}
                                </Badge>
                              ) : (
                                <span className="text-muted-foreground">#{entry.rank}</span>
                              )}
                            </td>
                            <td className="p-2 flex items-center gap-1">
                              {entry.name}
                              {entry.is_ai && <Bot className="h-3 w-3 text-muted-foreground" />}
                            </td>
                            <td className="p-2 text-right">{formatPrice(entry.balance)}</td>
                          </tr>
                        </>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div className="mt-2 text-sm text-muted-foreground text-center">
                You are ranked <span className="font-medium text-foreground">#{settlement.mini_leaderboard.user_rank}</span> of {settlement.mini_leaderboard.total_players} players
              </div>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-4 border-t">
            <Button onClick={onClose}>
              {isSeasonComplete ? 'View Final Results' : 'Continue to Next Race'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
