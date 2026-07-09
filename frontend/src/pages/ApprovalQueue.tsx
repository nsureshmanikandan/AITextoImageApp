import { AnimatePresence, motion } from 'framer-motion'
import { AlertCircle, CheckCircle2, ClipboardList, MessageSquare, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import LoadingSpinner from '../components/LoadingSpinner'
import QueueItemCard from '../components/QueueItemCard'
import { approveQueueItem, getApprovalQueue, rejectQueueItem } from '../lib/api'
import { cn } from '../lib/utils'
import { useLiveNewsStore } from '../stores/liveNewsStore'

type FilterTab = 'all' | 'awaiting_review' | 'failed'

export default function ApprovalQueue() {
  const { queueItems, removeQueueItem, connectWebSocket, disconnectWebSocket } = useLiveNewsStore()
  const [loading, setLoading] = useState(true)
  const [rejectTarget, setRejectTarget] = useState<number | null>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [filter, setFilter] = useState<FilterTab>('all')

  useEffect(() => {
    getApprovalQueue()
      .then((data) => {
        const items = Array.isArray(data) ? data : (data as any)?.items ?? []
        useLiveNewsStore.setState({ queueItems: items })
      })
      .catch(() => {})
      .finally(() => setLoading(false))

    try { connectWebSocket() } catch {}
    return () => { try { disconnectWebSocket() } catch {} }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Filter and sort items
  const filteredItems = queueItems.filter((item) => {
    if (filter === 'all') return true
    return item.status === filter
  })

  const sortedItems = [...filteredItems].sort((a, b) => {
    // Failed items go after awaiting_review
    if (a.status !== b.status) {
      return a.status === 'awaiting_review' ? -1 : 1
    }
    if (a.priority !== b.priority) {
      return a.priority === 'high' ? -1 : 1
    }
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  })

  const pendingCount = queueItems.filter((i) => i.status === 'awaiting_review').length
  const failedCount = queueItems.filter((i) => i.status === 'failed').length

  const handleApprove = async (jobId: number) => {
    try {
      await approveQueueItem(jobId)
      removeQueueItem(jobId)
    } catch {
      // silent
    }
  }

  const handleRejectConfirm = async () => {
    if (!rejectTarget) return
    try {
      await rejectQueueItem(rejectTarget, rejectReason)
      removeQueueItem(rejectTarget)
    } catch {
      // silent
    }
    setRejectTarget(null)
    setRejectReason('')
  }

  return (
    <div className="page-container">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex items-center justify-between mb-6"
      >
        <div>
          <h2 className="text-2xl font-bold text-white mb-1">
            Approval <span className="text-gradient-azure">Queue</span>
          </h2>
          <p className="text-slate-400 text-sm">
            Review auto-generated videos. {pendingCount} pending, {failedCount} failed.
          </p>
        </div>
      </motion.div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 mb-6">
        <button
          onClick={() => setFilter('all')}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all border',
            filter === 'all'
              ? 'bg-azure-600/15 text-azure-300 border-azure-500/30'
              : 'bg-navy-900/60 text-slate-400 border-white/5 hover:border-white/15 hover:text-white'
          )}
        >
          All
          {queueItems.length > 0 && (
            <span className={cn('px-1.5 py-0.5 rounded-full text-[10px] font-bold', filter === 'all' ? 'bg-azure-500/20 text-azure-300' : 'bg-white/5 text-slate-500')}>
              {queueItems.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setFilter('awaiting_review')}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all border',
            filter === 'awaiting_review'
              ? 'bg-azure-600/15 text-azure-300 border-azure-500/30'
              : 'bg-navy-900/60 text-slate-400 border-white/5 hover:border-white/15 hover:text-white'
          )}
        >
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          Pending Review
          {pendingCount > 0 && (
            <span className={cn('px-1.5 py-0.5 rounded-full text-[10px] font-bold', filter === 'awaiting_review' ? 'bg-azure-500/20 text-azure-300' : 'bg-white/5 text-slate-500')}>
              {pendingCount}
            </span>
          )}
        </button>
        <button
          onClick={() => setFilter('failed')}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all border',
            filter === 'failed'
              ? 'bg-azure-600/15 text-azure-300 border-azure-500/30'
              : 'bg-navy-900/60 text-slate-400 border-white/5 hover:border-white/15 hover:text-white'
          )}
        >
          <AlertCircle className="w-3.5 h-3.5 text-red-400" />
          Failed
          {failedCount > 0 && (
            <span className={cn('px-1.5 py-0.5 rounded-full text-[10px] font-bold', filter === 'failed' ? 'bg-azure-500/20 text-azure-300' : 'bg-white/5 text-slate-500')}>
              {failedCount}
            </span>
          )}
        </button>
      </div>

      {/* Queue Items */}
      {loading ? (
        <div className="flex justify-center py-16">
          <LoadingSpinner size="lg" />
        </div>
      ) : sortedItems.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="glass-card p-12 text-center"
        >
          <ClipboardList className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <p className="text-slate-400 text-sm">No items in the approval queue.</p>
          <p className="text-slate-500 text-xs mt-1">Videos will appear here when feeds detect new articles.</p>
        </motion.div>
      ) : (
        <div className="flex flex-col gap-3">
          <AnimatePresence>
            {sortedItems.map((item, i) => (
              <QueueItemCard
                key={item.job_id}
                item={item}
                onApprove={handleApprove}
                onReject={(jobId) => setRejectTarget(jobId)}
                delay={i * 0.04}
              />
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Reject Modal */}
      <AnimatePresence>
        {rejectTarget !== null && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
            onClick={() => setRejectTarget(null)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="glass-card p-6 w-full max-w-md"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                  <MessageSquare className="w-5 h-5 text-red-400" />
                  Reject Video
                </h3>
                <button onClick={() => setRejectTarget(null)} className="text-slate-400 hover:text-white transition-colors">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <p className="text-sm text-slate-400 mb-4">Please provide a reason for rejection.</p>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Enter rejection reason..."
                rows={3}
                className="w-full px-3 py-2.5 rounded-lg bg-navy-900/60 border border-white/10 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-azure-500 resize-none mb-4"
              />
              <div className="flex justify-end gap-3">
                <button onClick={() => setRejectTarget(null)} className="btn-secondary text-sm px-4 py-2">
                  Cancel
                </button>
                <button
                  onClick={handleRejectConfirm}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-red-500/15 text-red-400 border border-red-500/25 hover:bg-red-500/25 transition-colors"
                >
                  Reject
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
