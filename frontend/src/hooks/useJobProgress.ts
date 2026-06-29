import { useEffect, useRef } from 'react'
import { getWebSocketUrl, getJob } from '../lib/api'
import { useJobStore } from '../stores/jobStore'
import type { Job, JobStep } from '../types'

// Map backend step statuses → frontend display statuses
function normaliseStepStatus(s: string): JobStep['status'] {
  if (s === 'started' || s === 'active') return 'active'
  if (s === 'completed' || s === 'done') return 'done'
  if (s === 'failed' || s === 'error') return 'error'
  return 'pending'
}

function normaliseSteps(raw: unknown[]): JobStep[] {
  if (!Array.isArray(raw)) return []
  return raw.map((s: any) => ({
    step:    s.step    ?? s.key ?? '',
    status:  normaliseStepStatus(s.status ?? ''),
    message: s.message ?? '',
    ts:      s.ts      ?? s.timestamp ?? new Date().toISOString(),
  }))
}

// Derive which step should look "active" from job status alone
export function deriveStepsFromStatus(status: string): JobStep[] {
  const order = ['scraping','generating_script','generating_voice','rendering_video','awaiting_review']
  const activeIdx = order.indexOf(status)
  return order.map((key, i) => ({
    step:    key,
    status:  i < activeIdx ? 'done' : i === activeIdx ? 'active' : 'pending',
    message: '',
    ts:      new Date().toISOString(),
  }))
}

export function useJobProgress(jobId: string | null) {
  const wsRef = useRef<WebSocket | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const updateJob = useJobStore((s) => s.updateJob)
  const setCurrentJob = useJobStore((s) => s.setCurrentJob)

  useEffect(() => {
    if (!jobId) return

    let shouldReconnect = true
    let reconnectTimer: ReturnType<typeof setTimeout>

    // --- HTTP polling fallback (runs regardless of WS) ---
    // Poll fast (1s) while job is running so we catch short steps like scraping
    const POLL_INTERVAL = 1000
    pollRef.current = setInterval(async () => {
      try {
        const job = await getJob(jobId)
        const enriched: Job = {
          ...job,
          steps: job.steps?.length ? normaliseSteps(job.steps) : deriveStepsFromStatus(job.status),
        }
        updateJob(enriched)
        setCurrentJob(enriched)
        // Stop polling once terminal state reached, then do one final fetch to load quality scores
        if (['awaiting_review','ready','approved','failed'].includes(job.status)) {
          clearInterval(pollRef.current!)
          setTimeout(async () => {
            try {
              const final = await getJob(jobId)
              const enriched: Job = {
                ...final,
                steps: final.steps?.length ? normaliseSteps(final.steps) : deriveStepsFromStatus(final.status),
              }
              updateJob(enriched)
              setCurrentJob(enriched)
            } catch { /* ignore */ }
          }, 2000)
        }
      } catch { /* ignore */ }
    }, POLL_INTERVAL)

    // --- WebSocket (real-time updates on top of polling) ---
    function connect() {
      const url = getWebSocketUrl(jobId!)
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => console.debug(`[WS] Connected job ${jobId}`)

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data?.type === 'ping') return          // heartbeat, ignore

          // Backend sends job_id (not id) — normalise
          const id = String(data.job_id ?? data.id ?? jobId)
          if (!data.status) return

          const rawSteps: unknown[] = data.steps ?? []
          const steps = rawSteps.length
            ? normaliseSteps(rawSteps)
            : deriveStepsFromStatus(data.status)

          const patch: Partial<Job> & { id: string } = {
            id,
            status: data.status,
            steps,
            ...(data.script    && { script: data.script }),
            ...(data.error     && { error:  data.error  }),
            ...(data.video_path && { video_path: data.video_path }),
          }
          updateJob(patch as Job)
          setCurrentJob(patch as Job)
        } catch (e) {
          console.warn('[WS] Parse error', e)
        }
      }

      ws.onerror  = () => {}    // onclose will handle reconnect
      ws.onclose  = () => {
        console.debug(`[WS] Closed job ${jobId}`)
        if (shouldReconnect) reconnectTimer = setTimeout(connect, 3000)
      }
    }

    connect()

    return () => {
      shouldReconnect = false
      clearTimeout(reconnectTimer)
      clearInterval(pollRef.current!)
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [jobId, updateJob, setCurrentJob])
}
