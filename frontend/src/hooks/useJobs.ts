import { useEffect, useCallback, useRef } from 'react'
import { listJobs, getJob } from '../lib/api'
import { useJobStore } from '../stores/jobStore'
import { isProcessing } from '../lib/utils'

const POLL_INTERVAL = 5000

export function useJobs() {
  const { setJobs, setLoading, setError, jobs } = useJobStore()

  const fetchJobs = useCallback(async () => {
    try {
      const data = await listJobs()
      setJobs(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load jobs')
    }
  }, [setJobs, setError])

  useEffect(() => {
    setLoading(true)
    fetchJobs().finally(() => setLoading(false))
  }, [fetchJobs, setLoading])

  // Polling fallback for any active jobs without a live WS
  const activeJobs = jobs.filter((j) => isProcessing(j.status))
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const updateJob = useJobStore((s) => s.updateJob)

  useEffect(() => {
    if (activeJobs.length === 0) {
      if (pollRef.current) clearInterval(pollRef.current)
      return
    }

    pollRef.current = setInterval(async () => {
      for (const job of activeJobs) {
        try {
          const updated = await getJob(job.id)
          updateJob(updated)
        } catch {
          // silent
        }
      }
    }, POLL_INTERVAL)

    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [activeJobs.length, updateJob]) // eslint-disable-line react-hooks/exhaustive-deps

  return { fetchJobs }
}
