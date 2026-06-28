import { Bell, Search } from 'lucide-react'
import { useJobStore } from '../stores/jobStore'

interface HeaderProps {
  title: string
  subtitle?: string
}

export default function Header({ title, subtitle }: HeaderProps) {
  const jobs = useJobStore((s) => s.jobs)
  const pendingCount = jobs.filter((j) => j.status === 'awaiting_review').length

  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-white/5 bg-navy-900/40 backdrop-blur-xl sticky top-0 z-20">
      <div>
        <h1 className="text-lg font-bold text-white">{title}</h1>
        {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-3">
        {/* Search (decorative for demo) */}
        <button className="w-9 h-9 rounded-xl bg-navy-800/60 border border-white/10 flex items-center justify-center text-slate-400 hover:text-white hover:border-white/20 transition-all">
          <Search className="w-4 h-4" />
        </button>

        {/* Notifications */}
        <button className="relative w-9 h-9 rounded-xl bg-navy-800/60 border border-white/10 flex items-center justify-center text-slate-400 hover:text-white hover:border-white/20 transition-all">
          <Bell className="w-4 h-4" />
          {pendingCount > 0 && (
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-azure-500 rounded-full text-[9px] font-bold text-white flex items-center justify-center">
              {pendingCount > 9 ? '9+' : pendingCount}
            </span>
          )}
        </button>

        {/* Avatar */}
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-azure-600 to-teal-400 flex items-center justify-center shadow-lg shadow-azure-600/20">
          <span className="text-xs font-bold text-white">NS</span>
        </div>
      </div>
    </header>
  )
}
