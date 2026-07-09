import { motion } from 'framer-motion'
import { AlertCircle, Check, Clock, ExternalLink, Play, X } from 'lucide-react'
import { useState } from 'react'
import { getVideoUrl } from '../lib/api'
import { cn, formatRelativeTime, languageLabel } from '../lib/utils'
import type { QueueItem } from '../types'

interface QueueItemCardProps {
  item: QueueItem
  onApprove: (jobId: number) => void
  onReject: (jobId: number) => void
  delay?: number
}

export default function QueueItemCard({ item, onApprove, onReject, delay = 0 }: QueueItemCardProps) {
  const isHighPriority = item.priority === 'high'
  const isFailed = item.status === 'failed'
  const [showVideo, setShowVideo] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ delay, duration: 0.3 }}
      className={cn(
        'glass-card p-5',
        isFailed && 'border-red-500/20'
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            {/* Status badge */}
            {isFailed ? (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-red-500/15 text-red-400 border border-red-500/25">
                <AlertCircle className="w-3 h-3" />
                Failed
              </span>
            ) : (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Awaiting Review
              </span>
            )}
            {isHighPriority && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-amber-500/15 text-amber-400 border border-amber-500/25">
                High Priority
              </span>
            )}
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-azure-600/10 text-azure-400 border border-azure-500/20">
              {languageLabel(item.language)}
            </span>
          </div>

          <h4 className="text-sm font-semibold text-white mb-1 line-clamp-2">
            {item.article_title || item.article_url}
          </h4>

          <div className="flex items-center gap-3 text-xs text-slate-400">
            {item.feed_name && <span className="truncate max-w-[200px]">{item.feed_name}</span>}
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatRelativeTime(item.created_at)}
            </span>
          </div>

          {/* Error message for failed jobs */}
          {isFailed && item.error && (
            <div className="mt-3 p-3 rounded-lg bg-red-500/5 border border-red-500/15">
              <p className="text-xs text-red-400 font-medium mb-0.5">Error:</p>
              <p className="text-xs text-red-300/80 line-clamp-3 font-mono">{item.error}</p>
            </div>
          )}

          {/* Video preview for completed jobs */}
          {!isFailed && item.video_path && (
            <div className="mt-3">
              {showVideo ? (
                <video
                  src={getVideoUrl(item.video_path)}
                  controls
                  className="w-full max-w-md rounded-lg border border-white/10"
                  style={{ maxHeight: 200 }}
                />
              ) : (
                <button
                  onClick={() => setShowVideo(true)}
                  className="flex items-center gap-2 text-xs text-azure-400 hover:text-azure-300 transition-colors bg-azure-500/5 border border-azure-500/15 rounded-lg px-3 py-2"
                >
                  <Play className="w-3.5 h-3.5" />
                  Preview Video
                </button>
              )}
            </div>
          )}

          <a
            href={item.article_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-azure-400 hover:text-azure-300 mt-2 transition-colors"
          >
            <ExternalLink className="w-3 h-3" />
            View source article
          </a>
        </div>

        {/* Actions - only show for awaiting_review */}
        {!isFailed && (
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={() => onApprove(item.job_id)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors',
                'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20'
              )}
            >
              <Check className="w-3.5 h-3.5" />
              Approve
            </button>
            <button
              onClick={() => onReject(item.job_id)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors',
                'bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20'
              )}
            >
              <X className="w-3.5 h-3.5" />
              Reject
            </button>
          </div>
        )}
      </div>
    </motion.div>
  )
}
