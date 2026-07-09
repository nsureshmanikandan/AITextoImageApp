import { motion } from 'framer-motion'
import { Pause, Play, RotateCcw, Square } from 'lucide-react'
import { useState } from 'react'
import { pauseMonitoring, resumeMonitoring, startMonitoring, stopMonitoring } from '../lib/api'
import { cn } from '../lib/utils'
import { useLiveNewsStore } from '../stores/liveNewsStore'
import type { MonitorState } from '../types'

const stateConfig: Record<MonitorState, { label: string; color: string; dot: string }> = {
  active: { label: 'Active', color: 'bg-emerald-400/15 text-emerald-400 border-emerald-400/30', dot: 'bg-emerald-400 animate-pulse' },
  paused: { label: 'Paused', color: 'bg-yellow-400/15 text-yellow-400 border-yellow-400/30', dot: 'bg-yellow-400' },
  stopped: { label: 'Stopped', color: 'bg-slate-400/15 text-slate-400 border-slate-400/30', dot: 'bg-slate-400' },
}

export default function MonitorControls() {
  const { monitorState, setMonitorState } = useLiveNewsStore()
  const [loading, setLoading] = useState(false)
  const config = stateConfig[monitorState]

  const handleAction = async (action: () => Promise<{ status: string }>, newState: MonitorState) => {
    setLoading(true)
    try {
      await action()
      setMonitorState(newState)
    } catch {
      // Silent for now
    } finally {
      setLoading(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-white">Monitor Status</h3>
        <span className={cn('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border', config.color)}>
          <span className={cn('w-1.5 h-1.5 rounded-full', config.dot)} />
          {config.label}
        </span>
      </div>

      <div className="flex items-center gap-2">
        {monitorState === 'stopped' && (
          <button
            onClick={() => handleAction(startMonitoring, 'active')}
            disabled={loading}
            className="btn-primary flex items-center gap-2 text-xs px-3 py-2"
          >
            <Play className="w-3.5 h-3.5" />
            Start
          </button>
        )}

        {monitorState === 'active' && (
          <button
            onClick={() => handleAction(pauseMonitoring, 'paused')}
            disabled={loading}
            className="btn-secondary flex items-center gap-2 text-xs px-3 py-2"
          >
            <Pause className="w-3.5 h-3.5" />
            Pause
          </button>
        )}

        {monitorState === 'paused' && (
          <button
            onClick={() => handleAction(resumeMonitoring, 'active')}
            disabled={loading}
            className="btn-primary flex items-center gap-2 text-xs px-3 py-2"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Resume
          </button>
        )}

        {monitorState !== 'stopped' && (
          <button
            onClick={() => handleAction(stopMonitoring, 'stopped')}
            disabled={loading}
            className="flex items-center gap-2 text-xs px-3 py-2 rounded-lg bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 transition-colors"
          >
            <Square className="w-3.5 h-3.5" />
            Stop
          </button>
        )}
      </div>
    </motion.div>
  )
}
