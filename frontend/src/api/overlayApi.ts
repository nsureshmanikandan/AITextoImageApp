import { apiClient } from './client';

export interface SuggestOverlayParams {
  company: string;
  field: 'badge' | 'cta';
  promptContext?: string;
}

export async function suggestOverlayText(params: SuggestOverlayParams): Promise<string> {
  const { data } = await apiClient.post<{ suggestion: string }>('/suggest-overlay', {
    company: params.company,
    field: params.field,
    prompt_context: params.promptContext ?? '',
  });
  return data.suggestion;
}
