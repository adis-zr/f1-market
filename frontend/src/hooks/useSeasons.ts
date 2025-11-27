import { useQuery } from '@tanstack/react-query';
import { sportsApi } from '@/api/endpoints';
import { queryKeys } from './queryKeys';
import type { Season } from '@/api/types';

export function useSeasons(leagueId?: number) {
  return useQuery<Season[]>({
    queryKey: queryKeys.seasons(leagueId),
    queryFn: () => sportsApi.getSeasons(leagueId),
    enabled: !!leagueId,
    staleTime: 10 * 60 * 1000,
  });
}

