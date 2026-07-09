import { motion } from 'framer-motion'
import { Clock, FileText, Rss } from 'lucide-react'
import { cn, formatRelativeTime } from '../lib/utils'
import type { FeedConfiguration } from '../types'

interface FeedStatusCardProps {
  feed: FeedConfiguration
  onClick?: () => void
  delay?: number
}

const healthColors = {
  active: { dot: 'bg-emerald-400', label: 'text-emerald-400', bg: 'bg-emerald-400/10' },
  degraded: { dot: 'bg-yellow-400', label: 'text-yellow-400', bg: 'bg-yellow-400/10' },
  error: { dot: 'bg-red-400', label: 'text-red-400', bg: 'bg-red-400/10' },
}

export default function FeedStatusCard({ feed, onClick, delay = 0 }: FeedStatusCardProps) {
  const colors = healthColors[feed.health_status]

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.3 }}
      onClick={onClick}
      className={cn(
        'glass-card p-5 cursor-pointer hover:border-white/15 transition-all group',
        onClick && 'hover:scale-[1.01]'
      )}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-azure-600/10 flex items-center justify-center">
            <Rss className="w-4 h-4 text-azure-400" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white truncate max-w-[180px]">
              {feed.display_name}
            </h4>
            <span className={cn('text-xs font-medium capitalize', colors.label)}>
              {feed.health_status}
            </span>
          </div>
        </div>
        <div className={cn('w-2.5 h-2.5 rounded-full', colors.dot, feed.health_status === 'active' && 'animate-pulse')} />
      </div>

      <div className="flex items-center gap-4 text-xs text-slate-400">
        <div className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5" />
          <span>{feed.last_polled_at ? formatRelativeTime(feed.last_polled_at) : 'Never polled'}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <FileText className="w-3.5 h-3.5" />
          <span>{feed.articles_processed} articles</span>
        </div>
      </div>
    </motion.div>
  )
}
