import { useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { Eye, Download, Trash2, ExternalLink, Search, SlidersHorizontal } from 'lucide-react'
import Badge from '../components/Badge'
import EmptyState from '../components/EmptyState'
import ConfirmDialog from '../components/ConfirmDialog'
import LoadingSpinner from '../components/LoadingSpinner'
import { useJobStore } from '../stores/jobStore'
import { useJobs } from '../hooks/useJobs'
import { deleteJob, getVideoUrl } from '../lib/api'
import { truncateUrl, formatRelativeTime, languageLabel, formatLabel } from '../lib/utils'
import { cn } from '../lib/utils'

type FilterTab = 'all' | 'awaiting_review' | 'approved' | 'failed'

const TABS: { id: FilterTab; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'awaiting_review', label: 'Awaiting Review' },
  { id: 'approved', label: 'Approved' },
  { id: 'failed', label: 'Failed' },
]

export default function History() {
  const navigate = useNavigate()
  const { jobs, isLoading, removeJob } = useJobStore()
  useJobs()

  const [activeTab, setActiveTab] = useState<FilterTab>('all')
  const [search, setSearch] = useState('')
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)

  const filtered = jobs.filter((job) => {
    if (activeTab !== 'all' && job.status !== activeTab) return false
    if (search && !job.article_url.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const handleDownload = (videoPath: string, id: string) => {
    const a = document.createElement('a')
    a.href = getVideoUrl(videoPath)
    a.download = `vernacularcast-${id}.mp4`
    a.click()
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await deleteJob(deleteTarget)
      removeJob(deleteTarget)
    } catch { /* silent */ }
    setDeleteTarget(null)
  }

  const tabCount = (tab: FilterTab) => {
    if (tab === 'all') return jobs.length
    return jobs.filter((j) => j.status === tab).length
  }

  return (
    <div className="page-container">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        {/* Filters row */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          {/* Filter tabs */}
          <div className="flex gap-1 bg-navy-900/60 border border-white/5 rounded-xl p-1">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 flex items-center gap-1.5',
                  activeTab === tab.id
                    ? 'bg-azure-600/20 text-azure-300 border border-azure-500/30'
                    : 'text-slate-500 hover:text-white'
                )}
              >
                {tab.label}
                <span className={cn(
                  'text-[10px] px-1.5 py-0.5 rounded-full font-bold',
                  activeTab === tab.id ? 'bg-azure-500/20 text-azure-400' : 'bg-navy-800 text-slate-600'
                )}>
                  {tabCount(tab.id)}
                </span>
              </button>
            ))}
          </div>

          {/* Search */}
          <div className="relative flex-1 max-w-xs ml-auto">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search by URL…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input-field pl-9 h-9 text-sm"
            />
          </div>

          <button className="btn-secondary flex items-center gap-2 text-sm py-2">
            <SlidersHorizontal className="w-4 h-4" />
            Filter
          </button>
        </div>

        {/* Table */}
        {isLoading ? (
          <div className="flex justify-center py-20">
            <LoadingSpinner size="lg" />
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            title={activeTab === 'all' ? 'No videos yet' : `No ${activeTab.replace('_', ' ')} videos`}
            description={activeTab === 'all' ? 'Create your first AI video by pasting a news article URL.' : 'No videos match this filter.'}
            showCTA={activeTab === 'all'}
          />
        ) : (
          <div className="glass-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/5">
                    <th className="text-left px-5 py-3.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">Article</th>
                    <th className="text-left px-4 py-3.5 text-xs font-semibold text-slate-400 uppercase tracking-wider hidden sm:table-cell">Language</th>
                    <th className="text-left px-4 py-3.5 text-xs font-semibold text-slate-400 uppercase tracking-wider hidden md:table-cell">Format</th>
                    <th className="text-left px-4 py-3.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">Status</th>
                    <th className="text-left px-4 py-3.5 text-xs font-semibold text-slate-400 uppercase tracking-wider hidden lg:table-cell">Created</th>
                    <th className="text-right px-5 py-3.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {filtered.map((job, i) => (
                    <motion.tr
                      key={job.id}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.03 }}
                      className="hover:bg-white/[0.02] transition-colors group"
                    >
                      {/* Thumbnail + URL */}
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-7 rounded-md bg-navy-900/80 border border-white/10 flex items-center justify-center flex-shrink-0 text-sm">
                            {job.status === 'approved' ? '✅' : job.status === 'failed' ? '❌' : '🎬'}
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm text-slate-200 font-medium truncate max-w-[200px]" title={job.article_url}>
                              {truncateUrl(job.article_url, 40)}
                            </p>
                          </div>
                        </div>
                      </td>

                      {/* Language */}
                      <td className="px-4 py-4 hidden sm:table-cell">
                        <span className="text-xs text-slate-400">{languageLabel(job.language)}</span>
                      </td>

                      {/* Format */}
                      <td className="px-4 py-4 hidden md:table-cell">
                        <span className="text-xs text-slate-400">{formatLabel(job.format)}</span>
                      </td>

                      {/* Status */}
                      <td className="px-4 py-4">
                        <Badge status={job.status} />
                      </td>

                      {/* Created */}
                      <td className="px-4 py-4 hidden lg:table-cell">
                        <span className="text-xs text-slate-500">{formatRelativeTime(job.created_at)}</span>
                      </td>

                      {/* Actions */}
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-2 justify-end">
                          {(job.status === 'awaiting_review' || job.status === 'ready') && (
                            <button
                              onClick={() => navigate(`/review/${job.id}`)}
                              title="Review"
                              className="w-7 h-7 rounded-lg bg-azure-600/10 border border-azure-500/20 flex items-center justify-center text-azure-400 hover:bg-azure-600/20 transition-colors"
                            >
                              <Eye className="w-3.5 h-3.5" />
                            </button>
                          )}
                          {job.status === 'approved' && job.video_path && (
                            <button
                              onClick={() => handleDownload(job.video_path!, job.id)}
                              title="Download"
                              className="w-7 h-7 rounded-lg bg-emerald-400/10 border border-emerald-400/20 flex items-center justify-center text-emerald-400 hover:bg-emerald-400/20 transition-colors"
                            >
                              <Download className="w-3.5 h-3.5" />
                            </button>
                          )}
                          <a
                            href={job.article_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            title="Open source"
                            className="w-7 h-7 rounded-lg bg-navy-800/80 border border-white/10 flex items-center justify-center text-slate-400 hover:text-white transition-colors"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                          <button
                            onClick={() => setDeleteTarget(job.id)}
                            title="Delete"
                            className="w-7 h-7 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400/60 hover:text-red-400 hover:bg-red-500/20 transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Table footer */}
            <div className="px-5 py-3 border-t border-white/5 flex items-center justify-between">
              <p className="text-xs text-slate-500">
                Showing {filtered.length} of {jobs.length} videos
              </p>
            </div>
          </div>
        )}
      </motion.div>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete Video"
        message="This will permanently delete the video and all associated files. This action cannot be undone."
        confirmLabel="Delete"
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}
