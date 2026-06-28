import { apiClient } from './client';
import type { Preset, CreatePresetParams, UpdatePresetParams } from '@/types';

function mapPreset(data: Record<string, unknown>): Preset {
  return {
    id: data.id as string,
    name: data.name as string,
    style: data.style as string | undefined,
    lighting: data.lighting as string | undefined,
    composition: data.composition as string | undefined,
    quality: data.quality as string | undefined,
    negativePrompt: data.negative_prompt as string | undefined,
    createdAt: data.created_at as string | undefined,
    updatedAt: data.updated_at as string | undefined,
  };
}

export async function fetchPresets(): Promise<Preset[]> {
  const { data } = await apiClient.get('/presets');
  return (data as Record<string, unknown>[]).map(mapPreset);
}

export async function createPreset(params: CreatePresetParams): Promise<Preset> {
  const { data } = await apiClient.post('/presets', {
    name: params.name,
    style: params.style,
    lighting: params.lighting,
    composition: params.composition,
    quality: params.quality,
    negative_prompt: params.negativePrompt,
  });
  return mapPreset(data);
}

export async function updatePreset(id: string, params: UpdatePresetParams): Promise<Preset> {
  const { data } = await apiClient.put(`/presets/${id}`, {
    name: params.name,
    style: params.style,
    lighting: params.lighting,
    composition: params.composition,
    quality: params.quality,
    negative_prompt: params.negativePrompt,
  });
  return mapPreset(data);
}

export async function deletePreset(id: string): Promise<void> {
  await apiClient.delete(`/presets/${id}`);
}
