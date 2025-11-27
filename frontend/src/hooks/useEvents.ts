import { useQuery } from '@tanstack/react-query';
import { eventsApi } from '@/api/endpoints';
import { queryKeys } from './queryKeys';
import type { Event } from '@/api/types';

interface EventFilters {
  sport_id?: number;
  season_id?: number;
  status?: string;
}

export function useEvents(filters?: EventFilters) {
  return useQuery<Event[]>({
    queryKey: queryKeys.events(filters),
    queryFn: () => eventsApi.getEvents(filters),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

export function useEvent(eventId: number) {
  return useQuery<Event>({
    queryKey: queryKeys.event(eventId),
    queryFn: () => eventsApi.getEvent(eventId),
    enabled: !!eventId,
    staleTime: 2 * 60 * 1000,
  });
}

export function useEventMarkets(eventId: number) {
  return useQuery({
    queryKey: queryKeys.eventMarkets(eventId),
    queryFn: () => eventsApi.getEventMarkets(eventId),
    enabled: !!eventId,
    staleTime: 30 * 1000,
  });
}

