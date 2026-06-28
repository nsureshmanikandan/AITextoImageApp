import { apiClient } from './client';
import type { GenerateImageParams, JobStatus, RegenerateParams, RefinePromptParams, PromptVersion } from '@/types';

export async function submitGeneration(params: GenerateImageParams): Promise<{ jobId: string; status: string }> {
  const { data } = await apiClient.post('/generate-image', {
    prompt: params.prompt,
    num_variations: params.numVariations,
    preset_id: params.presetId,
    image_formats: params.imageFormats,
  });
  return { jobId: data.job_id, status: data.status };
}

export async function regenerateImage(params: RegenerateParams): Promise<{ jobId: string; status: string }> {
  const { data } = await apiClient.post('/regenerate', {
    image_id: params.imageId,
    edited_prompt: params.editedPrompt,
  });
  return { jobId: data.job_id, status: data.status };
}

export async function refinePrompt(params: RefinePromptParams): Promise<PromptVersion> {
  const { data } = await apiClient.post('/refine-prompt', {
    prompt_version_id: params.promptVersionId,
    edited_text: params.editedText,
  });
  return {
    id: data.id,
    promptInputId: data.prompt_input_id,
    originalInput: data.original_input ?? '',
    generatedPrompt: data.generated_prompt,
    negativePrompt: data.negative_prompt,
    versionNumber: data.version_number,
    source: data.source,
    createdAt: data.created_at,
  };
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const { data } = await apiClient.get(`/jobs/${jobId}`);
  return {
    jobId: data.job_id,
    status: data.status,
    createdAt: data.created_at,
    completedAt: data.completed_at,
    results: data.results?.map((r: Record<string, unknown>) => ({
      imageId: r.image_id,
      promptVersionId: r.prompt_version_id,
      generatedPrompt: r.generated_prompt,
      negativePrompt: r.negative_prompt,
      seed: r.seed,
      thumbnailUrl: r.thumbnail_url,
      fullUrl: r.full_url,
    })),
    error: data.error ? {
      errorCode: data.error.error_code,
      message: data.error.message,
      requestId: data.error.request_id,
    } : undefined,
  };
}
