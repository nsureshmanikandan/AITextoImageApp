import { motion } from 'framer-motion'
import { cn } from '../lib/utils'
import type { Language } from '../types'
import { LANGUAGE_OPTIONS } from '../types'

interface LanguagePickerProps {
  value: Language | null
  onChange: (lang: Language) => void
}

export default function LanguagePicker({ value, onChange }: LanguagePickerProps) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      {LANGUAGE_OPTIONS.map((lang) => {
        const selected = value === lang.value
        return (
          <motion.button
            key={lang.value}
            whileHover={{ scale: 1.02, y: -2 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => onChange(lang.value)}
            className={cn(
              'relative flex flex-col items-center gap-2 p-4 rounded-2xl border-2 transition-all duration-200 cursor-pointer text-left',
              selected
                ? 'border-azure-500 bg-azure-600/15 shadow-lg shadow-azure-600/20'
                : 'border-white/10 bg-navy-800/60 hover:border-white/20 hover:bg-navy-800'
            )}
          >
            {selected && (
              <motion.div
                layoutId="lang-select-glow"
                className="absolute inset-0 rounded-2xl bg-azure-500/10 pointer-events-none"
                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
              />
            )}
            <span className="text-3xl">{lang.flag}</span>
            <div className="text-center">
              <div className={cn(
                'text-sm font-semibold',
                selected ? 'text-azure-300' : 'text-white'
              )}>
                {lang.label}
              </div>
              <div className="text-xs text-slate-500 mt-0.5">{lang.nativeName}</div>
            </div>
            {selected && (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="absolute top-2 right-2 w-5 h-5 bg-azure-500 rounded-full flex items-center justify-center"
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
