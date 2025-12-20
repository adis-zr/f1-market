import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useReplayWallet, useReplayLedger } from '@/hooks';
import { formatPrice, formatDateTime } from '@/lib/formatters';

export function ReplayWalletPage() {
  const { data: wallet, isLoading: walletLoading } = useReplayWallet();
  const { data: ledgerData, isLoading: ledgerLoading } = useReplayLedger();

  const ledger = ledgerData?.ledger || [];

  if (walletLoading) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Loading wallet...
      </div>
    );
  }

  const balance = wallet?.balance || 0;
  const lockedBalance = wallet?.locked_balance || 0;

  const getTransactionBadge = (type: string) => {
    switch (type) {
      case 'deposit':
        return <Badge className="bg-green-500">Deposit</Badge>;
      case 'buy':
        return <Badge className="bg-blue-500">Buy</Badge>;
      case 'sell':
        return <Badge className="bg-purple-500">Sell</Badge>;
      case 'settlement':
        return <Badge className="bg-yellow-500">Settlement</Badge>;
      case 'fee':
        return <Badge variant="outline">Fee</Badge>;
      default:
        return <Badge variant="outline">{type}</Badge>;
    }
  };

  return (
    <div>
      <PageHeader
        title="Replay Wallet"
        description="Your virtual balance and transaction history"
        breadcrumbs={[
          { label: 'Replay', href: '/replay' },
          { label: 'Dashboard', href: '/replay/dashboard' },
          { label: 'Wallet' },
        ]}
      />

      {/* Balance Cards */}
      <div className="grid gap-4 md:grid-cols-2 mb-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Available Balance
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{formatPrice(balance)}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Locked in Positions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-muted-foreground">
              {formatPrice(lockedBalance)}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Transaction History */}
      <Card>
        <CardHeader>
          <CardTitle>Transaction History</CardTitle>
        </CardHeader>
        <CardContent>
          {ledgerLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading transactions...
            </div>
          ) : ledger.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No transactions yet. Start trading to see your history.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-3">Type</th>
                    <th className="text-left p-3">Description</th>
                    <th className="text-right p-3">Amount</th>
                    <th className="text-right p-3">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {ledger.map((entry) => {
                    const isPositive = entry.amount > 0;

                    return (
                      <tr key={entry.id} className="border-b last:border-0">
                        <td className="p-3">
                          {getTransactionBadge(entry.transaction_type)}
                        </td>
                        <td className="p-3 text-muted-foreground">
                          {entry.description || '—'}
                        </td>
                        <td
                          className={`p-3 text-right font-medium ${
                            isPositive ? 'text-green-600' : 'text-red-600'
                          }`}
                        >
                          {isPositive ? '+' : ''}{formatPrice(entry.amount)}
                        </td>
                        <td className="p-3 text-right text-muted-foreground">
                          {formatDateTime(entry.created_at)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
