import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatPrice } from '@/lib/formatters';
import { useWallet } from '@/hooks';

export function WalletSummaryCard() {
  const { data: wallet, isLoading } = useWallet();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Wallet</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-muted-foreground">Loading...</div>
        </CardContent>
      </Card>
    );
  }

  if (!wallet) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Wallet</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-muted-foreground">No wallet data</div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Wallet</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <div className="text-sm text-muted-foreground">Total Balance</div>
          <div className="text-2xl font-bold">{formatPrice(wallet.total_balance)}</div>
        </div>
        <div>
          <div className="text-sm text-muted-foreground">Available Balance</div>
          <div className="text-xl font-semibold">
            {formatPrice(wallet.available_balance)}
          </div>
        </div>
        <div>
          <div className="text-sm text-muted-foreground">Locked Balance</div>
          <div className="text-lg">{formatPrice(wallet.locked_balance)}</div>
        </div>
      </CardContent>
    </Card>
  );
}

