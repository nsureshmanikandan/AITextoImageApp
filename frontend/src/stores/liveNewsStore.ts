import { create } from 'zustand'
import { getLiveNewsWebSocketUrl } from '../lib/api'
import type { FeedConfiguration, FeedHealthStatus, LiveNewsDashboardStats, LiveNewsWSMessage, MonitorState, QueueItem } from '../types'

interface LiveNewsStore {
  monitorState: MonitorState
  feeds: FeedConfiguration[]
  dashboardStats: LiveNewsDashboardStats
  queueItems: QueueItem[]
  wsConnected: boolean

  setMonitorState: (state: MonitorState) => void
  setFeeds: (feeds: FeedConfiguration[]) => void
  updateFeedStatus: (feedId: number, status: FeedHealthStatus) => void
  addQueueItem: (item: QueueItem) => void
  removeQueueItem: (jobId: number) => void
  setDashboardStats: (stats: LiveNewsDashboardStats) => void
  setWsConnected: (connected: boolean) => void

  connectWebSocket: () => void
  disconnectWebSocket: () => void
}

const DEFAULT_STATS: LiveNewsDashboardStats = {
  monitor_state: 'stopped',
  total_active_feeds: 0,
  degraded_feeds: 0,
  articles_detected_last_hour: 0,
  videos_awaiting_review: 0,
  videos_auto_approved_last_hour: 0,
  active_processing_jobs: 0,
}

let ws: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null

export const useLiveNewsStore = create<LiveNewsStore>((set, get) => ({
  monitorState: 'stopped',
  feeds: [],
  dashboardStats: DEFAULT_STATS,
  queueItems: [],
  wsConnected: false,

  setMonitorState: (monitorState) => set({ monitorState }),

  setFeeds: (feeds) => set({ feeds }),

  updateFeedStatus: (feedId, status) =>
    set((state) => ({
      feeds: state.feeds.map((f) =>
        f.id === feedId ? { ...f, health_status: status } : f
      ),
    })),

  addQueueItem: (item) =>
    set((state) => ({
      queueItems: [item, ...state.queueItems],
    })),

  removeQueueItem: (jobId) =>
    set((state) => ({
      queueItems: state.queueItems.filter((q) => q.job_id !== jobId),
    })),

  setDashboardStats: (dashboardStats) => set({ dashboardStats }),

  setWsConnected: (wsConnected) => set({ wsConnected }),

  connectWebSocket: () => {
    if (ws && ws.readyState === WebSocket.OPEN) return

    const url = getLiveNewsWebSocketUrl()
    ws = new WebSocket(url)

    ws.onopen = () => {
      get().setWsConnected(true)
      if (reconnectTimer) {
        clearTimeout(reconnectTimer)
        reconnectTimer = null
      }
    }

    ws.onmessage = (event) => {
      try {
        const message: LiveNewsWSMessage = JSON.parse(event.data)
        const { type, payload } = message

        switch (type) {
          case 'feed_status': {
            const { feed_id, health_status } = payload as { feed_id: number; health_status: FeedHealthStatus }
            get().updateFeedStatus(feed_id, health_status)
            break
          }
          case 'new_queue_item': {
            get().addQueueItem(payload as QueueItem)
            break
          }
          case 'stats_update': {
            get().setDashboardStats(payload as LiveNewsDashboardStats)
            break
          }
          case 'monitor_state': {
            const { state } = payload as { state: MonitorState }
            get().setMonitorState(state)
            break
          }
          case 'breaking_alert': {
            // Handled by BreakingAlert component listening to a custom event
            window.dispatchEvent(new CustomEvent('breaking-alert', { detail: payload }))
            break
          }
        }
      } catch {
        // Ignore malformed messages
      }
    }

    ws.onclose = () => {
      get().setWsConnected(false)
      ws = null
      // Auto-reconnect after 3 seconds
      reconnectTimer = setTimeout(() => {
        get().connectWebSocket()
      }, 3000)
    }

    ws.onerror = () => {
      ws?.close()
    }
  },

  disconnectWebSocket: () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      ws.close()
      ws = null
    }
    get().setWsConnected(false)
  },
}))
