import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useReplayBuyShares, useReplaySellShares, useReplayEstimateCost, useToast } from '@/hooks';
import { formatPrice, formatShares } from '@/lib/formatters';
import { isApiError } from '@/api/types';
import type { ReplayMarket, ReplayPosition } from '@/api/types';

interface ReplayOrderPanelProps {
  marketId: number;
  market: ReplayMarket;
  position: ReplayPosition | null | undefined;
  balance: number;
  disabled?: boolean;
}

export function ReplayOrderPanel({
  marketId,
  market,
  position,
  balance,
  disabled = false,
}: ReplayOrderPanelProps) {
  const [quantity, setQuantity] = useState('');
  const [activeTab, setActiveTab] = useState<'buy' | 'sell'>('buy');
  const buyMutation = useReplayBuyShares(marketId);
  const sellMutation = useReplaySellShares(marketId);
  const { toast } = useToast();

  const qty = parseFloat(quantity) || 0;
  const currentPrice = market.current_price;
  const availableShares = position?.shares || 0;
  const availableBalance = balance;

  // Use bonding curve estimation for accurate cost/payout
  const { estimate: buyEstimate, isLoading: buyEstimateLoading } = useReplayEstimateCost(
    marketId,
    qty,
    'buy'
  );
  const { estimate: sellEstimate, isLoading: sellEstimateLoading } = useReplayEstimateCost(
    marketId,
    qty,
    'sell'
  );

  // Get accurate cost from bonding curve estimate, fallback to simple multiplication
  const estimatedCost = buyEstimate?.cost ?? qty * currentPrice;
  const estimatedPayout = sellEstimate?.payout ?? qty * currentPrice;

  const handleBuy = async () => {
    if (qty <= 0) {
      toast({ title: 'Error', description: 'Quantity must be greater than 0', variant: 'destructive' });
      return;
    }
    if (estimatedCost > availableBalance) {
      toast({ title: 'Error', description: 'Insufficient balance', variant: 'destructive' });
      return;
    }

    try {
      await buyMutation.mutateAsync(qty);
      toast({ title: 'Success', description: `Bought ${qty} shares of ${market.driver_code}` });
      setQuantity('');
    } catch (error: unknown) {
      const errorMessage = isApiError(error)
        ? error.response.data.error || error.response.data.message || 'Failed to buy shares'
        : 'Failed to buy shares';
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    }
  };

  const handleSell = async () => {
    if (qty <= 0) {
      toast({ title: 'Error', description: 'Quantity must be greater than 0', variant: 'destructive' });
      return;
    }
    if (qty > availableShares) {
      toast({ title: 'Error', description: 'Insufficient shares', variant: 'destructive' });
      return;
    }

    try {
      await sellMutation.mutateAsync(qty);
      toast({ title: 'Success', description: `Sold ${qty} shares of ${market.driver_code}` });
      setQuantity('');
    } catch (error: unknown) {
      const errorMessage = isApiError(error)
        ? error.response.data.error || error.response.data.message || 'Failed to sell shares'
        : 'Failed to sell shares';
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    }
  };

  const isLoading = buyMutation.isPending || sellMutation.isPending;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Trade {market.driver_code}</CardTitle>
      </CardHeader>
      <CardContent>
        {disabled ? (
          <div className="text-center py-6 text-muted-foreground">
            <p className="mb-2">Trading is not available for this market.</p>
            <p className="text-sm">
              {market.status === 'settled'
                ? 'This market has been settled.'
                : 'You can only trade markets for the current race.'}
            </p>
          </div>
        ) : (
          <Tabs value={activeTab} onValueChange={(v: string) => setActiveTab(v as 'buy' | 'sell')}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="buy">Buy</TabsTrigger>
              <TabsTrigger value="sell">Sell</TabsTrigger>
            </TabsList>
            <TabsContent value="buy" className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Quantity</label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  placeholder="0.00"
                  disabled={isLoading}
                />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Price per share</span>
                  <span>{formatPrice(currentPrice)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Estimated cost</span>
                  <span className="font-medium">
                    {buyEstimateLoading ? '...' : formatPrice(estimatedCost)}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Available balance</span>
                  <span>{formatPrice(availableBalance)}</span>
                </div>
              </div>
              <Button
                className="w-full"
                onClick={handleBuy}
                disabled={isLoading || buyEstimateLoading || qty <= 0 || estimatedCost > availableBalance}
              >
                {isLoading ? 'Processing...' : 'Buy Shares'}
              </Button>
            </TabsContent>
            <TabsContent value="sell" className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Quantity</label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  max={availableShares}
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  placeholder="0.00"
                  disabled={isLoading}
                />
                <p className="text-xs text-muted-foreground">
                  Available: {formatShares(availableShares)}
                </p>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Price per share</span>
                  <span>{formatPrice(currentPrice)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Estimated payout</span>
                  <span className="font-medium">
                    {sellEstimateLoading ? '...' : formatPrice(estimatedPayout)}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Your shares</span>
                  <span>{formatShares(availableShares)}</span>
                </div>
              </div>
              <Button
                className="w-full"
                onClick={handleSell}
                disabled={isLoading || sellEstimateLoading || qty <= 0 || qty > availableShares}
              >
                {isLoading ? 'Processing...' : 'Sell Shares'}
              </Button>
            </TabsContent>
          </Tabs>
        )}
      </CardContent>
    </Card>
  );
}
