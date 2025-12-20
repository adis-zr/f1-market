import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { formatPrice } from '@/lib/formatters';
import type { ReplaySettlementSummary } from '@/api/types';

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

          {/* Your Payouts */}
          {settlement.your_payouts.length > 0 && (
            <div>
              <h4 className="text-sm font-medium mb-3">Your Payouts</h4>
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-muted">
                    <tr>
                      <th className="text-left p-2">Driver</th>
                      <th className="text-right p-2">Shares</th>
                      <th className="text-right p-2">Payout</th>
                    </tr>
                  </thead>
                  <tbody>
                    {settlement.your_payouts.map((payout) => (
                      <tr key={payout.driver_code} className="border-t">
                        <td className="p-2 font-medium">{payout.driver_code}</td>
                        <td className="p-2 text-right">{payout.shares.toFixed(4)}</td>
                        <td className="p-2 text-right text-green-600 font-medium">
                          +{formatPrice(payout.payout)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-3 p-3 bg-green-50 dark:bg-green-950 rounded-lg">
                <div className="flex justify-between items-center">
                  <span className="font-medium">Total Payout</span>
                  <span className="text-xl font-bold text-green-600">
                    +{formatPrice(settlement.total_payout)}
                  </span>
                </div>
              </div>
            </div>
          )}

          {settlement.your_payouts.length === 0 && (
            <div className="text-center py-4 text-muted-foreground">
              You had no positions to settle for this race.
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
