import { motion } from 'framer-motion'
import { History, LayoutDashboard, Mic2, Radio, Rss, Settings2, Video } from 'lucide-react'
import { NavLink, useLocation } from 'react-router-dom'
import { cn } from '../lib/utils'

const NAV_ITEMS = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard, exact: true },
  { path: '/create', label: 'Create Video', icon: Video },
  { path: '/history', label: 'History', icon: History },
]

const LIVE_NEWS_ITEMS = [
  { path: '/live-news', label: 'Live Monitor', icon: Radio, exact: true },
  { path: '/live-news/queue', label: 'Approval Queue', icon: Rss },
  { path: '/live-news/feeds', label: 'Feed Config', icon: Settings2 },
]

interface SidebarProps {
  collapsed?: boolean
}

export default function Sidebar({ collapsed = false }: SidebarProps) {
  const location = useLocation()

  return (
    <motion.aside
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className="flex flex-col h-full bg-navy-900/80 border-r border-white/5 backdrop-blur-xl"
      style={{ width: collapsed ? 72 : 260 }}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-6 border-b border-white/5">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-azure-600 to-azure-500 flex items-center justify-center flex-shrink-0 shadow-lg shadow-azure-600/30">
          <Mic2 className="w-5 h-5 text-white" />
        </div>
        {!collapsed && (
          <motion.div
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.15 }}
          >
            <div className="text-white font-bold text-base leading-tight">VernacularCast</div>
            <div className="text-azure-400/70 text-xs font-medium">AI Video Newsroom</div>
          </motion.div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 flex flex-col gap-1">
        {NAV_ITEMS.map(({ path, label, icon: Icon, exact }) => {
          const isActive = exact
            ? location.pathname === path
            : location.pathname.startsWith(path)

          return (
            <NavLink
              key={path}
              to={path}
              end={exact}
              className={({ isActive: ia }) =>
                cn(
                  'relative flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 group overflow-hidden',
                  ia
                    ? 'bg-azure-600/15 text-azure-300'
                    : 'text-slate-400 hover:text-white hover:bg-navy-800/60'
                )
              }
            >
              {isActive && (
                <motion.div
                  layoutId="nav-active-bg"
                  className="absolute inset-0 bg-azure-600/10 rounded-xl"
                  transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                />
              )}
              {isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-azure-500 rounded-r-full" />
              )}

              <motion.div
                whileHover={{ x: 2 }}
                transition={{ duration: 0.15 }}
                className="flex items-center gap-3 relative z-10"
              >
                <Icon className={cn('w-5 h-5 flex-shrink-0', isActive ? 'text-azure-400' : '')} />
                {!collapsed && (
                  <span className="text-sm font-medium">{label}</span>
                )}
              </motion.div>
            </NavLink>
          )
        })}

        {/* Live News Section */}
        {!collapsed && (
          <div className="mt-4 mb-1 px-3">
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Live News</span>
          </div>
        )}
        {collapsed && <div className="my-2 mx-3 border-t border-white/5" />}

        {LIVE_NEWS_ITEMS.map(({ path, label, icon: Icon, exact }) => {
          const isActive = exact
            ? location.pathname === path
            : location.pathname.startsWith(path)

          return (
            <NavLink
              key={path}
              to={path}
              end={exact}
              className={({ isActive: ia }) =>
                cn(
                  'relative flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 group overflow-hidden',
                  ia
                    ? 'bg-azure-600/15 text-azure-300'
                    : 'text-slate-400 hover:text-white hover:bg-navy-800/60'
                )
              }
            >
              {isActive && (
                <motion.div
                  layoutId="nav-active-bg"
                  className="absolute inset-0 bg-azure-600/10 rounded-xl"
                  transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                />
              )}
              {isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-azure-500 rounded-r-full" />
              )}

              <motion.div
                whileHover={{ x: 2 }}
                transition={{ duration: 0.15 }}
                className="flex items-center gap-3 relative z-10"
              >
                <Icon className={cn('w-5 h-5 flex-shrink-0', isActive ? 'text-azure-400' : '')} />
                {!collapsed && (
                  <span className="text-sm font-medium">{label}</span>
                )}
              </motion.div>
            </NavLink>
          )
        })}
      </nav>

      {/* Bottom version badge */}
      {!collapsed && (
        <div className="px-5 pb-5 pt-3 border-t border-white/5">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs text-slate-500 font-medium">v1.0 · Hackathon</span>
          </div>
        </div>
      )}
    </motion.aside>
  )
}
