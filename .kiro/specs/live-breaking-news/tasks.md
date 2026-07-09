# Implementation Plan: Live Breaking News Mode (RSS Auto-Monitor)

## Overview

This plan implements an autonomous RSS feed monitoring system that continuously polls configured news sources, detects new articles, deduplicates them, and automatically triggers the existing article-to-video pipeline. The implementation proceeds from backend data models → core services → API routes → WebSocket integration → frontend store/types → frontend pages/components → integration wiring.

## Tasks

- [x] 1. Data models and database schema
  - [x] 1.1 Create FeedConfiguration SQLModel in `backend/app/models/feed_configuration.py`
    - Define `FeedConfiguration` table with all fields: id, feed_url, display_name, polling_interval_seconds, language, priority_keywords, trust_level, auto_approve, enabled, health_status, consecutive_failures, last_polled_at, last_successful_poll, articles_processed, current_polling_interval, created_at, updated_at
    - Define `FeedConfigCreate`, `FeedConfigRead`, `FeedConfigUpdate` Pydantic schemas
    - Add field validators: polling_interval_seconds >= 60, language in allowed set, trust_level in {trusted, standard, untrusted}, feed_url must be valid HTTP/HTTPS URL
    - _Requirements: 1.1, 1.4, 1.5, 10.1_

  - [x] 1.2 Create ArticleFingerprint SQLModel in `backend/app/models/article_fingerprint.py`
    - Define `ArticleFingerprint` table with fields: id, url_hash (indexed), title_normalized (indexed), original_url, original_title, feed_config_id (FK), job_id, detected_at, status, expires_at
    - Define `DetectedArticle` Pydantic schema for internal passing between services
    - _Requirements: 3.1, 3.3_

  - [x] 1.3 Register new models in `backend/app/models/__init__.py` and update database initialization
    - Import both new models so SQLModel.metadata.create_all picks them up
    - Add migration statements in `main.py` `_run_db_migrations()` for forward compatibility
    - _Requirements: 1.1, 3.1_

  - [ ]* 1.4 Write property tests for FeedConfiguration validation
    - **Property 2: Polling interval minimum enforcement**
    - **Property 3: Invalid URL rejection**
    - **Validates: Requirements 1.4, 1.5, 10.1**

- [x] 2. DeduplicationEngine service
  - [x] 2.1 Implement `backend/app/services/dedup_engine.py`
    - Implement `compute_fingerprint(url: str) -> str` — normalize URL (lowercase, strip utm_*, ref, fbclid params), compute SHA-256 hash
    - Implement `normalize_title(title: str) -> str` — lowercase, strip punctuation, collapse whitespace
    - Implement `is_duplicate(url: str, title: str) -> bool` — check url_hash match OR title similarity >90% via `difflib.SequenceMatcher`
    - Implement `record_article(url: str, title: str, feed_config_id: int) -> ArticleFingerprint` — store fingerprint with computed expires_at
    - Implement `cleanup_expired(retention_days: int = 7) -> int` — delete fingerprints past expiry
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ]* 2.2 Write property test for URL fingerprint determinism
    - **Property 6: URL fingerprint determinism and normalization**
    - **Validates: Requirements 3.1**

  - [ ]* 2.3 Write property test for deduplication round-trip
    - **Property 7: Deduplication round-trip**
    - **Validates: Requirements 3.2**

  - [ ]* 2.4 Write property test for fingerprint retention and expiry
    - **Property 8: Fingerprint retention and expiry**
    - **Validates: Requirements 3.3**

  - [ ]* 2.5 Write property test for title normalization deduplication
    - **Property 9: Title normalization deduplication**
    - **Validates: Requirements 3.4**

- [x] 3. PipelineTrigger service
  - [x] 3.1 Implement `backend/app/services/pipeline_trigger.py`
    - Implement `get_active_job_count() -> int` — count jobs with status in {pending, scraping, generating_script, generating_voice, rendering_video}
    - Implement `should_hold() -> bool` — return True if active count >= MAX_PENDING_JOBS (10)
    - Implement `assign_priority(article: DetectedArticle, config: FeedConfiguration) -> str` — case-insensitive keyword matching against title and summary; return "high" or "standard"
    - Implement `trigger_article(article: DetectedArticle, config: FeedConfiguration) -> Job | None` — create Job with mode="article", correct language, brand_data JSON containing feed_config_id and origin="live_news"; return None if concurrency limits exceeded
    - Sort multiple articles by published_at descending (newest first) before triggering
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 10.2_

  - [ ]* 3.2 Write property test for triggered job correctness
    - **Property 10: Triggered job correctness**
    - **Validates: Requirements 4.1, 4.4**

  - [ ]* 3.3 Write property test for publication-date ordering
    - **Property 11: Publication-date ordering**
    - **Validates: Requirements 4.2**

  - [ ]* 3.4 Write property test for concurrency throttling (pending queue)
    - **Property 12: Concurrency throttling (pending queue)**
    - **Validates: Requirements 4.3**

  - [ ]* 3.5 Write property test for concurrency throttling (active pipeline)
    - **Property 13: Concurrency throttling (active pipeline)**
    - **Validates: Requirements 10.2**

  - [ ]* 3.6 Write property test for priority assignment by keyword presence
    - **Property 14: Priority assignment by keyword presence**
    - **Validates: Requirements 5.1, 5.2, 5.3**

- [x] 4. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. FeedMonitorService (background polling)
  - [x] 5.1 Implement `backend/app/services/feed_monitor.py`
    - Create singleton `FeedMonitorService` class with state: "active" | "paused" | "stopped"
    - Implement `start()` — spawn asyncio tasks per enabled feed with 2-second stagger
    - Implement `pause()` — cancel all polling tasks, retain state
    - Implement `resume()` — restart polling from current time (no reprocessing paused articles)
    - Implement `stop()` — cancel all tasks, reset state
    - Implement `add_feed(config)`, `remove_feed(feed_id)`, `update_feed(config)` for dynamic configuration
    - _Requirements: 9.1, 9.2, 9.3, 10.4_

  - [x] 5.2 Implement the per-feed polling loop in `_poll_feed`
    - Use `httpx.AsyncClient` to fetch RSS feed URL
    - Parse RSS/Atom XML with `feedparser` library
    - Extract title, URL, published date, summary from each entry
    - Handle HTTP errors: increment failure counter, log error, retry next cycle
    - Handle HTTP 429: double `current_polling_interval` (cap at 3600)
    - After 5 consecutive failures: mark feed as "degraded", broadcast WebSocket alert
    - On success after degraded: reset counter, restore original interval
    - On success: call DeduplicationEngine, then PipelineTrigger for new articles
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 10.3_

  - [ ]* 5.3 Write property test for failure counter increment
    - **Property 5: Failure counter monotonic increment**
    - **Validates: Requirements 2.3**

  - [ ]* 5.4 Write property test for HTTP 429 backoff doubling
    - **Property 22: HTTP 429 backoff doubling**
    - **Validates: Requirements 10.3**

  - [ ]* 5.5 Write property test for RSS entry parsing
    - **Property 4: RSS entry parsing extracts all required fields**
    - **Validates: Requirements 2.2**

- [x] 6. WebSocket broadcast channel for live-news
  - [x] 6.1 Implement `LiveNewsBroadcastManager` in `backend/app/ws_manager.py`
    - Add a broadcast channel class managing a list of WebSocket connections (separate from per-job connections)
    - Implement `connect(websocket)`, `disconnect(websocket)`, `broadcast(message)` methods
    - Define message types: feed_status, new_queue_item, breaking_alert, stats_update, monitor_state
    - Export a singleton `live_news_ws` instance
    - _Requirements: 2.4, 5.4, 8.2_

  - [x] 6.2 Add `/ws/live-news` WebSocket endpoint in `backend/app/main.py`
    - Register WebSocket route accepting dashboard client connections
    - Handle connect/disconnect lifecycle with keepalive ping
    - _Requirements: 8.2_

- [x] 7. API routes — Feed CRUD and monitoring lifecycle
  - [x] 7.1 Create `backend/app/api/routes/feeds.py` with feed configuration CRUD endpoints
    - `GET /api/feeds` — list all feed configurations
    - `GET /api/feeds/{id}` — get single feed
    - `POST /api/feeds` — create new feed configuration with validation
    - `PUT /api/feeds/{id}` — update feed configuration; FeedMonitorService picks up changes next cycle
    - `DELETE /api/feeds/{id}` — soft delete (mark disabled, retain ArticleFingerprint history)
    - `POST /api/feeds/{id}/validate` — validate RSS URL is reachable and parseable
    - _Requirements: 1.1, 1.2, 1.3, 1.5_

  - [x] 7.2 Create `backend/app/api/routes/live_news.py` with monitoring lifecycle and dashboard endpoints
    - `POST /api/live-news/start` — activate monitoring (call FeedMonitorService.start())
    - `POST /api/live-news/pause` — pause all polling
    - `POST /api/live-news/resume` — resume polling
    - `POST /api/live-news/stop` — stop monitoring
    - `GET /api/live-news/status` — get current monitor state + aggregate stats
    - `GET /api/live-news/dashboard` — compute and return LiveNewsDashboardStats
    - `GET /api/live-news/queue` — paginated approval queue items sorted by priority then recency
    - `POST /api/live-news/queue/{job_id}/approve` — approve video, handle auto-approve audit log
    - `POST /api/live-news/queue/{job_id}/reject` — reject with reason
    - `GET /api/live-news/feeds/{id}/articles` — recent articles from specific feed
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 8.1, 8.3, 8.4, 9.1, 9.2, 9.3, 9.4_

  - [x] 7.3 Register new routers in `backend/app/main.py`
    - Import and include feeds router with prefix `/api`
    - Import and include live_news router with prefix `/api`
    - Wire FeedMonitorService into the FastAPI lifespan (auto-start if previously active)
    - _Requirements: 9.1_

  - [ ]* 7.4 Write property test for feed configuration round-trip
    - **Property 1: Feed configuration storage round-trip**
    - **Validates: Requirements 1.1**

  - [ ]* 7.5 Write property test for approval state transition
    - **Property 16: Approval state transition**
    - **Validates: Requirements 6.2**

  - [ ]* 7.6 Write property test for rejection state transition
    - **Property 17: Rejection state transition with reason**
    - **Validates: Requirements 6.3**

  - [ ]* 7.7 Write property test for queue sorting
    - **Property 18: Queue sorting — priority then recency**
    - **Validates: Requirements 6.4**

  - [ ]* 7.8 Write property test for auto-approve trusted sources
    - **Property 19: Auto-approve for trusted sources**
    - **Validates: Requirements 6.5, 7.1**

  - [ ]* 7.9 Write property test for auto-approval audit logging
    - **Property 20: Auto-approval audit logging**
    - **Validates: Requirements 7.2**

  - [ ]* 7.10 Write property test for dashboard stats accuracy
    - **Property 21: Dashboard stats accuracy**
    - **Validates: Requirements 8.1**

  - [ ]* 7.11 Write property test for deletion retaining article history
    - **Property 23: Deletion retains article history**
    - **Validates: Requirements 1.3**

- [x] 8. Checkpoint — Backend complete, ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Frontend types and API client
  - [x] 9.1 Add TypeScript types to `frontend/src/types/index.ts`
    - Add `FeedConfiguration` interface
    - Add `LiveNewsDashboardStats` interface
    - Add `QueueItem` interface
    - Add `MonitorState` type alias
    - Add `LiveNewsWSMessage` interface
    - Add `FeedHealthStatus` type
    - _Requirements: 8.1, 8.3_

  - [x] 9.2 Add live-news API functions to `frontend/src/lib/api.ts`
    - `listFeeds()`, `getFeed(id)`, `createFeed(payload)`, `updateFeed(id, payload)`, `deleteFeed(id)`, `validateFeedUrl(id)`
    - `startMonitoring()`, `pauseMonitoring()`, `resumeMonitoring()`, `stopMonitoring()`, `getMonitorStatus()`
    - `getDashboardLiveNews()`, `getApprovalQueue(params)`, `approveQueueItem(jobId)`, `rejectQueueItem(jobId, reason)`, `getFeedArticles(feedId)`
    - `getLiveNewsWebSocketUrl()` helper
    - _Requirements: 8.1, 8.2, 9.4_

- [x] 10. Frontend zustand store
  - [x] 10.1 Create `frontend/src/stores/liveNewsStore.ts`
    - State: monitorState, feeds, dashboardStats, queueItems, wsConnected
    - Actions: setMonitorState, setFeeds, updateFeedStatus, addQueueItem, removeQueueItem, setDashboardStats, setWsConnected
    - WebSocket connection management: connect to `/ws/live-news`, handle message types (feed_status, new_queue_item, breaking_alert, stats_update, monitor_state)
    - Auto-reconnect on disconnect
    - _Requirements: 8.2, 9.4_

- [x] 11. Frontend pages
  - [x] 11.1 Create `frontend/src/pages/LiveNewsDashboard.tsx`
    - Stat cards: total active feeds, degraded feeds, articles detected last hour, videos awaiting review, auto-approved last hour, active jobs
    - Per-feed status list with health indicator, last polled time, article count, next poll time
    - Click-through to feed detail showing recent articles
    - MonitorControls component for start/pause/resume/stop
    - Wire to liveNewsStore and WebSocket for real-time updates
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 9.4_

  - [x] 11.2 Create `frontend/src/pages/ApprovalQueue.tsx`
    - List queue items sorted by priority (high first) then creation time (newest first)
    - Each item shows: article title, source feed, language, priority badge, video preview, timestamp
    - Approve button → calls API, removes from queue
    - Reject button → shows reason input modal, calls API, removes from queue
    - Auto-refreshes via WebSocket new_queue_item messages
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 11.3 Create `frontend/src/pages/FeedConfigPage.tsx`
    - List existing feed configurations in card layout
    - "Add Feed" button → opens FeedForm modal/panel
    - Edit/delete actions on each feed card
    - Show feed health status, enable/disable toggle
    - URL validation feedback on create/edit
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 12. Frontend components
  - [x] 12.1 Create `frontend/src/components/FeedStatusCard.tsx`
    - Display feed name, health indicator (green/yellow/red), last polled timestamp, articles processed count
    - Clickable to show feed detail
    - _Requirements: 8.3_

  - [x] 12.2 Create `frontend/src/components/MonitorControls.tsx`
    - Show current monitor state (active/paused/stopped) with colored badge
    - Start, Pause, Resume, Stop buttons with appropriate disabled states
    - Calls API lifecycle endpoints on click
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [x] 12.3 Create `frontend/src/components/QueueItem.tsx`
    - Display article title, source feed name, language, priority badge, creation time
    - Video preview player (reuse existing VideoPlayer component)
    - Approve and Reject action buttons
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 12.4 Create `frontend/src/components/FeedForm.tsx`
    - Form fields: feed URL, display name, polling interval, language picker, priority keywords, trust level dropdown, auto-approve toggle, enabled toggle
    - Client-side validation: URL format, polling interval >= 60
    - "Validate URL" button that calls `/api/feeds/{id}/validate`
    - Submit handler for create/update modes
    - _Requirements: 1.1, 1.4, 1.5_

  - [x] 12.5 Create `frontend/src/components/BreakingAlert.tsx`
    - Toast/banner notification component for breaking news detection
    - Triggered by WebSocket `breaking_alert` messages
    - Shows article title, source feed, auto-dismiss after 10 seconds
    - _Requirements: 5.4, 8.2_

- [x] 13. Integration and wiring
  - [x] 13.1 Add routes for live-news pages in `frontend/src/App.tsx`
    - Add `/live-news` route → LiveNewsDashboard
    - Add `/live-news/queue` route → ApprovalQueue
    - Add `/live-news/feeds` route → FeedConfigPage
    - _Requirements: 8.1, 6.1_

  - [x] 13.2 Add "Live News" section to sidebar navigation in `frontend/src/components/Sidebar.tsx`
    - Add nav items for Live News Dashboard, Approval Queue, Feed Config
    - Use appropriate icons (Rss, Radio, or similar from lucide-react)
    - _Requirements: 8.1_

  - [x] 13.3 Wire auto-approve policy into pipeline completion
    - In `backend/app/services/feed_monitor.py`, after pipeline reaches `awaiting_review`, check if source feed has `trust_level="trusted"` and `auto_approve=True`
    - If yes, automatically transition to "approved" and log audit entry in job steps
    - Broadcast auto-approval event via WebSocket
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 13.4 Add `feedparser` and `httpx` dependencies to `backend/requirements.txt`
    - Add `feedparser==6.0.11` for RSS/Atom parsing
    - Add `httpx==0.27.0` for async HTTP client (feed fetching)
    - _Requirements: 2.2_

  - [ ]* 13.5 Write property test for queue item completeness
    - **Property 15: Queue item completeness**
    - **Validates: Requirements 6.1**

- [x] 14. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document (23 properties total)
- Unit tests validate specific examples and edge cases
- The backend uses Python (FastAPI, SQLModel, asyncio, Hypothesis for PBT)
- The frontend uses TypeScript (React, zustand, Tailwind CSS, axios)
- The existing `Job` model is reused without schema changes — live_news metadata stored in `brand_data` JSON
