import { motion } from 'framer-motion'
import { Newspaper, Play, Megaphone, GraduationCap, Layers } from 'lucide-react'
import type { VideoMode } from '../types'

interface Props {
  selectedMode: VideoMode
  onSelect: (mode: VideoMode) => void
}

const MODES = [
  { id: 'article' as VideoMode, icon: Newspaper, label: 'News Article', desc: 'News URL → regional language slideshow', color: 'azure' },
  { id: 'youtube' as VideoMode, icon: Play, label: 'YouTube Dub', desc: 'YouTube video → dubbed in your language', color: 'red' },
  { id: 'brand_ad' as VideoMode, icon: Megaphone, label: 'Brand Ad', desc: 'Create regional language brand ad', color: 'purple' },
  { id: 'educational' as VideoMode, icon: GraduationCap, label: 'Educational', desc: 'Topic → structured learning video', color: 'emerald' },
  { id: 'batch' as VideoMode, icon: Layers, label: 'Batch / Trending', desc: 'Multiple videos from trending topics', color: 'amber' },
]

const colorMap: Record<string, { border: string, bg: string, icon: string }> = {
  azure: { border: 'border-azure-500', bg: 'bg-azure-500/10', icon: 'text-azure-400' },
  red: { border: 'border-red-500', bg: 'bg-red-500/10', icon: 'text-red-400' },
  purple: { border: 'border-purple-500', bg: 'bg-purple-500/10', icon: 'text-purple-400' },
  emerald: { border: 'border-emerald-500', bg: 'bg-emerald-500/10', icon: 'text-emerald-400' },
  amber: { border: 'border-amber-500', bg: 'bg-amber-500/10', icon: 'text-amber-400' },
}

export default function ModeSelector({ selectedMode, onSelect }: Props) {
  return (
    <div className="overflow-x-auto pb-2">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 min-w-max lg:min-w-0">
        {MODES.map((mode) => {
          const Icon = mode.icon
          const colors = colorMap[mode.color]
          const isSelected = selectedMode === mode.id
          return (
            <motion.button
              key={mode.id}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onSelect(mode.id)}
              className={`glass-card p-4 text-left cursor-pointer border-2 transition-all ${
                isSelected ? `${colors.border} ${colors.bg}` : 'border-transparent'
              }`}
            >
              <Icon className={`w-6 h-6 mb-2 ${isSelected ? colors.icon : 'text-slate-400'}`} />
              <div className={`font-semibold text-sm ${isSelected ? 'text-white' : 'text-slate-300'}`}>{mode.label}</div>
              <div className="text-xs text-slate-500 mt-1 leading-snug">{mode.desc}</div>
            </motion.button>
          )
        })}
      </div>
    </div>
  )
}
