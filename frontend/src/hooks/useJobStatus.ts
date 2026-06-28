import { useQuery } from '@tanstack/react-query';
import { pollJobStatus } from '@/api/jobsApi';
import type { JobStatus } from '@/types';

const TERMINAL_STATUSES = ['completed', 'failed', 'timed_out'];

export function useJobStatus(jobId: string | null) {
  return useQuery<JobStatus>({
    queryKey: ['jobStatus', jobId],
    queryFn: () => pollJobStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status && TERMINAL_STATUSES.includes(status)) {
        return false;
      }
      return 2000;
    },
    staleTime: 0,
  });
}
