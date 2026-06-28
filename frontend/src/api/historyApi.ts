import { apiClient } from './client';
import type { PaginatedResponse, PromptHistoryItem, HistoryFilters } from '@/types';

export async function fetchHistory(filters: HistoryFilters): Promise<PaginatedResponse<PromptHistoryItem>> {
  const params: Record<string, string | number> = {};
  if (filters.page) params.page = filters.page;
  if (filters.pageSize) params.page_size = filters.pageSize;
  if (filters.dateFrom) params.date_from = filters.dateFrom;
  if (filters.dateTo) params.date_to = filters.dateTo;
  if (filters.search) params.search = filters.search;

  const { data } = await apiClient.get('/history', { params });
  return {
    items: data.items.map((item: Record<string, unknown>) => ({
      id: item.id,
      userInput: item.user_input,
      createdAt: item.created_at,
      versionCount: item.version_count,
      latestImageUrl: item.latest_image_url,
    })),
    total: data.total,
    page: data.page,
    pageSize: data.page_size,
  };
}
