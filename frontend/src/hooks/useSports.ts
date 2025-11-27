import { useQuery } from '@tanstack/react-query';
import { sportsApi } from '@/api/endpoints';
import { queryKeys } from './queryKeys';
import type { Sport } from '@/api/types';

export function useSports() {
  return useQuery<Sport[]>({
    queryKey: queryKeys.sports,
    queryFn: () => sportsApi.getSports(),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

