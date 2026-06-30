import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Globe, Loader2, CheckCircle2, XCircle, ArrowRight, ArrowLeft, Sparkles,
  Newspaper, Play, Megaphone, GraduationCap, Layers,
} from 'lucide-react'
import LanguagePicker from '../components/LanguagePicker'
import FormatPicker from '../components/FormatPicker'
import ProgressStepper from '../components/ProgressStepper'
import { BRAND_AD_PIPELINE_STEPS, EDUCATIONAL_PIPELINE_STEPS } from '../types'
import ModeSelector from '../components/ModeSelector'
import BrandAdForm from '../components/BrandAdForm'
import EducationalForm from '../components/EducationalForm'
import BatchForm from '../components/BatchForm'
import { useJobStore } from '../stores/jobStore'
import { useJobProgress } from '../hooks/useJobProgress'
import { createJob, getScrapePreview } from '../lib/api'
import type { Language, VideoFormat, Job, ScrapePreview, VideoMode, BrandAdParams, EducationalParams } from '../types'
import { cn } from '../lib/utils'

type Step = 1 | 2 | 3 | 4

const MODE_STEP_LABELS: Record<VideoMode, string[]> = {
  article: ['Mode', 'Article URL', 'Language & Format', 'Processing', 'Done'],
  youtube: ['Mode', 'YouTube URL', 'Language & Format', 'Processing', 'Done'],
  brand_ad: ['Mode', 'Brand Details', 'Language & Format', 'Processing', 'Done'],
  educational: ['Mode', 'Topic', 'Language & Format', 'Processing', 'Done'],
  batch: ['Mode', 'Topics', 'Processing', 'Done'],
}

const MODE_ICONS: Record<VideoMode, React.ElementType> = {
  article: Newspaper,
  youtube: Play,
  brand_ad: Megaphone,
  educational: GraduationCap,
  batch: Layers,
}

const MODE_COLORS: Record<VideoMode, string> = {
  article: 'text-azure-400',
  youtube: 'text-red-400',
  brand_ad: 'text-purple-400',
  educational: 'text-emerald-400',
  batch: 'text-amber-400',
}

function StepIndicator({ current, mode }: { current: Step; mode: VideoMode }) {
  const labels = MODE_STEP_LABELS[mode].slice(1) // skip 'Mode' label, steps 1-N map to URL/details etc.
  return (
    <div className="flex items-center gap-2 mb-10">
      {labels.map((label, idx) => {
        const step = (idx + 1) as Step
        const done = current > step
        const active = current === step
        return (
          <div key={step} className="flex items-center gap-2">
            <div className={cn(
              'flex items-center gap-2 transition-all',
              active ? 'opacity-100' : done ? 'opacity-80' : 'opacity-40'
            )}>
              <div className={cn(
                'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all',
                active ? 'bg-azure-600 border-azure-500 text-white' :
                done ? 'bg-emerald-400/20 border-emerald-400 text-emerald-400' :
                'bg-navy-800 border-navy-600 text-slate-500'
              )}>
                {done ? '✓' : step}
              </div>
              <span className={cn('text-xs font-medium hidden sm:block', active ? 'text-white' : 'text-slate-500')}>
                {label}
              </span>
            </div>
            {idx < labels.length - 1 && (
              <div className={cn('w-8 sm:w-16 h-px', done ? 'bg-emerald-400/40' : 'bg-white/10')} />
            )}
          </div>
        )
      })}
    </div>
  )
}

function ModeBadge({ mode }: { mode: VideoMode }) {
  const Icon = MODE_ICONS[mode]
  const colorClass = MODE_COLORS[mode]
  const labels: Record<VideoMode, string> = {
    article: 'News Article',
    youtube: 'YouTube Dub',
    brand_ad: 'Brand Ad',
    educational: 'Educational',
    batch: 'Batch / Trending',
  }
  return (
    <div className={`flex items-center gap-1.5 text-xs font-medium mb-4 ${colorClass}`}>
      <Icon className="w-3.5 h-3.5" />
      {labels[mode]}
    </div>
  )
}

export default function CreateVideo() {
  const navigate = useNavigate()
  const { addJob } = useJobStore()

  // Mode selection (shown before step 1)
  const [selectedMode, setSelectedMode] = useState<VideoMode>('article')
  const [modeConfirmed, setModeConfirmed] = useState(false)

  const [step, setStep] = useState<Step>(1)

  // Step 1 — article/youtube URL
  const [url, setUrl] = useState('')
  const [urlError, setUrlError] = useState('')
  const [preview, setPreview] = useState<ScrapePreview | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  // Brand ad / educational params (filled by child forms before advancing)
  const [brandAdPayload, setBrandAdPayload] = useState<(BrandAdParams & { brand_colors?: string[] }) | null>(null)
  const [educationalPayload, setEducationalPayload] = useState<EducationalParams | null>(null)

  // Step 2 — language + format (article/youtube/brand_ad/educational)
  const [language, setLanguage] = useState<Language | null>(null)
  const [format, setFormat] = useState<VideoFormat | null>(null)

  // Processing
  const [createdJob, setCreatedJob] = useState<Job | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const [elapsedSeconds, setElapsedSeconds] = useState(0)

  useJobProgress(createdJob?.id ?? null)

  const liveJob = useJobStore((s) =>
    createdJob ? s.jobs.find((j) => j.id === createdJob.id) ?? createdJob : null
  )

  // Determine processing step number based on mode
  const processingStep: Step = selectedMode === 'batch' ? 2 : 3
  const doneStep: Step = selectedMode === 'batch' ? 3 : 4

  useEffect(() => {
    if (step !== processingStep) return
    const interval = setInterval(() => setElapsedSeconds((s) => s + 1), 1000)
    return () => clearInterval(interval)
  }, [step, processingStep])

  useEffect(() => {
    if (!liveJob) return
    if (liveJob.status === 'awaiting_review' || liveJob.status === 'ready') {
      setTimeout(() => setStep(doneStep), 500)
    }
    if (liveJob.status === 'failed') {
      setSubmitError(liveJob.error ?? 'Processing failed. Please try again.')
    }
  }, [liveJob?.status]) // eslint-disable-line react-hooks/exhaustive-deps

  const validateUrl = (val: string) => {
    try { new URL(val); return '' }
    catch { return 'Please enter a valid URL (include https://)' }
  }

  const handleUrlBlur = async () => {
    const err = validateUrl(url)
    setUrlError(err)
    if (!err && url) {
      setPreviewLoading(true)
      try {
        const p = await getScrapePreview(url)
        setPreview(p)
      } catch {
        setPreview({ title: new URL(url).hostname, description: url, url })
      } finally {
        setPreviewLoading(false)
      }
    }
  }

  const handleStep1Next = async () => {
    const err = validateUrl(url)
    if (err) { setUrlError(err); return }
    if (!preview) await handleUrlBlur()
    setStep(2)
  }

  const handleBrandAdSubmit = (params: BrandAdParams & { brand_colors?: string[] }) => {
    setBrandAdPayload(params)
    setStep(2)
  }

  const handleEducationalSubmit = (params: EducationalParams) => {
    setEducationalPayload(params)
    setStep(2)
  }

  const submitJob = async (articleUrl: string, lang: Language, fmt: VideoFormat, extraData?: Record<string, unknown>) => {
    setSubmitting(true)
    setSubmitError('')
    setElapsedSeconds(0)
    try {
      const job = await createJob({
        article_url: articleUrl,
        language: lang,
        format: fmt,
        mode: selectedMode,
        brand_data: extraData ? JSON.stringify(extraData) : undefined,
      })
      addJob(job)
      setCreatedJob(job)
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to create job')
    } finally {
      setSubmitting(false)
    }
  }

  const handleStep2Next = async () => {
    if (!language || !format) return
    if (selectedMode === 'article' || selectedMode === 'youtube') {
      await submitJob(url, language, format)
    } else if (selectedMode === 'brand_ad' && brandAdPayload) {
      await submitJob(brandAdPayload.brand_name, language, format, brandAdPayload as unknown as Record<string, unknown>)
    } else if (selectedMode === 'educational' && educationalPayload) {
      await submitJob(educationalPayload.topic || '', language, format, educationalPayload as unknown as Record<string, unknown>)
    }
    setStep(3)
  }

  const handleBatchSubmit = async (topics: string[], lang: string, fmt: string, soraIntro: boolean) => {
    setStep(2)
    setElapsedSeconds(0)
    setSubmitting(true)
    setSubmitError('')
    try {
      const job = await createJob({
        article_url: topics.length === 1 ? topics[0] : `Batch: ${topics.slice(0, 2).join(', ')}${topics.length > 2 ? '…' : ''}`,
        language: lang as Language,
        format: fmt as VideoFormat,
        mode: 'batch',
        brand_data: JSON.stringify({ topics, sora_intro: soraIntro }),
      })
      addJob(job)
      setCreatedJob(job)
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to create batch job')
    } finally {
      setSubmitting(false)
    }
  }

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`

  // Mode selection screen (before main steps)
  if (!modeConfirmed) {
    return (
      <div className="page-container max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white mb-2">Create a New Video</h1>
          <p className="text-slate-400 text-sm">Choose how you'd like to create your regional language video.</p>
        </div>
        <ModeSelector selectedMode={selectedMode} onSelect={setSelectedMode} />
        <div className="mt-6 flex justify-end">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setModeConfirmed(true)}
            className="btn-primary flex items-center gap-2"
          >
            Continue with {selectedMode === 'article' ? 'News Article' : selectedMode === 'youtube' ? 'YouTube Dub' : selectedMode === 'brand_ad' ? 'Brand Ad' : selectedMode === 'educational' ? 'Educational' : 'Batch'}
            <ArrowRight className="w-4 h-4" />
          </motion.button>
        </div>
      </div>
    )
  }

  return (
    <div className="page-container max-w-3xl mx-auto">
      <div className="flex items-center gap-3 mb-2">
        <button
          onClick={() => { setModeConfirmed(false); setStep(1) }}
          className="text-slate-500 hover:text-slate-300 text-xs flex items-center gap-1 transition-colors"
        >
          <ArrowLeft className="w-3 h-3" /> Change mode
        </button>
      </div>
      <StepIndicator current={step} mode={selectedMode} />

      <AnimatePresence mode="wait">

        {/* ARTICLE / YOUTUBE: Step 1 — URL */}
        {(selectedMode === 'article' || selectedMode === 'youtube') && step === 1 && (
          <motion.div
            key="step1-url"
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -24 }}
            transition={{ duration: 0.35 }}
          >
            <div className="glass-card p-8">
              <ModeBadge mode={selectedMode} />
              <div className="mb-8 text-center">
                <div className="w-14 h-14 rounded-2xl bg-azure-600/20 border border-azure-500/30 flex items-center justify-center mx-auto mb-4">
                  <Globe className="w-7 h-7 text-azure-400" />
                </div>
                <h2 className="text-2xl font-bold text-white mb-2">
                  {selectedMode === 'youtube' ? 'Paste a YouTube URL' : 'Paste your news article URL'}
                </h2>
                <p className="text-slate-400 text-sm">
                  {selectedMode === 'youtube'
                    ? "We'll dub the video audio into your chosen regional language."
                    : "We'll scrape the content and turn it into a regional language video."}
                </p>
              </div>

              <div className="relative mb-4">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500">
                  <Globe className="w-5 h-5" />
                </div>
                <input
                  type="url"
                  value={url}
                  onChange={(e) => { setUrl(e.target.value); setUrlError('') }}
                  onBlur={handleUrlBlur}
                  onKeyDown={(e) => e.key === 'Enter' && handleStep1Next()}
                  placeholder={selectedMode === 'youtube' ? 'https://www.youtube.com/watch?v=...' : 'https://www.thehindu.com/news/...'}
                  className={cn(
                    'input-field pl-12 pr-4 text-base h-14',
                    urlError && 'border-red-500/50 focus:border-red-500'
                  )}
                  autoFocus
                />
              </div>

              {urlError && (
                <motion.p
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-red-400 text-xs mb-4 flex items-center gap-1.5"
                >
                  <XCircle className="w-3.5 h-3.5" /> {urlError}
                </motion.p>
              )}

              <AnimatePresence>
                {previewLoading && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="flex items-center gap-3 bg-navy-900/60 border border-white/10 rounded-xl p-4 mb-4">
                      <Loader2 className="w-4 h-4 text-azure-400 animate-spin" />
                      <span className="text-sm text-slate-400">Fetching preview…</span>
                    </div>
                  </motion.div>
                )}
                {preview && !previewLoading && (
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 8 }}
                    className="bg-navy-900/60 border border-white/10 rounded-xl p-4 mb-6 flex gap-4"
                  >
                    {preview.image && (
                      <img src={preview.image} alt="" className="w-16 h-16 rounded-lg object-cover flex-shrink-0 bg-navy-700" />
                    )}
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5 mb-1">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                        <span className="text-xs text-emerald-400 font-medium">Found</span>
                      </div>
                      <p className="text-sm font-semibold text-white line-clamp-2 mb-1">{preview.title}</p>
                      <p className="text-xs text-slate-500 truncate">{preview.url}</p>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              <button
                onClick={handleStep1Next}
                disabled={!url}
                className="btn-primary w-full flex items-center justify-center gap-2 h-12 text-base"
              >
                Continue
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </motion.div>
        )}

        {/* BRAND AD: Step 1 — form */}
        {selectedMode === 'brand_ad' && step === 1 && (
          <motion.div
            key="step1-brand"
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -24 }}
            transition={{ duration: 0.35 }}
          >
            <ModeBadge mode={selectedMode} />
            <BrandAdForm onSubmit={handleBrandAdSubmit} loading={false} />
          </motion.div>
        )}

        {/* EDUCATIONAL: Step 1 — form */}
        {selectedMode === 'educational' && step === 1 && (
          <motion.div
            key="step1-edu"
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -24 }}
            transition={{ duration: 0.35 }}
          >
            <ModeBadge mode={selectedMode} />
            <EducationalForm onSubmit={handleEducationalSubmit} loading={false} />
          </motion.div>
        )}

        {/* BATCH: Step 1 — batch form (has its own language/format, submits directly to processing) */}
        {selectedMode === 'batch' && step === 1 && (
          <motion.div
            key="step1-batch"
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -24 }}
            transition={{ duration: 0.35 }}
          >
            <ModeBadge mode={selectedMode} />
            <BatchForm onBatchSubmit={handleBatchSubmit} loading={false} />
          </motion.div>
        )}

        {/* STEP 2: Language + Format (article / youtube / brand_ad / educational) */}
        {selectedMode !== 'batch' && step === 2 && (
          <motion.div
            key="step2"
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -24 }}
            transition={{ duration: 0.35 }}
          >
            <div className="glass-card p-8">
              <ModeBadge mode={selectedMode} />
              <div className="mb-8">
                <h2 className="text-2xl font-bold text-white mb-2">Choose language & format</h2>
                <p className="text-slate-400 text-sm">Select the output language and video aspect ratio.</p>
              </div>

              <div className="mb-8">
                <h3 className="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider">Output Language</h3>
                <LanguagePicker value={language} onChange={setLanguage} />
              </div>

              <div className="mb-8">
                <h3 className="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider">Video Format</h3>
                <FormatPicker value={format} onChange={setFormat} />
              </div>

              <div className="flex gap-3">
                <button onClick={() => setStep(1)} className="btn-secondary flex items-center gap-2">
                  <ArrowLeft className="w-4 h-4" /> Back
                </button>
                <button
                  onClick={handleStep2Next}
                  disabled={!language || !format || submitting}
                  className="btn-primary flex-1 flex items-center justify-center gap-2 h-12 text-base"
                >
                  {submitting ? (
                    <><Loader2 className="w-4 h-4 animate-spin" /> Creating job…</>
                  ) : (
                    <><Sparkles className="w-4 h-4" /> Start Processing</>
                  )}
                </button>
              </div>
            </div>
          </motion.div>
        )}

        {/* PROCESSING STEP (step 3 for article/youtube/brand_ad/educational; step 2 for batch) */}
        {step === processingStep && (
          <motion.div
            key="processing"
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.97 }}
            transition={{ duration: 0.35 }}
          >
            <div className="glass-card p-8">
              <div className="mb-8 text-center">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
                  className="w-16 h-16 rounded-full border-2 border-azure-500/30 border-t-azure-500 mx-auto mb-4"
                />
                <h2 className="text-2xl font-bold text-white mb-2">AI is crafting your video</h2>
                <p className="text-slate-400 text-sm">
                  Elapsed: <span className="text-azure-400 font-mono">{formatTime(elapsedSeconds)}</span>
                  {liveJob?.status !== 'failed' && ' · Est. 2–4 minutes'}
                </p>
              </div>

              {submitError ? (
                <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 mb-6 text-center">
                  <XCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
                  <p className="text-red-400 text-sm font-medium">{submitError}</p>
                </div>
              ) : (
                <div className="mb-8">
                  <ProgressStepper
                    steps={liveJob?.steps ?? []}
                    currentStatus={liveJob?.status}
                    pipelineSteps={
                      liveJob?.mode === 'brand_ad'
                        ? BRAND_AD_PIPELINE_STEPS
                        : liveJob?.mode === 'educational'
                          ? EDUCATIONAL_PIPELINE_STEPS.filter(
                              s => s.key !== 'sora_intro' || educationalPayload?.sora_intro)
                          : undefined
                    }
                  />
                </div>
              )}

              <div className="flex justify-center">
                <button onClick={() => navigate('/')} className="btn-secondary text-sm">
                  Cancel
                </button>
              </div>
            </div>
          </motion.div>
        )}

        {/* DONE STEP */}
        {step === doneStep && liveJob && (
          <motion.div
            key="done"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          >
            <div className="glass-card p-10 text-center">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.1, type: 'spring', stiffness: 400, damping: 20 }}
                className="w-20 h-20 rounded-full bg-emerald-400/20 border-2 border-emerald-400 flex items-center justify-center mx-auto mb-6"
              >
                <CheckCircle2 className="w-10 h-10 text-emerald-400" />
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25 }}
              >
                <h2 className="text-2xl font-bold text-white mb-2">Video is ready!</h2>
                <p className="text-slate-400 text-sm mb-8">
                  Your AI-generated video has been processed and is ready for review.
                </p>

                <div className="flex gap-3 justify-center">
                  <button onClick={() => navigate('/')} className="btn-secondary text-sm">
                    Back to Dashboard
                  </button>
                  <motion.button
                    whileHover={{ scale: 1.03 }}
                    whileTap={{ scale: 0.97 }}
                    onClick={() => navigate(`/review/${liveJob.id}`)}
                    className="btn-primary flex items-center gap-2"
                  >
                    Review Video
                    <ArrowRight className="w-4 h-4" />
                  </motion.button>
                </div>
              </motion.div>
            </div>
          </motion.div>
        )}

      </AnimatePresence>
    </div>
  )
}
