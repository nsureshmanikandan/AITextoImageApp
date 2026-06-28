import { motion, AnimatePresence } from 'framer-motion'
import { Check, AlertCircle } from 'lucide-react'
import { cn } from '../lib/utils'
import type { JobStep } from '../types'
import { PIPELINE_STEPS } from '../types'

interface ProgressStepperProps {
  steps: JobStep[]
  currentStatus?: string
}

export default function ProgressStepper({ steps }: ProgressStepperProps) {
  const getStepData = (key: string) => {
    return steps.find((s) => s.step === key)
  }

  return (
    <div className="flex flex-col gap-0">
      {PIPELINE_STEPS.map((pipeStep, index) => {
        const stepData = getStepData(pipeStep.key)
        const status = stepData?.status ?? 'pending'
        const isLast = index === PIPELINE_STEPS.length - 1

        return (
          <div key={pipeStep.key} className="flex gap-4">
            {/* Left: icon + connector */}
            <div className="flex flex-col items-center">
              <div className="relative flex items-center justify-center w-10 h-10 flex-shrink-0">
                {/* Outer ring for active */}
                {status === 'active' && (
                  <motion.div
                    className="absolute inset-0 rounded-full border-2 border-azure-500/40"
                    animate={{ scale: [1, 1.3, 1], opacity: [0.6, 0, 0.6] }}
                    transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                  />
                )}

                <motion.div
                  initial={{ scale: 0.8 }}
                  animate={{ scale: 1 }}
                  className={cn(
                    'w-10 h-10 rounded-full flex items-center justify-center border-2 relative z-10',
                    status === 'done' && 'bg-emerald-400/20 border-emerald-400 text-emerald-400',
                    status === 'active' && 'bg-azure-600/20 border-azure-500 text-azure-400',
                    status === 'pending' && 'bg-navy-800 border-navy-600 text-slate-600',
                    status === 'error' && 'bg-red-500/20 border-red-500 text-red-400'
                  )}
                >
                  {status === 'done' && <Check className="w-5 h-5" strokeWidth={2.5} />}
                  {status === 'active' && (
                    <div className="w-4 h-4 border-2 border-azure-400 border-t-transparent rounded-full animate-spin" />
                  )}
                  {status === 'pending' && (
                    <div className="w-2.5 h-2.5 rounded-full bg-navy-600" />
                  )}
                  {status === 'error' && <AlertCircle className="w-5 h-5" />}
                </motion.div>
              </div>

              {/* Connector line */}
              {!isLast && (
                <div className="w-0.5 flex-1 min-h-[32px] my-1 relative overflow-hidden">
                  <div className="absolute inset-0 bg-navy-700" />
                  {status === 'done' && (
                    <motion.div
                      className="absolute inset-0 bg-emerald-400/40"
                      initial={{ scaleY: 0, originY: 0 }}
                      animate={{ scaleY: 1 }}
                      transition={{ duration: 0.5, ease: 'easeOut' }}
                    />
                  )}
                  {status === 'active' && (
                    <motion.div
                      className="absolute inset-0 bg-azure-500/40"
                      animate={{ opacity: [0.4, 1, 0.4] }}
                      transition={{ duration: 1.5, repeat: Infinity }}
                    />
                  )}
                </div>
              )}
            </div>

            {/* Right: content */}
            <div className="pb-8 pt-1.5 flex-1">
              <AnimatePresence mode="wait">
                <motion.div
                  key={status}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3 }}
                >
                  <div className="flex items-center gap-2 mb-0.5">
                    <p className={cn(
                      'text-sm font-semibold',
                      status === 'done' && 'text-emerald-400',
                      status === 'active' && 'text-white',
                      status === 'pending' && 'text-slate-500',
                      status === 'error' && 'text-red-400'
                    )}>
                      {pipeStep.label}
                    </p>
                    {status === 'active' && (
                      <span className="text-xs text-azure-400 bg-azure-600/10 border border-azure-500/20 px-2 py-0.5 rounded-full">
                        In progress
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500">
                    {stepData?.message || pipeStep.description}
                  </p>
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        )
      })}
    </div>
  )
}
