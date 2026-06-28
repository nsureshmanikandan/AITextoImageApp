import { apiClient } from './client';
import type { JobStatus } from '@/types';

export async function pollJobStatus(jobId: string): Promise<JobStatus> {
  const { data } = await apiClient.get(`/jobs/${jobId}`);

  // The backend returns: { result: { results: [...], prompt_version_id: "..." } }
  let results = undefined;
  if (data.status === 'completed' && data.result?.results) {
    results = data.result.results.map((r: Record<string, unknown>) => ({
      imageId: r.image_id as string,
      promptVersionId: r.prompt_version_id as string,
      generatedPrompt: (r.generated_prompt as string) || '',
      negativePrompt: (r.negative_prompt as string) || undefined,
      seed: r.seed as number,
      thumbnailUrl: '',
      fullUrl: '',
    }));
  }

  return {
    jobId: data.job_id,
    status: data.status,
    createdAt: data.created_at,
    completedAt: data.completed_at,
    results,
    error: data.error ? {
      errorCode: data.error.error_code || data.error.error || 'UNKNOWN',
      message: data.error.message || data.error.error || 'Generation failed',
      requestId: data.error.request_id || '',
    } : undefined,
  };
}
