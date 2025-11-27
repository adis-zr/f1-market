import { usePositions } from './usePositions';
import { useWallet } from './useWallet';
import { useMemo } from 'react';

export function usePortfolio() {
  const { data: positions = [], ...positionsQuery } = usePositions();
  const { data: wallet } = useWallet();

  const portfolioValue = useMemo(() => {
    if (!positions || !wallet) return null;
    
    const positionsValue = positions.reduce((sum, pos) => {
      if (pos.current_price && pos.shares) {
        return sum + pos.current_price * pos.shares;
      }
      return sum;
    }, 0);

    return wallet.available_balance + positionsValue;
  }, [positions, wallet]);

  const totalPnL = useMemo(() => {
    if (!positions) return null;
    return positions.reduce((sum, pos) => sum + (pos.total_pnl || 0), 0);
  }, [positions]);

  const positionsBySport = useMemo(() => {
    // This would need sport info from market/event data
    // For now, return empty object
    return {};
  }, [positions]);

  return {
    positions,
    wallet,
    portfolioValue,
    totalPnL,
    positionsBySport,
    ...positionsQuery,
  };
}

