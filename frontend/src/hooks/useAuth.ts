import { useQuery } from '@tanstack/react-query';
import { authApi } from '@/api/endpoints';
import type { User } from '@/api/types';

export function useCurrentUser() {
  return useQuery<User>({
    queryKey: ['currentUser'],
    queryFn: () => authApi.getCurrentUser(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

