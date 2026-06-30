import { motion, AnimatePresence } from 'framer-motion'
import { Check, AlertCircle, Mic, FileText, Video, Search, Eye, Wand2, Image } from 'lucide-react'
import { cn } from '../lib/utils'
import type { JobStep } from '../types'
import { PIPELINE_STEPS } from '../types'
import { deriveStepsFromStatus } from '../hooks/useJobProgress'

interface ProgressStepperProps {
  steps: JobStep[]
  currentStatus?: string
  pipelineSteps?: typeof PIPELINE_STEPS
}

const STEP_ICONS: Record<string, React.FC<{ className?: string }>> = {
  scraping:           ({ className }) => <Search   className={className} />,
  generating_script:  ({ className }) => <FileText className={className} />,
  generating_voice:   ({ className }) => <Mic      className={className} />,
  rendering_video:    ({ className }) => <Video    className={className} />,
  awaiting_review:    ({ className }) => <Eye      className={className} />,
  sora_prompt:        ({ className }) => <Wand2    className={className} />,
  brand_images:       ({ className }) => <Image    className={className} />,
}

export default function ProgressStepper({ steps, currentStatus, pipelineSteps }: ProgressStepperProps) {
  const activeSteps = pipelineSteps ?? PIPELINE_STEPS
  // If WS hasn't sent steps yet, derive them from job status
  const effectiveSteps: JobStep[] =
    steps.length > 0 ? steps : (currentStatus ? deriveStepsFromStatus(currentStatus) : [])

  const getStepData = (key: string): JobStep =>
    effectiveSteps.find((s) => s.step === key) ?? { step: key, status: 'pending', message: '', ts: '' }

  return (
    <div className="flex flex-col gap-0 w-full">
      {activeSteps.map((pipeStep, index) => {
        const stepData  = getStepData(pipeStep.key)
        const status    = stepData.status
        const isLast    = index === activeSteps.length - 1
        const StepIcon  = STEP_ICONS[pipeStep.key]

        return (
          <div key={pipeStep.key} className="flex gap-4">
            {/* Left column: icon bubble + connector */}
            <div className="flex flex-col items-center">

              {/* ── Icon bubble ── */}
              <div className="relative flex items-center justify-center w-11 h-11 flex-shrink-0">

                {/* Pulse ring — active only */}
                {status === 'active' && (
                  <motion.div
                    className="absolute inset-0 rounded-full border-2 border-azure-400/50"
                    animate={{ scale: [1, 1.5, 1], opacity: [0.7, 0, 0.7] }}
                    transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
                  />
                )}
                {status === 'active' && (
                  <motion.div
                    className="absolute inset-0 rounded-full border border-azure-400/30"
                    animate={{ scale: [1, 1.9, 1], opacity: [0.4, 0, 0.4] }}
                    transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut', delay: 0.3 }}
                  />
                )}

                <motion.div
                  initial={{ scale: 0.7, opacity: 0 }}
                  animate={{ scale: 1,   opacity: 1 }}
                  transition={{ duration: 0.35, ease: 'backOut' }}
                  className={cn(
                    'w-11 h-11 rounded-full flex items-center justify-center relative z-10 transition-all duration-500',
                    status === 'done'    && 'bg-emerald-500/20 border-2 border-emerald-400 shadow-[0_0_12px_rgba(0,201,120,0.35)]',
                    status === 'active'  && 'bg-azure-600/30  border-2 border-azure-400  shadow-[0_0_16px_rgba(0,134,240,0.5)]',
                    status === 'pending' && 'bg-navy-800/60   border-2 border-navy-600/60',
                    status === 'error'   && 'bg-red-500/20    border-2 border-red-400     shadow-[0_0_12px_rgba(255,77,77,0.35)]',
                  )}
                >
                  {/* Spinner overlay for active */}
                  {status === 'active' && (
                    <div className="absolute inset-0 rounded-full overflow-hidden">
                      <motion.div
                        className="absolute inset-0 rounded-full border-2 border-transparent border-t-azure-400"
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                      />
                    </div>
                  )}

                  <AnimatePresence mode="wait">
                    {status === 'done' && (
                      <motion.div key="done"
                        initial={{ scale: 0, rotate: -90 }}
                        animate={{ scale: 1, rotate: 0 }}
                        transition={{ type: 'spring', stiffness: 400, damping: 20 }}>
                        <Check className="w-5 h-5 text-emerald-400" strokeWidth={2.5} />
                      </motion.div>
                    )}
                    {status === 'error' && (
                      <motion.div key="error"
                        initial={{ scale: 0 }} animate={{ scale: 1 }}>
                        <AlertCircle className="w-5 h-5 text-red-400" />
                      </motion.div>
                    )}
                    {(status === 'active' || status === 'pending') && StepIcon && (
                      <motion.div key="icon"
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                        <StepIcon className={cn(
                          'w-4 h-4',
                          status === 'active'  && 'text-azure-300',
                          status === 'pending' && 'text-navy-500',
                        )} />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              </div>

              {/* Connector line */}
              {!isLast && (
                <div className="w-0.5 flex-1 min-h-[28px] my-1 relative overflow-hidden rounded-full bg-navy-700">
                  {status === 'done' && (
                    <motion.div
                      className="absolute inset-0 bg-emerald-400/50"
                      initial={{ scaleY: 0, originY: 0 }}
                      animate={{ scaleY: 1 }}
                      transition={{ duration: 0.6, ease: 'easeOut' }}
                    />
                  )}
                  {status === 'active' && (
                    <motion.div
                      className="absolute inset-0 bg-azure-400/40"
                      animate={{ opacity: [0.3, 1, 0.3] }}
                      transition={{ duration: 1.2, repeat: Infinity }}
                    />
                  )}
                </div>
              )}
            </div>

            {/* Right column: text */}
            <div className={cn('pb-7 pt-2 flex-1 min-w-0', isLast && 'pb-0')}>
              <AnimatePresence mode="wait">
                <motion.div
                  key={status}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10 }}
                  transition={{ duration: 0.25 }}
                >
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={cn(
                      'text-sm font-semibold leading-snug',
                      status === 'done'    && 'text-emerald-400',
                      status === 'active'  && 'text-white',
                      status === 'pending' && 'text-slate-500',
                      status === 'error'   && 'text-red-400',
                    )}>
                      {pipeStep.label}
                    </span>

                    {status === 'active' && (
                      <motion.span
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="text-[10px] font-medium text-azure-300 bg-azure-600/20 border border-azure-500/30 px-2 py-0.5 rounded-full"
                      >
                        In progress…
                      </motion.span>
                    )}
                    {status === 'done' && (
                      <motion.span
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="text-[10px] font-medium text-emerald-400/80 bg-emerald-400/10 border border-emerald-400/20 px-2 py-0.5 rounded-full"
                      >
                        Done
                      </motion.span>
                    )}
                  </div>

                  <p className={cn(
                    'text-xs mt-0.5 leading-relaxed truncate',
                    status === 'active'  && 'text-azure-400/80',
                    status === 'done'    && 'text-slate-500',
                    status === 'pending' && 'text-slate-600',
                    status === 'error'   && 'text-red-400/80',
                  )}>
                    {stepData.message || pipeStep.description}
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
