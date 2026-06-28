import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { Video, CheckCircle2, Clock, Globe2, Plus, ArrowRight } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import StatCard from '../components/StatCard'
import JobCard from '../components/JobCard'
import EmptyState from '../components/EmptyState'
import ConfirmDialog from '../components/ConfirmDialog'
import LoadingSpinner from '../components/LoadingSpinner'
import { useJobStore } from '../stores/jobStore'
import { useJobs } from '../hooks/useJobs'
import { getDashboardStats, deleteJob } from '../lib/api'
import type { DashboardStats } from '../types'

const MOCK_STATS: DashboardStats = {
  total_videos: 24,
  approved: 18,
  pending_review: 3,
  languages_used: 4,
  recent_jobs: [],
  weekly_trend: [
    { day: 'Mon', count: 2 },
    { day: 'Tue', count: 4 },
    { day: 'Wed', count: 3 },
    { day: 'Thu', count: 6 },
    { day: 'Fri', count: 5 },
    { day: 'Sat', count: 2 },
    { day: 'Sun', count: 7 },
  ],
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { jobs, isLoading, removeJob } = useJobStore()
  useJobs()
  const [stats, setStats] = useState<DashboardStats>(MOCK_STATS)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)

  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .catch(() => {
        // Use counts derived from actual jobs if API unavailable
        setStats((prev) => ({
          ...prev,
          total_videos: jobs.length,
          approved: jobs.filter((j) => j.status === 'approved').length,
          pending_review: jobs.filter((j) => j.status === 'awaiting_review').length,
          languages_used: new Set(jobs.map((j) => j.language)).size || prev.languages_used,
        }))
      })
  }, [jobs.length]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await deleteJob(deleteTarget)
      removeJob(deleteTarget)
    } catch {
      // silent for demo
    }
    setDeleteTarget(null)
  }

  const recentJobs = jobs.slice(0, 6)

  return (
    <div className="page-container">
      {/* Hero CTA */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex items-center justify-between mb-8"
      >
        <div>
          <h2 className="text-2xl font-bold text-white mb-1">
            Good morning, <span className="text-gradient-azure">Newsroom</span>
          </h2>
          <p className="text-slate-400 text-sm">Here's your AI video production at a glance.</p>
        </div>
        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => navigate('/create')}
          className="btn-primary flex items-center gap-2 text-sm"
        >
          <Plus className="w-4 h-4" />
          Create New Video
        </motion.button>
      </motion.div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Videos" value={stats.total_videos} icon={Video} color="azure" trend={12} delay={0.05} />
        <StatCard label="Approved" value={stats.approved} icon={CheckCircle2} color="emerald" trend={8} delay={0.1} />
        <StatCard label="Pending Review" value={stats.pending_review} icon={Clock} color="gold" delay={0.15} />
        <StatCard label="Languages Used" value={stats.languages_used} icon={Globe2} color="teal" delay={0.2} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Activity chart */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="glass-card p-6 lg:col-span-2"
        >
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-sm font-semibold text-white">Weekly Production</h3>
              <p className="text-xs text-slate-500 mt-0.5">Videos generated per day</p>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={160}>
            <AreaChart data={stats.weekly_trend} margin={{ top: 4, right: 4, left: -30, bottom: 0 }}>
              <defs>
                <linearGradient id="azureGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0086F0" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#0086F0" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="day" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: '#0F2040', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#fff', fontSize: 12 }}
                cursor={{ stroke: '#0086F0', strokeWidth: 1, strokeDasharray: '4 4' }}
              />
              <Area type="monotone" dataKey="count" stroke="#0086F0" strokeWidth={2} fill="url(#azureGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="glass-card p-6"
        >
          <h3 className="text-sm font-semibold text-white mb-4">Quick Actions</h3>
          <div className="flex flex-col gap-2">
            {[
              { label: 'New Tamil video', sub: 'Tamil · 9:16', emoji: '🎬', onClick: () => navigate('/create') },
              { label: 'New Hindi video', sub: 'Hindi · 16:9', emoji: '📺', onClick: () => navigate('/create') },
              { label: 'View all pending', sub: `${stats.pending_review} awaiting`, emoji: '⏳', onClick: () => navigate('/history') },
            ].map((action, i) => (
              <button
                key={i}
                onClick={action.onClick}
                className="flex items-center gap-3 p-3 rounded-xl bg-navy-900/60 border border-white/5 hover:border-white/15 hover:bg-navy-800/80 transition-all text-left group"
              >
                <span className="text-xl">{action.emoji}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-white truncate">{action.label}</div>
                  <div className="text-xs text-slate-500">{action.sub}</div>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-azure-400 transition-colors" />
              </button>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Recent Jobs */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35 }}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white">Recent Videos</h3>
          <button
            onClick={() => navigate('/history')}
            className="text-xs text-azure-400 hover:text-azure-300 transition-colors flex items-center gap-1"
          >
            View all <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-16">
            <LoadingSpinner size="lg" />
          </div>
        ) : recentJobs.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {recentJobs.map((job, i) => (
              <JobCard key={job.id} job={job} onDelete={setDeleteTarget} delay={i * 0.05} />
            ))}
          </div>
        )}
      </motion.div>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete Video"
        message="This will permanently delete the video and all associated files. This action cannot be undone."
        confirmLabel="Delete"
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}
