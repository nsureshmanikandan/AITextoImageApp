import { useEffect, useRef } from 'react'
import { getWebSocketUrl } from '../lib/api'
import { useJobStore } from '../stores/jobStore'
import type { Job } from '../types'

export function useJobProgress(jobId: string | null) {
  const wsRef = useRef<WebSocket | null>(null)
  const updateJob = useJobStore((s) => s.updateJob)
  const setCurrentJob = useJobStore((s) => s.setCurrentJob)

  useEffect(() => {
    if (!jobId) return

    let reconnectTimer: ReturnType<typeof setTimeout>
    let shouldReconnect = true

    function connect() {
      const url = getWebSocketUrl(jobId!)
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        console.debug(`[WS] Connected for job ${jobId}`)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as Partial<Job>
          if (data && data.id) {
            updateJob(data as Job)
            setCurrentJob(data as Job)
          }
        } catch (e) {
          console.warn('[WS] Failed to parse message', e)
        }
      }

      ws.onerror = (err) => {
        console.warn('[WS] Error', err)
      }

      ws.onclose = () => {
        console.debug(`[WS] Closed for job ${jobId}`)
        if (shouldReconnect) {
          reconnectTimer = setTimeout(connect, 3000)
        }
      }
    }

    connect()

    return () => {
      shouldReconnect = false
      clearTimeout(reconnectTimer)
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [jobId, updateJob, setCurrentJob])
}
