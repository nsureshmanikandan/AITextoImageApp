import { Outlet, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import Sidebar from './Sidebar'

const PAGE_TITLES: Record<string, { title: string; subtitle?: string }> = {
  '/': { title: 'Dashboard', subtitle: 'Overview of your AI video newsroom' },
  '/create': { title: 'Create Video', subtitle: 'Generate a regional language news video from an article URL' },
  '/history': { title: 'Video History', subtitle: 'Browse and manage all generated videos' },
}

export default function Layout() {
  const location = useLocation()
  const meta = PAGE_TITLES[location.pathname] ??
    (location.pathname.startsWith('/review/')
      ? { title: 'Review Video', subtitle: 'Preview, approve or regenerate your video' }
      : { title: 'VernacularCast' })

  return (
    <div className="flex h-screen overflow-hidden bg-navy-950">
      {/* Sidebar — fixed width */}
      <div className="hidden md:flex flex-col flex-shrink-0" style={{ width: 260 }}>
        <Sidebar />
      </div>

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-white/5 bg-navy-900/40 backdrop-blur-xl sticky top-0 z-20 flex-shrink-0">
          <div>
            <h1 className="text-lg font-bold text-white">{meta.title}</h1>
            {meta.subtitle && <p className="text-xs text-slate-500">{meta.subtitle}</p>}
          </div>
          <div className="flex items-center gap-3">
            <button className="relative w-9 h-9 rounded-xl bg-navy-800/60 border border-white/10 flex items-center justify-center text-slate-400 hover:text-white hover:border-white/20 transition-all">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6 6 0 10-12 0v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>
            </button>
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-azure-600 to-teal-400 flex items-center justify-center shadow-lg shadow-azure-600/20">
              <span className="text-xs font-bold text-white">NS</span>
            </div>
          </div>
        </header>

        {/* Scrollable page content */}
        <main className="flex-1 overflow-y-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              className="h-full"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}
