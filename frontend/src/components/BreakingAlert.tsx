import { AnimatePresence, motion } from 'framer-motion'
import { X, Zap } from 'lucide-react'
import { useEffect, useState } from 'react'

interface BreakingAlertData {
  title: string
  feed_name: string
}

export default function BreakingAlert() {
  const [alerts, setAlerts] = useState<(BreakingAlertData & { id: number })[]>([])

  useEffect(() => {
    let nextId = 0
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail as BreakingAlertData
      const id = nextId++
      setAlerts((prev) => [...prev, { ...detail, id }])

      // Auto-dismiss after 10 seconds
      setTimeout(() => {
        setAlerts((prev) => prev.filter((a) => a.id !== id))
      }, 10000)
    }

    window.addEventListener('breaking-alert', handler)
    return () => window.removeEventListener('breaking-alert', handler)
  }, [])

  const dismiss = (id: number) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id))
  }

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      <AnimatePresence>
        {alerts.map((alert) => (
          <motion.div
            key={alert.id}
            initial={{ opacity: 0, x: 50, scale: 0.9 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 50, scale: 0.9 }}
            transition={{ duration: 0.3 }}
            className="glass-card p-4 border-l-4 border-l-red-500 shadow-2xl shadow-red-500/10"
          >
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-red-500/15 flex items-center justify-center flex-shrink-0">
                <Zap className="w-4 h-4 text-red-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[10px] font-bold uppercase text-red-400 tracking-wide mb-0.5">
                  Breaking News
                </p>
                <p className="text-sm font-medium text-white truncate">{alert.title}</p>
                <p className="text-xs text-slate-400 mt-0.5">{alert.feed_name}</p>
              </div>
              <button
                onClick={() => dismiss(alert.id)}
                className="text-slate-500 hover:text-white transition-colors flex-shrink-0"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
