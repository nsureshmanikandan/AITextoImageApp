import { motion } from 'framer-motion'
import { cn } from '../lib/utils'
import type { VideoFormat } from '../types'
import { FORMAT_OPTIONS } from '../types'

interface FormatPickerProps {
  value: VideoFormat | null
  onChange: (format: VideoFormat) => void
}

function VerticalMockup({ selected }: { selected: boolean }) {
  return (
    <div className={cn(
      'mx-auto w-14 h-24 rounded-xl border-2 overflow-hidden flex flex-col transition-colors',
      selected ? 'border-azure-400' : 'border-slate-600'
    )}>
      <div className={cn('h-3 flex items-center justify-center gap-1', selected ? 'bg-azure-600/30' : 'bg-navy-700')}>
        <div className="w-3 h-1 rounded bg-slate-500" />
        <div className="w-1 h-1 rounded-full bg-slate-500" />
      </div>
      <div className={cn('flex-1', selected ? 'bg-azure-600/10' : 'bg-navy-800')}>
        <div className="h-full flex flex-col p-1 gap-1">
          <div className={cn('h-10 rounded', selected ? 'bg-azure-600/30' : 'bg-navy-700')} />
          <div className={cn('h-1.5 rounded w-4/5', selected ? 'bg-azure-500/20' : 'bg-navy-700')} />
          <div className={cn('h-1.5 rounded w-3/5', selected ? 'bg-azure-500/20' : 'bg-navy-700')} />
        </div>
      </div>
    </div>
  )
}

function LandscapeMockup({ selected }: { selected: boolean }) {
  return (
    <div className={cn(
      'mx-auto w-32 h-20 rounded-lg border-2 overflow-hidden flex flex-col transition-colors',
      selected ? 'border-azure-400' : 'border-slate-600'
    )}>
      <div className={cn('h-3 flex items-center gap-1 px-2', selected ? 'bg-azure-600/30' : 'bg-navy-700')}>
        <div className="flex gap-0.5">
          {[0,1,2].map(i => (
            <div key={i} className={cn('w-1.5 h-1.5 rounded-full', selected ? 'bg-azure-400/60' : 'bg-slate-600')} />
          ))}
        </div>
        <div className={cn('flex-1 h-1.5 rounded mx-1', selected ? 'bg-azure-500/20' : 'bg-navy-800')} />
      </div>
      <div className={cn('flex-1', selected ? 'bg-azure-600/10' : 'bg-navy-800')}>
        <div className="h-full flex p-1.5 gap-1.5">
          <div className={cn('w-16 rounded', selected ? 'bg-azure-600/30' : 'bg-navy-700')} />
          <div className="flex-1 flex flex-col gap-1 pt-1">
            <div className={cn('h-1.5 rounded', selected ? 'bg-azure-500/20' : 'bg-navy-700')} />
            <div className={cn('h-1.5 rounded w-4/5', selected ? 'bg-azure-500/20' : 'bg-navy-700')} />
            <div className={cn('h-1.5 rounded w-3/5', selected ? 'bg-azure-500/20' : 'bg-navy-700')} />
          </div>
        </div>
      </div>
    </div>
  )
}

export default function FormatPicker({ value, onChange }: FormatPickerProps) {
  return (
    <div className="grid grid-cols-2 gap-4">
      {FORMAT_OPTIONS.map((fmt) => {
        const selected = value === fmt.value
        return (
          <motion.button
            key={fmt.value}
            whileHover={{ scale: 1.02, y: -2 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => onChange(fmt.value)}
            className={cn(
              'relative flex flex-col items-center gap-4 p-6 rounded-2xl border-2 transition-all duration-200 cursor-pointer',
              selected
                ? 'border-azure-500 bg-azure-600/15 shadow-lg shadow-azure-600/20'
                : 'border-white/10 bg-navy-800/60 hover:border-white/20 hover:bg-navy-800'
            )}
          >
            {fmt.value === 'vertical_9_16'
              ? <VerticalMockup selected={selected} />
              : <LandscapeMockup selected={selected} />}

            <div className="text-center">
              <div className={cn('text-sm font-bold', selected ? 'text-azure-300' : 'text-white')}>
                {fmt.label}
              </div>
              <div className="text-xs text-slate-500 mt-1">{fmt.description}</div>
            </div>

            {selected && (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="absolute top-3 right-3 w-5 h-5 bg-azure-500 rounded-full flex items-center justify-center"
              >
                <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </motion.div>
            )}
          </motion.button>
        )
      })}
    </div>
  )
}
