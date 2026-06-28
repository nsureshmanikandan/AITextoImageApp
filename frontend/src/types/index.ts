// API request/response types for the AI Image Generation Platform

export interface GenerateImageParams {
  prompt: string;
  numVariations: number;
  presetId?: string;
  imageFormats?: string[];
}

export interface JobStatus {
  jobId: string;
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'timed_out';
  createdAt: string;
  completedAt?: string;
  results?: ImageResult[];
  error?: ErrorDetail;
}

export interface ImageResult {
  imageId: string;
  promptVersionId: string;
  generatedPrompt: string;
  negativePrompt?: string;
  seed: number;
  thumbnailUrl: string;
  fullUrl: string;
}

export interface PromptVersion {
  id: string;
  promptInputId: string;
  originalInput: string;
  generatedPrompt: string;
  negativePrompt?: string;
  versionNumber: number;
  source: 'optimization' | 'user_edit';
  createdAt: string;
}

export interface Preset {
  id: string;
  name: string;
  style?: string;
  lighting?: string;
  composition?: string;
  quality?: string;
  negativePrompt?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface CreatePresetParams {
  name: string;
  style?: string;
  lighting?: string;
  composition?: string;
  quality?: string;
  negativePrompt?: string;
}

export interface UpdatePresetParams extends CreatePresetParams {}

export interface ErrorDetail {
  errorCode: string;
  message: string;
  requestId: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface HistoryFilters {
  page?: number;
  pageSize?: number;
  dateFrom?: string;
  dateTo?: string;
  search?: string;
}

export interface GalleryFilters {
  page?: number;
  pageSize?: number;
  dateFrom?: string;
  dateTo?: string;
  search?: string;
}

export interface PromptHistoryItem {
  id: string;
  userInput: string;
  createdAt: string;
  versionCount: number;
  latestImageUrl?: string;
}

export interface RegenerateParams {
  imageId: string;
  editedPrompt?: string;
}

export interface RefinePromptParams {
  promptVersionId: string;
  editedText: string;
}

export interface GalleryImage {
  id: string;
  promptVersionId: string;
  storagePath: string;
  contentType: string;
  fileSizeBytes: number;
  width: number;
  height: number;
  seed: number;
  modelName: string;
  generationTimeMs: number;
  createdAt: string;
  url: string;
  prompt?: string;
}
