import { apiClient } from './client';
import type { PaginatedResponse, GalleryImage, GalleryFilters } from '@/types';

export function getImageUrl(imageId: string): string {
  const baseUrl = apiClient.defaults.baseURL || '/api/v1';
  return `${baseUrl}/images/${imageId}`;
}

export async function deleteImage(imageId: string): Promise<void> {
  await apiClient.delete(`/images/${imageId}`);
}

export async function fetchGallery(filters: GalleryFilters): Promise<PaginatedResponse<GalleryImage>> {
  const params: Record<string, string | number> = {};
  if (filters.page) params.page = filters.page;
  if (filters.pageSize) params.page_size = filters.pageSize;
  if (filters.dateFrom) params.date_from = filters.dateFrom;
  if (filters.dateTo) params.date_to = filters.dateTo;
  if (filters.search) params.search = filters.search;

  const { data } = await apiClient.get('/images', { params });
  return {
    items: data.items.map((item: Record<string, unknown>) => ({
      id: item.id,
      promptVersionId: item.prompt_version_id,
      storagePath: item.storage_path,
      contentType: item.content_type,
      fileSizeBytes: item.file_size_bytes,
      width: item.width,
      height: item.height,
      seed: item.seed,
      modelName: item.model_name,
      generationTimeMs: item.generation_time_ms,
      createdAt: item.created_at,
      url: item.url || getImageUrl(item.id as string),
      prompt: item.prompt as string | undefined,
    })),
    total: data.total,
    page: data.page,
    pageSize: data.page_size,
  };
}
