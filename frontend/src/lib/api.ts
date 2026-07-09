import axios from 'axios'
import type { DashboardStats, FeedConfiguration, Job, Language, LiveNewsDashboardStats, QueueItem, ScrapePreview, TrendingTopic, VideoFormat } from '../types'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const message = err.response?.data?.detail ?? err.message ?? 'An error occurred'
    return Promise.reject(new Error(message))
  }
)

export interface CreateJobPayload {
  article_url: string
  language: Language
  format: VideoFormat
  mode?: string
  brand_data?: string
}

export async function createJob(payload: CreateJobPayload): Promise<Job> {
  const { data } = await api.post<Job>('/api/jobs', payload)
  return data
}

export async function getJob(id: string): Promise<Job> {
  const { data } = await api.get<Job>(`/api/jobs/${id}`)
  return data
}

export async function listJobs(params?: { status?: string; page?: number; limit?: number }): Promise<Job[]> {
  const { data } = await api.get<Job[]>('/api/jobs', { params })
  return data
}

export async function approveJob(id: string): Promise<Job> {
  const { data } = await api.post<Job>(`/api/jobs/${id}/approve`)
  return data
}

export async function rejectJob(id: string): Promise<Job> {
  const { data } = await api.post<Job>(`/api/jobs/${id}/reject`)
  return data
}

export async function deleteJob(id: string): Promise<void> {
  await api.delete(`/api/jobs/${id}`)
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await api.get<DashboardStats>('/api/dashboard/stats')
  return data
}

export async function getScrapePreview(url: string): Promise<ScrapePreview> {
  const { data } = await api.get<ScrapePreview>('/api/scrape-preview', { params: { url } })
  return data
}

export function getVideoUrl(videoPath: string): string {
  if (videoPath.startsWith('http')) return videoPath
  // videoPath may be an absolute Windows path (C:\...\media\job_8.mp4)
  // or a relative path — always serve via /media/<filename>
  const filename = videoPath.replace(/\\/g, '/').split('/').pop()
  return `${BASE_URL}/media/${filename}`
}

export function getWebSocketUrl(jobId: string): string {
  const wsBase = BASE_URL.replace(/^http/, 'ws')
  return `${wsBase}/ws/jobs/${jobId}`
}

export async function getTrendingSuggestions(category?: string): Promise<TrendingTopic[]> {
  const { data } = await api.get<TrendingTopic[]>('/api/jobs/trending', { params: { category } })
  return data
}

export async function suggestTopics(mode: 'educational' | 'batch' = 'educational', category = 'AI'): Promise<{ label: string; hot: boolean }[]> {
  const { data } = await api.get<{ topics: { label: string; hot: boolean }[] }>(
    '/api/jobs/suggest-topics', { params: { mode, category } }
  )
  return data.topics ?? []
}

export interface AdCopyVariant {
  headline: string
  subline: string
  cta: string
}

export async function saveSoraPrompt(id: string, prompt: string): Promise<Job> {
  const { data } = await api.patch<Job>(`/api/jobs/${id}/sora-prompt`, { prompt })
  return data
}

export async function regenerateSoraPrompt(
  id: string,
  prompt: string,
): Promise<{ status: string; videostoreid: string }> {
  const { data } = await api.post(`/api/jobs/${id}/regenerate-sora`, { prompt })
  return data
}

export async function generateAdCopy(
  id: string,
  tone: string,
): Promise<{ variants: AdCopyVariant[] }> {
  const { data } = await api.post(`/api/jobs/${id}/ad-copy`, { tone })
  return data
}

export async function selectAdCopy(
  id: string,
  variant: AdCopyVariant,
  tone: string,
): Promise<Job> {
  const { data } = await api.patch<Job>(`/api/jobs/${id}/ad-copy/select`, { ...variant, tone })
  return data
}


// ─── Live Breaking News API ───────────────────────────────────────────────────

// Feed CRUD
export async function listFeeds(): Promise<FeedConfiguration[]> {
  const { data } = await api.get<FeedConfiguration[]>('/api/feeds')
  return data
}

export async function getFeed(id: number): Promise<FeedConfiguration> {
  const { data } = await api.get<FeedConfiguration>(`/api/feeds/${id}`)
  return data
}

export interface CreateFeedPayload {
  feed_url: string
  display_name: string
  polling_interval_seconds?: number
  language?: string
  priority_keywords?: string
  trust_level?: string
  auto_approve?: boolean
  enabled?: boolean
}

export async function createFeed(payload: CreateFeedPayload): Promise<FeedConfiguration> {
  const { data } = await api.post<FeedConfiguration>('/api/feeds', payload)
  return data
}

export async function updateFeed(id: number, payload: Partial<CreateFeedPayload>): Promise<FeedConfiguration> {
  const { data } = await api.put<FeedConfiguration>(`/api/feeds/${id}`, payload)
  return data
}

export async function deleteFeed(id: number): Promise<void> {
  await api.delete(`/api/feeds/${id}`)
}

export async function validateFeedUrl(id: number): Promise<{ valid: boolean; message?: string }> {
  const { data } = await api.post<{ valid: boolean; message?: string }>(`/api/feeds/${id}/validate`)
  return data
}

// Monitoring lifecycle
export async function startMonitoring(): Promise<{ status: string }> {
  const { data } = await api.post<{ status: string }>('/api/live-news/start')
  return data
}

export async function pauseMonitoring(): Promise<{ status: string }> {
  const { data } = await api.post<{ status: string }>('/api/live-news/pause')
  return data
}

export async function resumeMonitoring(): Promise<{ status: string }> {
  const { data } = await api.post<{ status: string }>('/api/live-news/resume')
  return data
}

export async function stopMonitoring(): Promise<{ status: string }> {
  const { data } = await api.post<{ status: string }>('/api/live-news/stop')
  return data
}

export async function getMonitorStatus(): Promise<{ state: string }> {
  const { data } = await api.get<{ state: string }>('/api/live-news/status')
  return data
}

// Dashboard & Queue
export async function getDashboardLiveNews(): Promise<LiveNewsDashboardStats> {
  const { data } = await api.get<LiveNewsDashboardStats>('/api/live-news/dashboard')
  return data
}

export async function getApprovalQueue(page = 1, pageSize = 20): Promise<QueueItem[]> {
  const { data } = await api.get<QueueItem[]>('/api/live-news/queue', { params: { page, page_size: pageSize } })
  return data
}

export async function approveQueueItem(jobId: number): Promise<{ status: string }> {
  const { data } = await api.post<{ status: string }>(`/api/live-news/queue/${jobId}/approve`)
  return data
}

export async function rejectQueueItem(jobId: number, reason: string): Promise<{ status: string }> {
  const { data } = await api.post<{ status: string }>(`/api/live-news/queue/${jobId}/reject`, { reason })
  return data
}

export async function getFeedArticles(feedId: number): Promise<{ url: string; title: string; detected_at: string; status: string }[]> {
  const { data } = await api.get(`/api/live-news/feeds/${feedId}/articles`)
  return data
}

// WebSocket
export function getLiveNewsWebSocketUrl(): string {
  const wsBase = BASE_URL.replace(/^http/, 'ws')
  return `${wsBase}/ws/live-news`
}
