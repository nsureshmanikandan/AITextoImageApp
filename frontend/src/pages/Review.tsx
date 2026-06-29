import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  CheckCircle2, RefreshCw, Trash2, ExternalLink,
  FileText, Clock, Languages, Maximize2
} from 'lucide-react'
import VideoPlayer from '../components/VideoPlayer'
import Badge from '../components/Badge'
import ConfirmDialog from '../components/ConfirmDialog'
import LoadingSpinner from '../components/LoadingSpinner'
import { useJobStore } from '../stores/jobStore'
import { useJobProgress } from '../hooks/useJobProgress'
import { getJob, approveJob, rejectJob, deleteJob, getVideoUrl } from '../lib/api'
import { languageLabel, formatLabel, formatDate } from '../lib/utils'

export default function Review() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { updateJob, removeJob } = useJobStore()

  const job = useJobStore((s) => s.jobs.find((j) => String(j.id) === id))
  const [loading, setLoading] = useState(!job)
  const [error, setError] = useState('')
  const [approving, setApproving] = useState(false)
  const [showApproveConfirm, setShowApproveConfirm] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [showRejectConfirm, setShowRejectConfirm] = useState(false)
  const [approved, setApproved] = useState(false)

  // Live WS updates
  useJobProgress(id ?? null)

  useEffect(() => {
    if (!id) return
    if (!job) {
      setLoading(true)
      getJob(id)
        .then((j) => { updateJob(j) })
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false))
    }
  }, [id]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleApprove = async () => {
    if (!id) return
    setApproving(true)
    try {
      const updated = await approveJob(id)
      updateJob(updated)
      setApproved(true)
      setTimeout(() => navigate('/history'), 1800)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Approval failed')
    } finally {
      setApproving(false)
      setShowApproveConfirm(false)
    }
  }

  const handleReject = async () => {
    if (!id) return
    try {
      const updated = await rejectJob(id)
      updateJob(updated)
      navigate('/create')
    } catch {
      navigate('/create')
    }
    setShowRejectConfirm(false)
  }

  const handleDelete = async () => {
    if (!id) return
    try {
      await deleteJob(id)
      removeJob(id)
    } catch { /* silent */ }
    navigate('/history')
    setShowDeleteConfirm(false)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error || !job) {
    return (
      <div className="page-container text-center py-24">
        <p className="text-red-400 mb-4">{error || 'Video not found'}</p>
        <button onClick={() => navigate('/')} className="btn-secondary">Back to Dashboard</button>
      </div>
    )
  }

  const videoSrc = job.video_path ? getVideoUrl(job.video_path) : ''
  const isYouTube = /youtube\.com|youtu\.be/i.test(job.article_url ?? '')
  // YouTube dubs are always landscape regardless of format selected
  const playerFormat = isYouTube ? 'landscape_16_9' : job.format

  return (
    <div className="page-container">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="grid grid-cols-1 lg:grid-cols-5 gap-6"
      >
        {/* Video Player (60%) */}
        <div className="lg:col-span-3">
          <div className="glass-card overflow-hidden">
            {videoSrc ? (
              <VideoPlayer
                src={videoSrc}
                format={playerFormat}
                className={playerFormat === 'vertical_9_16' ? '' : 'w-full aspect-video'}
              />
            ) : (
              <div className="w-full aspect-video bg-navy-900/60 flex items-center justify-center">
                {job.status === 'awaiting_review' ? (
                  <div className="text-center">
                    <div className="w-12 h-12 border-2 border-azure-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                    <p className="text-slate-400 text-sm">Video processing…</p>
                  </div>
                ) : (
                  <p className="text-slate-500 text-sm">No video available</p>
                )}
              </div>
            )}
          </div>

          {/* Meta strip */}
          <div className="flex items-center gap-3 mt-3 flex-wrap">
            <Badge status={job.status} />
            <span className="text-xs text-slate-500 bg-navy-800/60 border border-white/10 px-2.5 py-1 rounded-md">
              <Languages className="w-3 h-3 inline mr-1" />{languageLabel(job.language)}
            </span>
            <span className="text-xs text-slate-500 bg-navy-800/60 border border-white/10 px-2.5 py-1 rounded-md">
              <Maximize2 className="w-3 h-3 inline mr-1" />{formatLabel(job.format)}
            </span>
            <span className="text-xs text-slate-500 bg-navy-800/60 border border-white/10 px-2.5 py-1 rounded-md">
              <Clock className="w-3 h-3 inline mr-1" />{formatDate(job.created_at)}
            </span>
          </div>
        </div>

        {/* Right panel (40%) */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          {/* Script */}
          <div className="glass-card p-5 flex-1 flex flex-col">
            <div className="flex items-center gap-2 mb-4">
              <FileText className="w-4 h-4 text-azure-400" />
              <h3 className="text-sm font-semibold text-white">Generated Script</h3>
            </div>

            <div className="flex-1 overflow-y-auto max-h-64 lg:max-h-none">
              {job.script ? (
                <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
                  {job.script.replace(/\*{1,2}([^*]+)\*{1,2}/g, '$1')}
                </p>
              ) : (
                <p className="text-sm text-slate-500 italic">Script will appear here once generated.</p>
              )}
            </div>

            <div className="mt-4 pt-4 border-t border-white/5">
              <p className="text-xs text-slate-500 mb-1">Source article</p>
              <a
                href={job.article_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-azure-400 hover:text-azure-300 flex items-center gap-1 truncate"
              >
                <ExternalLink className="w-3 h-3 flex-shrink-0" />
                <span className="truncate">{job.article_url}</span>
              </a>
            </div>
          </div>

          {/* Quality Scores — shown for all YouTube dub jobs */}
          {isYouTube && (
            <div className="glass-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <span className="text-azure-400 text-base">⚡</span>
                <h3 className="text-sm font-semibold text-white">Dub Quality Score</h3>
              </div>
              <div className="space-y-4">

                {/* Timing Match */}
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400">Timing Match</span>
                    <span className={
                      job.timing_score == null ? 'text-slate-500' :
                      job.timing_score >= 90 ? 'text-emerald-400' :
                      job.timing_score >= 70 ? 'text-yellow-400' : 'text-red-400'
                    }>
                      {job.timing_score != null ? `${job.timing_score}%` : 'Not scored'}
                    </span>
                  </div>
                  <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full transition-all ${
                      job.timing_score == null ? 'bg-slate-700' :
                      job.timing_score >= 90 ? 'bg-emerald-500' :
                      job.timing_score >= 70 ? 'bg-yellow-500' : 'bg-red-500'
                    }`} style={{ width: `${job.timing_score ?? 0}%` }} />
                  </div>
                  <p className="text-xs text-slate-600 mt-1">How well dubbed audio length matches original video</p>
                </div>

                {/* Translation Quality */}
                {(() => {
                  const noTranscript = (() => { try { return JSON.parse(job.quality_details ?? '{}')?.translation?.no_transcript } catch { return false } })()
                  const score = job.translation_score
                  return (
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-slate-400">{noTranscript ? 'Script Quality' : 'Translation Quality'}</span>
                        <span className={
                          score == null ? 'text-slate-500' :
                          score === 0 ? 'text-slate-500' :
                          score >= 80 ? 'text-emerald-400' :
                          score >= 60 ? 'text-yellow-400' : 'text-red-400'
                        }>
                          {score != null && score > 0 ? `${score}%` : 'Not scored'}
                        </span>
                      </div>
                      <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full transition-all ${
                          score == null || score === 0 ? 'bg-slate-700' :
                          score >= 80 ? 'bg-emerald-500' :
                          score >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                        }`} style={{ width: `${score && score > 0 ? score : 0}%` }} />
                      </div>
                      <p className="text-xs text-slate-600 mt-1">
                        {noTranscript
                          ? 'No subtitles found — GPT-4o rated script fluency directly'
                          : 'GPT-4o rates accuracy vs original English transcript'}
                      </p>
                    </div>
                  )
                })()}

                {/* Duration details */}
                {job.quality_details && (() => {
                  try {
                    const d = JSON.parse(job.quality_details!)
                    const t = d.timing
                    return t ? (
                      <div className="flex gap-4 pt-1 text-xs text-slate-500 border-t border-white/5">
                        <span>Original: <b className="text-slate-300">{t.original_secs}s</b></span>
                        <span>Dubbed: <b className="text-slate-300">{t.dubbed_secs}s</b></span>
                        <span>Diff: <b className={Math.abs(t.diff_secs) <= 2 ? 'text-emerald-400' : 'text-yellow-400'}>Δ{t.diff_secs}s</b></span>
                      </div>
                    ) : null
                  } catch { return null }
                })()}

                {/* Original transcript */}
                {job.original_transcript ? (
                  <details className="pt-1">
                    <summary className="text-xs text-slate-400 cursor-pointer hover:text-slate-200 select-none font-medium">
                      📄 Original English Transcript
                    </summary>
                    <p className="text-xs text-slate-400 mt-2 leading-relaxed max-h-32 overflow-y-auto whitespace-pre-wrap border border-white/5 rounded-lg p-2 bg-white/5">
                      {job.original_transcript}
                    </p>
                  </details>
                ) : (
                  <p className="text-xs text-slate-600 italic pt-1">No transcript available for this job. New jobs will show transcript here.</p>
                )}
              </div>
            </div>
          )}

          {/* Actions */}
          {!approved ? (
            <div className="glass-card p-5">
              <h3 className="text-sm font-semibold text-white mb-4">Actions</h3>
              <div className="flex flex-col gap-3">
                <motion.button
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  onClick={() => setShowApproveConfirm(true)}
                  disabled={approving || job.status === 'approved'}
                  className="btn-success flex items-center justify-center gap-2 w-full"
                >
                  {approving ? (
                    <LoadingSpinner size="sm" />
                  ) : (
                    <CheckCircle2 className="w-4 h-4" />
                  )}
                  {job.status === 'approved' ? 'Already Approved' : 'Approve & Download'}
                </motion.button>

                <button
                  onClick={() => setShowRejectConfirm(true)}
                  className="btn-secondary flex items-center justify-center gap-2 w-full text-sm"
                >
                  <RefreshCw className="w-4 h-4" />
                  Regenerate
                </button>

                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  className="btn-danger flex items-center justify-center gap-2 w-full text-sm"
                >
                  <Trash2 className="w-4 h-4" />
                  Discard
                </button>
              </div>
            </div>
          ) : (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="glass-card p-5 border-emerald-400/20 text-center"
            >
              <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
              <p className="text-white font-semibold">Approved!</p>
              <p className="text-slate-400 text-xs mt-1">Redirecting to history…</p>
            </motion.div>
          )}
        </div>
      </motion.div>

      <ConfirmDialog
        open={showApproveConfirm}
        title="Approve Video"
        message="This will mark the video as approved and make it available for download. Continue?"
        confirmLabel="Approve"
        variant="default"
        onConfirm={handleApprove}
        onCancel={() => setShowApproveConfirm(false)}
      />

      <ConfirmDialog
        open={showRejectConfirm}
        title="Regenerate Video"
        message="This will send you back to create a new video from the same article. The current video will be discarded."
        confirmLabel="Regenerate"
        variant="warning"
        onConfirm={handleReject}
        onCancel={() => setShowRejectConfirm(false)}
      />

      <ConfirmDialog
        open={showDeleteConfirm}
        title="Discard Video"
        message="This will permanently delete the video. This cannot be undone."
        confirmLabel="Discard"
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setShowDeleteConfirm(false)}
      />
    </div>
  )
}
