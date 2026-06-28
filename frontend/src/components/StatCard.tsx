import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { cn } from '../lib/utils'
import type { LucideIcon } from 'lucide-react'

interface StatCardProps {
  label: string
  value: number | string
  icon: LucideIcon
  trend?: number
  color?: 'azure' | 'teal' | 'gold' | 'emerald'
  delay?: number
}

const colorMap = {
  azure: { value: 'text-azure-400', icon: 'text-azure-500', bg: 'bg-azure-600/10', glow: 'shadow-azure-600/10' },
  teal: { value: 'text-teal-300', icon: 'text-teal-400', bg: 'bg-teal-400/10', glow: 'shadow-teal-400/10' },
  gold: { value: 'text-gold-300', icon: 'text-gold-400', bg: 'bg-gold-400/10', glow: 'shadow-gold-400/10' },
  emerald: { value: 'text-emerald-400', icon: 'text-emerald-400', bg: 'bg-emerald-400/10', glow: 'shadow-emerald-400/10' },
}

export default function StatCard({ label, value, icon: Icon, trend, color = 'azure', delay = 0 }: StatCardProps) {
  const colors = colorMap[color]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4, ease: 'easeOut' }}
      className={cn('glass-card p-6 relative overflow-hidden shadow-xl', colors.glow)}
    >
      {/* Background glow */}
      <div className={cn('absolute -top-6 -right-6 w-24 h-24 rounded-full blur-2xl opacity-20', colors.bg)} />

      <div className="flex items-start justify-between mb-4">
        <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center', colors.bg)}>
          <Icon className={cn('w-5 h-5', colors.icon)} />
        </div>
        {trend !== undefined && (
          <div className={cn(
            'flex items-center gap-1 text-xs font-medium',
            trend >= 0 ? 'text-emerald-400' : 'text-red-400'
          )}>
            {trend >= 0 ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
            {Math.abs(trend)}%
          </div>
        )}
      </div>

      <div className={cn('text-3xl font-bold mb-1', colors.value)}>
        {value}
      </div>
      <div className="text-sm text-slate-400 font-medium">{label}</div>
    </motion.div>
  )
}
