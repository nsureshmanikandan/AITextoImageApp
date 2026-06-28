import { useQuery } from '@tanstack/react-query';
import { fetchHistory } from '@/api/historyApi';
import type { HistoryFilters } from '@/types';

export function useHistory(filters: HistoryFilters) {
  return useQuery({
    queryKey: ['history', filters],
    queryFn: () => fetchHistory(filters),
    staleTime: 30_000,
  });
}
