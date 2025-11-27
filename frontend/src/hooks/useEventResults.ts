import { useQuery } from '@tanstack/react-query';
import { eventsApi } from '@/api/endpoints';
import { queryKeys } from './queryKeys';
import type { EventResult } from '@/api/types';

export function useEventResults(eventId: number) {
  return useQuery<EventResult[]>({
    queryKey: queryKeys.eventResults(eventId),
    queryFn: () => eventsApi.getEventResults(eventId),
    enabled: !!eventId,
    staleTime: 5 * 60 * 1000, // 5 minutes (results don't change)
  });
}

