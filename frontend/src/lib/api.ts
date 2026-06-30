import axios from 'axios'
import type { Job, DashboardStats, ScrapePreview, Language, VideoFormat, TrendingTopic } from '../types'

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
