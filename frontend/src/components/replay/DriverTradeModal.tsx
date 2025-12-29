import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { useReplayMarket, useReplay } from '@/hooks';
import { formatPrice, formatPnL } from '@/lib/formatters';
import { ReplayOrderPanel } from './ReplayOrderPanel';

interface DriverTradeModalProps {
  open: boolean;
  onClose: () => void;
  marketId: number | null;
}

export function DriverTradeModal({
  open,
  onClose,
  marketId,
}: DriverTradeModalProps) {
  const { data, isLoading: marketLoading } = useReplayMarket(marketId ?? 0);
  const { wallet, currentRace } = useReplay();

  if (!marketId) return null;

  const market = data?.market;
  const position = data?.position;
  const balance = wallet?.balance ?? 0;

  // Determine if trading should be disabled
  const isDisabled = !market || market.status !== 'open' || market.race_number !== currentRace;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            {marketLoading ? (
              <span>Loading...</span>
            ) : market ? (
              <>
                <span className="font-mono text-2xl">{market.driver_code}</span>
                <Badge variant={market.status === 'open' ? 'default' : 'secondary'}>
                  {formatPrice(market.current_price)}
                </Badge>
              </>
            ) : (
              <span>Market not found</span>
            )}
          </DialogTitle>
          {market && (
            <DialogDescription>
              {market.driver_name} - {market.team_name}
            </DialogDescription>
          )}
        </DialogHeader>

        {marketLoading ? (
          <div className="py-8 text-center text-muted-foreground">
            Loading market data...
          </div>
        ) : market ? (
          <div className="space-y-4">
            {/* Position Summary */}
            {position && position.shares > 0 && (
              <div className="rounded-lg border bg-muted/50 p-4">
                <div className="text-sm font-medium mb-2">Your Position</div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">Shares</span>
                    <div className="font-medium">{position.shares.toFixed(2)}</div>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Avg Entry</span>
                    <div className="font-medium">{formatPrice(position.avg_entry_price)}</div>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Market Value</span>
                    <div className="font-medium">{formatPrice(position.market_value)}</div>
                  </div>
                  <div>
                    <span className="text-muted-foreground">P&L</span>
                    <div className={`font-medium ${
                      position.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {formatPnL(position.unrealized_pnl)?.value || '$0.00'}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Order Panel */}
            <ReplayOrderPanel
              marketId={marketId}
              market={market}
              position={position}
              balance={balance}
              disabled={isDisabled}
            />
          </div>
        ) : (
          <div className="py-8 text-center text-muted-foreground">
            Market not found
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
