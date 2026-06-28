import { cn } from '../lib/utils'
import type { JobStatus } from '../types'
import { statusLabel } from '../lib/utils'

interface BadgeProps {
  status: JobStatus
  className?: string
}

const statusStyles: Record<JobStatus, string> = {
  pending: 'bg-slate-700/60 text-slate-400 border-slate-600/40',
  scraping: 'bg-azure-600/20 text-azure-400 border-azure-500/30',
  generating_script: 'bg-azure-600/20 text-azure-400 border-azure-500/30',
  generating_voice: 'bg-teal-400/20 text-teal-300 border-teal-400/30',
  rendering_video: 'bg-teal-400/20 text-teal-300 border-teal-400/30',
  awaiting_review: 'bg-gold-400/20 text-gold-300 border-gold-400/30',
  ready: 'bg-gold-400/20 text-gold-300 border-gold-400/30',
  approved: 'bg-emerald-400/20 text-emerald-400 border-emerald-400/30',
  failed: 'bg-red-500/20 text-red-400 border-red-500/30',
}

export default function Badge({ status, className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border',
        statusStyles[status],
        className
      )}
    >
      <span
        className={cn(
          'w-1.5 h-1.5 rounded-full',
          status === 'approved' && 'bg-emerald-400',
          status === 'failed' && 'bg-red-400',
          ['awaiting_review', 'ready'].includes(status) && 'bg-gold-400',
          ['scraping', 'generating_script', 'generating_voice', 'rendering_video'].includes(status) && 'bg-azure-400 animate-pulse',
          status === 'pending' && 'bg-slate-500'
        )}
      />
      {statusLabel(status)}
    </span>
  )
}
