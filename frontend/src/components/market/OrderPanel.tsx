import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useMarket } from '@/hooks/useMarkets';
import { usePosition } from '@/hooks/usePositions';
import { useWallet } from '@/hooks/useWallet';
import { useBuyShares } from '@/hooks/useBuyShares';
import { useSellShares } from '@/hooks/useSellShares';
import { formatPrice, formatShares } from '@/lib/formatters';
import { useToast } from '@/hooks/useToast';

interface OrderPanelProps {
  marketId: number;
}

export function OrderPanel({ marketId }: OrderPanelProps) {
  const [quantity, setQuantity] = useState('');
  const [activeTab, setActiveTab] = useState<'buy' | 'sell'>('buy');
  const { data: market } = useMarket(marketId);
  const { data: position } = usePosition(marketId);
  const { data: wallet } = useWallet(marketId);
  const buyMutation = useBuyShares(marketId);
  const sellMutation = useSellShares(marketId);
  const { toast } = useToast();

  const qty = parseFloat(quantity) || 0;
  const currentPrice = market?.current_price || 0;
  const estimatedCost = qty * currentPrice;
  const estimatedPayout = qty * currentPrice;
  const availableShares = position?.shares || 0;
  const availableBalance = wallet?.available_balance || 0;

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
      await buyMutation.mutateAsync({ quantity: qty });
      toast({ title: 'Success', description: `Bought ${qty} shares` });
      setQuantity('');
    } catch (error: unknown) {
      const err = error as { response?: { data?: { error?: string } } };
      toast({
        title: 'Error',
        description: err.response?.data?.error || 'Failed to buy shares',
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
      await sellMutation.mutateAsync({ quantity: qty });
      toast({ title: 'Success', description: `Sold ${qty} shares` });
      setQuantity('');
    } catch (error: unknown) {
      const err = error as { response?: { data?: { error?: string } } };
      toast({
        title: 'Error',
        description: err.response?.data?.error || 'Failed to sell shares',
        variant: 'destructive',
      });
    }
  };

  const isLoading = buyMutation.isPending || sellMutation.isPending;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Trade</CardTitle>
      </CardHeader>
      <CardContent>
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
                <span className="font-medium">{formatPrice(estimatedCost)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Available balance</span>
                <span>{formatPrice(availableBalance)}</span>
              </div>
            </div>
            <Button
              className="w-full"
              onClick={handleBuy}
              disabled={isLoading || qty <= 0 || estimatedCost > availableBalance}
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
                <span className="font-medium">{formatPrice(estimatedPayout)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Your shares</span>
                <span>{formatShares(availableShares)}</span>
              </div>
            </div>
            <Button
              className="w-full"
              onClick={handleSell}
              disabled={isLoading || qty <= 0 || qty > availableShares}
            >
              {isLoading ? 'Processing...' : 'Sell Shares'}
            </Button>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

