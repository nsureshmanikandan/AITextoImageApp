import { motion } from 'framer-motion'
import { AlertTriangle, CheckCircle2, Clock, Cpu, FileText, Rss } from 'lucide-react'
import { useEffect, useState } from 'react'
import FeedStatusCard from '../components/FeedStatusCard'
import MonitorControls from '../components/MonitorControls'
import StatCard from '../components/StatCard'
import { getDashboardLiveNews, listFeeds } from '../lib/api'
import { useLiveNewsStore } from '../stores/liveNewsStore'

export default function LiveNewsDashboard() {
  const {
    dashboardStats,
    feeds,
    setDashboardStats,
    setFeeds,
    setMonitorState,
    connectWebSocket,
    disconnectWebSocket,
  } = useLiveNewsStore()
  const [, setLoaded] = useState(false)

  useEffect(() => {
    // Fetch initial data
    getDashboardLiveNews()
      .then((stats) => {
        if (stats) {
          setDashboardStats(stats)
          if (stats.monitor_state) setMonitorState(stats.monitor_state)
        }
      })
      .catch(() => {})
      .finally(() => setLoaded(true))

    listFeeds()
      .then((data) => { if (Array.isArray(data)) setFeeds(data) })
      .catch(() => {})

    // Connect WebSocket for real-time updates
    try {
      connectWebSocket()
    } catch {
      // WebSocket connection failed — non-fatal
    }

    return () => {
      try { disconnectWebSocket() } catch {}
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const stats = dashboardStats

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
            Live News <span className="text-gradient-azure">Monitor</span>
          </h2>
          <p className="text-slate-400 text-sm">Real-time RSS feed monitoring and auto-video generation.</p>
        </div>
      </motion.div>

      {/* Monitor Controls */}
      <div className="mb-6">
        <MonitorControls />
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
        <StatCard label="Active Feeds" value={stats?.total_active_feeds ?? 0} icon={Rss} color="azure" delay={0.05} />
        <StatCard label="Degraded" value={stats?.degraded_feeds ?? 0} icon={AlertTriangle} color="gold" delay={0.1} />
        <StatCard label="Articles / hr" value={stats?.articles_detected_last_hour ?? 0} icon={FileText} color="teal" delay={0.15} />
        <StatCard label="Awaiting Review" value={stats?.videos_awaiting_review ?? 0} icon={Clock} color="gold" delay={0.2} />
        <StatCard label="Auto-Approved / hr" value={stats?.videos_auto_approved_last_hour ?? 0} icon={CheckCircle2} color="emerald" delay={0.25} />
        <StatCard label="Active Jobs" value={stats?.active_processing_jobs ?? 0} icon={Cpu} color="azure" delay={0.3} />
      </div>

      {/* Feed Status List */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35 }}
      >
        <h3 className="text-sm font-semibold text-white mb-4">Feed Health</h3>
        {feeds.length === 0 ? (
          <div className="glass-card p-8 text-center">
            <Rss className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <p className="text-slate-400 text-sm">No feeds configured yet.</p>
            <p className="text-slate-500 text-xs mt-1">Add RSS feeds from the Feed Configuration page.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {feeds.map((feed, i) => (
              <FeedStatusCard key={feed.id} feed={feed} delay={i * 0.05} />
            ))}
          </div>
        )}
      </motion.div>
    </div>
  )
}
