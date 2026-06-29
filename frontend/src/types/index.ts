export type JobStatus =
  | 'pending'
  | 'scraping'
  | 'generating_script'
  | 'generating_voice'
  | 'rendering_video'
  | 'awaiting_review'
  | 'approved'
  | 'ready'
  | 'failed'

export interface JobStep {
  step: string
  status: 'pending' | 'active' | 'done' | 'error'
  message: string
  ts: string
}

export interface Job {
  id: string
  status: JobStatus
  article_url: string
  language: string
  format: string
  script?: string
  video_path?: string
  error?: string
  steps: JobStep[]
  created_at: string
  original_transcript?: string
  timing_score?: number
  translation_score?: number
  quality_details?: string
}

export type Language = 'ta-IN' | 'hi-IN' | 'te-IN' | 'kn-IN' | 'en-IN'
export type VideoFormat = 'vertical_9_16' | 'landscape_16_9'

export interface DashboardStats {
  total_videos: number
  approved: number
  pending_review: number
  languages_used: number
  recent_jobs: Job[]
  weekly_trend: { day: string; count: number }[]
}

export interface ScrapePreview {
  title: string
  description: string
  image?: string
  url: string
}

export const LANGUAGE_OPTIONS: { value: Language; label: string; flag: string; nativeName: string }[] = [
  { value: 'ta-IN', label: 'Tamil', flag: '🇮🇳', nativeName: 'தமிழ்' },
  { value: 'hi-IN', label: 'Hindi', flag: '🇮🇳', nativeName: 'हिंदी' },
  { value: 'te-IN', label: 'Telugu', flag: '🇮🇳', nativeName: 'తెలుగు' },
  { value: 'kn-IN', label: 'Kannada', flag: '🇮🇳', nativeName: 'ಕನ್ನಡ' },
  { value: 'en-IN', label: 'English (India)', flag: '🇮🇳', nativeName: 'English' },
]

export const FORMAT_OPTIONS: { value: VideoFormat; label: string; description: string; aspectRatio: string }[] = [
  { value: 'vertical_9_16', label: 'Vertical 9:16', description: 'Instagram Reels · YouTube Shorts · WhatsApp Status', aspectRatio: '9/16' },
  { value: 'landscape_16_9', label: 'Landscape 16:9', description: 'YouTube · News Portals · Desktop Web', aspectRatio: '16/9' },
]

export const PIPELINE_STEPS = [
  { key: 'scraping', label: 'Scraping Article', description: 'Extracting content from URL' },
  { key: 'generating_script', label: 'Generating Script', description: 'AI writing regional language script' },
  { key: 'generating_voice', label: 'Creating Voice', description: 'Synthesising natural speech' },
  { key: 'rendering_video', label: 'Rendering Video', description: 'Compositing visuals & audio' },
  { key: 'awaiting_review', label: 'Ready for Review', description: 'Video ready — awaiting approval' },
]
