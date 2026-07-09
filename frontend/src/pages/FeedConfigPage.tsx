import { AnimatePresence, motion } from 'framer-motion'
import { Pencil, Plus, Power, PowerOff, Rss, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import ConfirmDialog from '../components/ConfirmDialog'
import type { FeedFormData } from '../components/FeedForm'
import FeedForm from '../components/FeedForm'
import LoadingSpinner from '../components/LoadingSpinner'
import { createFeed, deleteFeed, listFeeds, updateFeed, validateFeedUrl } from '../lib/api'
import { cn, formatRelativeTime, languageLabel } from '../lib/utils'
import { useLiveNewsStore } from '../stores/liveNewsStore'
import type { FeedConfiguration } from '../types'

const healthColors = {
  active: 'bg-emerald-400',
  degraded: 'bg-yellow-400',
  error: 'bg-red-400',
}

export default function FeedConfigPage() {
  const { feeds, setFeeds } = useLiveNewsStore()
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editFeed, setEditFeed] = useState<FeedConfiguration | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)
  const [validating, setValidating] = useState(false)

  useEffect(() => {
    listFeeds()
      .then(setFeeds)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleCreate = async (data: FeedFormData) => {
    try {
      const newFeed = await createFeed(data)
      setFeeds([...feeds, newFeed])
      setShowForm(false)
    } catch {
      // silent
    }
  }

  const handleUpdate = async (data: FeedFormData) => {
    if (!editFeed) return
    try {
      const updated = await updateFeed(editFeed.id, data)
      setFeeds(feeds.map((f) => (f.id === editFeed.id ? updated : f)))
      setEditFeed(null)
    } catch {
      // silent
    }
  }

  const handleDelete = async () => {
    if (deleteTarget === null) return
    try {
      await deleteFeed(deleteTarget)
      setFeeds(feeds.filter((f) => f.id !== deleteTarget))
    } catch {
      // silent
    }
    setDeleteTarget(null)
  }

  const handleToggleEnabled = async (feed: FeedConfiguration) => {
    try {
      const updated = await updateFeed(feed.id, { enabled: !feed.enabled })
      setFeeds(feeds.map((f) => (f.id === feed.id ? updated : f)))
    } catch {
      // silent
    }
  }

  const handleValidateUrl = async () => {
    if (!editFeed) return
    setValidating(true)
    try {
      await validateFeedUrl(editFeed.id)
    } catch {
      // silent
    }
    setValidating(false)
  }

  return (
    <div className="page-container">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex items-center justify-between mb-8"
      >
        <div>
          <h2 className="text-2xl font-bold text-white mb-1">
            Feed <span className="text-gradient-azure">Configuration</span>
          </h2>
          <p className="text-slate-400 text-sm">Manage RSS feed sources for automated monitoring.</p>
        </div>
        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => setShowForm(true)}
          className="btn-primary flex items-center gap-2 text-sm"
        >
          <Plus className="w-4 h-4" />
          Add Feed
        </motion.button>
      </motion.div>

      {/* Feed List */}
      {loading ? (
        <div className="flex justify-center py-16">
          <LoadingSpinner size="lg" />
        </div>
      ) : feeds.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="glass-card p-12 text-center"
        >
          <Rss className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <p className="text-slate-400 text-sm">No feeds configured.</p>
          <p className="text-slate-500 text-xs mt-1">Click "Add Feed" to get started.</p>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {feeds.map((feed, i) => (
            <motion.div
              key={feed.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="glass-card p-5"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2.5">
                  <div className={cn('w-2.5 h-2.5 rounded-full', healthColors[feed.health_status])} />
                  <h4 className="text-sm font-semibold text-white truncate max-w-[180px]">
                    {feed.display_name}
                  </h4>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleToggleEnabled(feed)}
                    className={cn(
                      'p-1.5 rounded-lg transition-colors',
                      feed.enabled ? 'text-emerald-400 hover:bg-emerald-400/10' : 'text-slate-500 hover:bg-slate-500/10'
                    )}
                    title={feed.enabled ? 'Disable feed' : 'Enable feed'}
                  >
                    {feed.enabled ? <Power className="w-3.5 h-3.5" /> : <PowerOff className="w-3.5 h-3.5" />}
                  </button>
                  <button
                    onClick={() => setEditFeed(feed)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => setDeleteTarget(feed.id)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <p className="text-xs text-slate-500 truncate mb-3">{feed.feed_url}</p>

              <div className="flex flex-wrap gap-2 text-xs text-slate-400">
                <span className="px-2 py-0.5 rounded bg-navy-900/60 border border-white/5">
                  {languageLabel(feed.language)}
                </span>
                <span className="px-2 py-0.5 rounded bg-navy-900/60 border border-white/5 capitalize">
                  {feed.trust_level}
                </span>
                <span className="px-2 py-0.5 rounded bg-navy-900/60 border border-white/5">
                  {feed.polling_interval_seconds}s
                </span>
                {feed.auto_approve && (
                  <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Auto-approve
                  </span>
                )}
              </div>

              {feed.last_polled_at && (
                <p className="text-xs text-slate-500 mt-3">
                  Last polled: {formatRelativeTime(feed.last_polled_at)}
                </p>
              )}
            </motion.div>
          ))}
        </div>
      )}

      {/* Form Modal */}
      <AnimatePresence>
        {(showForm || editFeed) && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
            onClick={() => { setShowForm(false); setEditFeed(null) }}
          >
            <div onClick={(e) => e.stopPropagation()}>
              <FeedForm
                mode={editFeed ? 'edit' : 'create'}
                initialData={editFeed ? {
                  feed_url: editFeed.feed_url,
                  display_name: editFeed.display_name,
                  polling_interval_seconds: editFeed.polling_interval_seconds,
                  language: editFeed.language,
                  priority_keywords: editFeed.priority_keywords,
                  trust_level: editFeed.trust_level,
                  auto_approve: editFeed.auto_approve,
                  enabled: editFeed.enabled,
                } : undefined}
                onSubmit={editFeed ? handleUpdate : handleCreate}
                onCancel={() => { setShowForm(false); setEditFeed(null) }}
                onValidateUrl={editFeed ? handleValidateUrl : undefined}
                validating={validating}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={deleteTarget !== null}
        title="Delete Feed"
        message="This will stop monitoring this feed. Historical article data will be retained. Are you sure?"
        confirmLabel="Delete"
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}
