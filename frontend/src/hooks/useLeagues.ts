import { useQuery } from '@tanstack/react-query';
import { sportsApi } from '@/api/endpoints';
import { queryKeys } from './queryKeys';
import type { League } from '@/api/types';

export function useLeagues(sportId?: number) {
  return useQuery<League[]>({
    queryKey: queryKeys.leagues(sportId),
    queryFn: () => sportsApi.getLeagues(sportId),
    enabled: !!sportId,
    staleTime: 10 * 60 * 1000,
  });
}

