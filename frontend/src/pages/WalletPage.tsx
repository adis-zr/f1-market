import { useState } from 'react';
import { PageHeader } from '@/components/layout/PageHeader';
import { WalletSummaryCard } from '@/components/wallet/WalletSummaryCard';
import { LedgerTable } from '@/components/wallet/LedgerTable';
import { useLedger } from '@/hooks';
import { Select } from '@/components/ui/select';

export function WalletPage() {
  const [transactionType, setTransactionType] = useState<string>('');
  const { data: ledgerEntries = [], isLoading } = useLedger({
    limit: 100,
    type: transactionType || undefined,
  });

  return (
    <div>
      <PageHeader
        title="Wallet"
        description="View your balance and transaction history"
        actions={
          <Select
            value={transactionType}
            onChange={(e) => setTransactionType(e.target.value)}
          >
            <option value="">All Types</option>
            <option value="deposit">Deposit</option>
            <option value="withdrawal">Withdrawal</option>
            <option value="buy">Buy</option>
            <option value="sell">Sell</option>
            <option value="settlement">Settlement</option>
            <option value="fee">Fee</option>
          </Select>
        }
      />
      <div className="space-y-6">
        <WalletSummaryCard />
        <div>
          <h2 className="text-2xl font-bold mb-4">Transaction History</h2>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading transactions...
            </div>
          ) : (
            <LedgerTable entries={ledgerEntries} />
          )}
        </div>
      </div>
    </div>
  );
}

