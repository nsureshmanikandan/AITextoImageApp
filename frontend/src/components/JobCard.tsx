import { motion } from 'framer-motion'
import { Eye, Download, Trash2, RefreshCw, ExternalLink } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import Badge from './Badge'
import type { Job } from '../types'
import { truncateUrl, formatRelativeTime, languageLabel, formatLabel } from '../lib/utils'
import { getVideoUrl } from '../lib/api'

interface JobCardProps {
  job: Job
  onDelete?: (id: string) => void
  delay?: number
}

export default function JobCard({ job, onDelete, delay = 0 }: JobCardProps) {
  const navigate = useNavigate()

  const handleDownload = () => {
    if (job.video_path) {
      const a = document.createElement('a')
      a.href = getVideoUrl(job.video_path)
      a.download = `vernacularcast-${job.id}.mp4`
      a.click()
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.35, ease: 'easeOut' }}
      className="glass-card p-5 hover:border-white/20 transition-all duration-300 group"
    >
      {/* Thumbnail placeholder */}
      <div className="w-full aspect-video bg-navy-900/60 rounded-xl mb-4 flex items-center justify-center relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-navy-700/30 to-navy-950/60" />
        {job.status === 'approved' || job.status === 'awaiting_review' || job.status === 'ready' ? (
          <div className="relative text-4xl">🎬</div>
        ) : job.status === 'failed' ? (
          <div className="relative text-4xl">❌</div>
        ) : (
          <div className="relative flex flex-col items-center gap-2">
            <div className="w-8 h-8 border-2 border-azure-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-xs text-slate-500">Processing…</span>
          </div>
        )}
        <div className="absolute top-2 right-2">
          <Badge status={job.status} />
        </div>
      </div>

      {/* Info */}
      <div className="mb-4">
        <p className="text-sm text-slate-300 font-medium mb-1 truncate" title={job.article_url}>
          {truncateUrl(job.article_url)}
        </p>
        <div className="flex items-center gap-2 flex-wrap mt-2">
          <span className="text-xs bg-navy-700/60 border border-white/10 px-2 py-0.5 rounded-md text-slate-400">
            {languageLabel(job.language)}
          </span>
          <span className="text-xs bg-navy-700/60 border border-white/10 px-2 py-0.5 rounded-md text-slate-400">
            {formatLabel(job.format)}
          </span>
          <span className="text-xs text-slate-500 ml-auto">{formatRelativeTime(job.created_at)}</span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 pt-3 border-t border-white/5">
        {(job.status === 'awaiting_review' || job.status === 'ready') && (
          <button
            className="flex items-center gap-1.5 text-xs font-medium text-azure-400 hover:text-azure-300 transition-colors"
            onClick={() => navigate(`/review/${job.id}`)}
          >
            <Eye className="w-3.5 h-3.5" />
            Review
          </button>
        )}
        {job.status === 'approved' && job.video_path && (
          <button
            className="flex items-center gap-1.5 text-xs font-medium text-emerald-400 hover:text-emerald-300 transition-colors"
            onClick={handleDownload}
          >
            <Download className="w-3.5 h-3.5" />
            Download
          </button>
        )}
        <a
          href={job.article_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-300 transition-colors"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          Source
        </a>
        {job.status === 'failed' && (
          <button
            className="flex items-center gap-1.5 text-xs font-medium text-gold-400 hover:text-gold-300 transition-colors"
            onClick={() => navigate('/create')}
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Retry
          </button>
        )}
        {onDelete && (
          <button
            className="flex items-center gap-1.5 text-xs font-medium text-red-400/70 hover:text-red-400 transition-colors ml-auto"
            onClick={() => onDelete(job.id)}
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </motion.div>
  )
}
