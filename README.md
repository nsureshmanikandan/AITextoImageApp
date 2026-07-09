# VernacularCast

> **AI-powered regional language video newsroom — from article to broadcast-ready video in minutes.**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=flat-square&logo=fastapi&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4o-0078D4?style=flat-square&logo=microsoft-azure&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)

---

## What Is VernacularCast?

VernacularCast is an enterprise-grade AI video generation platform that transforms news articles, YouTube videos, and brand content into broadcast-quality regional Indian language videos. It combines Azure GPT-4o for intelligent script generation and translation, edge-tts for natural Neural voice synthesis, Flux-2 for AI image generation, and FFmpeg for professional video rendering.

The platform supports 5 Indian languages (Tamil, Hindi, Telugu, Kannada, English), multiple video pipelines, and includes an autonomous RSS feed monitoring system for 24/7 automated content generation.

---

## Key Features

### 🎬 Multi-Pipeline Video Generation

| Pipeline | Description |
|----------|-------------|
| **News Article** | Scrape any article URL → GPT-4o regional script → TTS voiceover → branded slideshow video |
| **YouTube Dubbing** | Download video → translate audio → synthesize dubbed voiceover → replace audio track |
| **Brand Ad** | GPT-4o ad script → Flux-2 AI images → Sora-2 cinematic video → animated HTML5 banner |
| **Educational** | Topic → chapter structure → animated slides → optional Sora cinematic intro |
| **Batch Mode** | Process multiple topics sequentially with optional Sora intros |

### 📡 Live Breaking News (Autonomous RSS Monitor)

- **Configurable RSS Feeds** — Add any RSS/Atom feed with per-feed language, polling interval, priority keywords, and trust level
- **24/7 Auto-Polling** — Background asyncio tasks continuously monitor feeds for new articles
- **Smart Deduplication** — URL fingerprinting + title similarity (>90%) prevents duplicate videos
- **Priority Routing** — Articles matching keywords (breaking, urgent, etc.) get processed first
- **Auto-Approve Policy** — Trusted feeds bypass the approval queue for faster publishing
- **Editorial Approval Queue** — Review, approve, or reject auto-generated videos with error visibility
- **Real-Time Dashboard** — WebSocket-powered live stats: active feeds, degraded feeds, articles/hour, queue depth
- **Feed Health Monitoring** — Automatic degradation detection after 5 consecutive failures, HTTP 429 backoff
- **Lifecycle Controls** — Start/Pause/Resume/Stop the entire monitoring system from the UI

### 🌐 Multi-Language Support

| Language | Code | TTS Voice |
|----------|------|-----------|
| Tamil | ta-IN | PallaviNeural |
| Hindi | hi-IN | SwaraNeural |
| Telugu | te-IN | ShrutiNeural |
| Kannada | kn-IN | SapnaNeural |
| English (India) | en-IN | NeerjaNeural |

### 🎨 Video Formats

- **Landscape 16:9** — YouTube, news portals, desktop web
- **Vertical 9:16** — Instagram Reels, YouTube Shorts, WhatsApp Status

### 📊 Quality Scoring

- **Translation Accuracy** — GPT-4o evaluates script faithfulness to source
- **Timing Score** — Measures dubbed audio duration vs. original video length
- **Quality Dashboard** — Per-job quality details on the Review page

### 🔐 Responsible AI

| Safeguard | Implementation |
|-----------|---------------|
| AI Disclosure Watermark | All videos carry "AI Generated \| VernacularCast" overlay |
| Source Citation | Original source URL stored with every job |
| Human Review Gate | Videos held in `awaiting_review` until editor approves |
| Tech Terms Preservation | 200+ technical terms kept in English (never transliterated) |
| Audit Trail | All job state transitions timestamped in steps_json |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Browser Client                          │
│         React 18 + Vite + Tailwind + Framer Motion          │
└───────────────────────┬─────────────────────────────────────┘
                        │ REST /api/*  │  WebSocket /ws/*
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Nginx Reverse Proxy (port 80)                   │
└────────┬──────────────────────────────────┬─────────────────┘
         │                                  │
         ▼                                  ▼
┌────────────────────┐            ┌────────────────────┐
│   FastAPI Backend  │            │  Feed Monitor      │
│   (port 8000)      │            │  (asyncio tasks)   │
│                    │            │                    │
│  • Job CRUD        │            │  • RSS Polling     │
│  • Pipeline        │            │  • Deduplication   │
│  • Live News API   │            │  • Auto-Trigger    │
│  • WebSocket       │            │  • Auto-Approve    │
└────────┬───────────┘            └────────┬───────────┘
         │                                  │
         └──────────────┬───────────────────┘
                        │
     ┌──────────────────┼──────────────────────┐
     ▼                  ▼                      ▼
┌──────────┐    ┌──────────────┐    ┌──────────────────┐
│Azure     │    │  edge-tts    │    │    FFmpeg         │
│GPT-4o    │    │  Neural TTS  │    │  Video Render    │
│Script &  │    │  (free)      │    │  (slideshow,     │
│Translation│    │              │    │   dub, compose)  │
└──────────┘    └──────────────┘    └──────────────────┘
     │                                      │
     ▼                                      ▼
┌──────────┐                    ┌──────────────────────┐
│ Flux-2   │                    │  SQLite + Local FS   │
│ AI Images│                    │  (media + metadata)  │
└──────────┘                    └──────────────────────┘
```

---

## Quick Start

### Prerequisites

| Option | Requirements |
|--------|-------------|
| Docker (recommended) | Docker Desktop 4.x |
| Manual | Python 3.12+, Node 18+, FFmpeg in PATH |

### 1 — Clone & Configure

```bash
git clone https://github.com/nsureshmanikandan/AITextoImageApp.git
cd AITextoImageApp
```

Create a `.env` file in the `backend/` directory:

```env
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_KEY=<your-key>
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-12-01-preview
STORAGE_BACKEND=local
LOCAL_MEDIA_DIR=./media
```

### 2 — Run with Docker

```bash
docker-compose up --build
```

| Service | URL |
|---------|-----|
| App (Nginx) | http://localhost |
| Frontend (direct) | http://localhost:5173 |
| API (direct) | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |

### 3 — Run Manually (no Docker)

**Backend:**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

**Frontend** (new terminal):

```bash
cd frontend
npm install
npm run dev
```

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI resource endpoint | Yes |
| `AZURE_OPENAI_KEY` | Azure OpenAI API key | Yes |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name (default: `gpt-4o`) | Yes |
| `AZURE_OPENAI_API_VERSION` | API version (default: `2024-12-01-preview`) | No |
| `FLUX_API_URL` | Flux-2 image generation API endpoint | No |
| `FLUX_API_KEY` | Flux-2 API key | No |
| `PEXELS_API_KEY` | Pexels stock image fallback | No |
| `STORAGE_BACKEND` | `local` or `azure_blob` | No (default: `local`) |
| `LOCAL_MEDIA_DIR` | Local media output directory | No (default: `./media`) |

> **Demo Mode:** If Azure OpenAI credentials are not configured, the app runs in demo mode with placeholder scripts. TTS and video rendering still work.

---

## API Endpoints

### Jobs

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/jobs` | Create a new video generation job |
| `GET` | `/api/jobs` | List all jobs with status |
| `GET` | `/api/jobs/{id}` | Get job details |
| `POST` | `/api/jobs/{id}/approve` | Approve video for publishing |
| `POST` | `/api/jobs/{id}/reject` | Reject video |
| `DELETE` | `/api/jobs/{id}` | Delete job and media |
| `GET` | `/api/jobs/{id}/video` | Download rendered MP4 |

### Live Breaking News

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/feeds` | List all RSS feed configurations |
| `POST` | `/api/feeds` | Create new feed |
| `PUT` | `/api/feeds/{id}` | Update feed settings |
| `DELETE` | `/api/feeds/{id}` | Disable feed (soft delete) |
| `POST` | `/api/feeds/{id}/validate` | Validate RSS URL |
| `POST` | `/api/live-news/start` | Start feed monitoring |
| `POST` | `/api/live-news/pause` | Pause all polling |
| `POST` | `/api/live-news/resume` | Resume polling |
| `POST` | `/api/live-news/stop` | Stop monitoring |
| `GET` | `/api/live-news/dashboard` | Real-time dashboard stats |
| `GET` | `/api/live-news/queue` | Approval queue (paginated) |
| `POST` | `/api/live-news/queue/{id}/approve` | Approve auto-generated video |
| `POST` | `/api/live-news/queue/{id}/reject` | Reject with reason |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `ws/jobs/{job_id}` | Real-time job progress events |
| `ws/live-news` | Dashboard broadcast (feed status, queue updates, breaking alerts) |

---

## Frontend Pages

| Page | Route | Description |
|------|-------|-------------|
| Dashboard | `/` | Overview stats, weekly chart, recent videos, quick actions |
| Create Video | `/create` | Multi-step wizard: mode → URL/details → language/format → processing |
| Review | `/review/:id` | Video player, script editor, quality scores, approve/reject |
| History | `/history` | Filterable table of all jobs with actions |
| Live Monitor | `/live-news` | Real-time feed health, stat cards, monitor controls |
| Approval Queue | `/live-news/queue` | Review/approve/reject auto-generated videos, error logs |
| Feed Config | `/live-news/feeds` | CRUD interface for RSS feed management |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite 5, TypeScript, Tailwind CSS, Framer Motion, Zustand, Recharts |
| Backend | Python 3.12, FastAPI, SQLModel, asyncio, WebSockets |
| AI Script | Azure OpenAI GPT-4o (translation, script generation, ad copy) |
| Voice | edge-tts (free Microsoft Neural TTS — same voices as Azure Speech) |
| Images | Flux-2 (AI generation), Pexels (stock fallback) |
| Video | Sora-2 (cinematic generation), FFmpeg (slideshow, dub, compose) |
| RSS Parsing | feedparser, httpx (async HTTP) |
| Database | SQLite (WAL mode, busy timeout) |
| Storage | Local filesystem / Azure Blob Storage |
| Containers | Docker, Docker Compose, Nginx |

---

## Project Structure

```
VernacularCast/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app + lifespan + WebSocket
│   │   ├── config.py                  # Settings from .env
│   │   ├── database.py                # SQLModel engine + session
│   │   ├── pipeline.py                # Multi-mode pipeline orchestrator
│   │   ├── ws_manager.py             # WebSocket managers (per-job + broadcast)
│   │   ├── models/
│   │   │   ├── job.py                 # Job table + schemas
│   │   │   ├── feed_configuration.py # RSS feed config table + schemas
│   │   │   └── article_fingerprint.py # Deduplication fingerprints
│   │   ├── services/
│   │   │   ├── scraper.py            # Article extraction (BeautifulSoup)
│   │   │   ├── script_generator.py   # GPT-4o script generation
│   │   │   ├── tts_service.py        # edge-tts Neural voice synthesis
│   │   │   ├── video_renderer.py     # FFmpeg slideshow renderer
│   │   │   ├── youtube_dubber.py     # yt-dlp download + audio dubbing
│   │   │   ├── feed_monitor.py       # Async RSS polling service
│   │   │   ├── dedup_engine.py       # URL/title deduplication
│   │   │   ├── pipeline_trigger.py   # Auto job creation + concurrency
│   │   │   ├── flux_service.py       # Flux-2 AI image generation
│   │   │   ├── pexels_service.py     # Pexels stock image fallback
│   │   │   ├── sora_service.py       # Sora-2 video generation
│   │   │   ├── quality_scorer.py     # Translation + timing scoring
│   │   │   ├── brand_ad_service.py   # Brand ad script generation
│   │   │   ├── educational_service.py # Educational chapter generation
│   │   │   └── stt_service.py        # Azure Speech-to-Text
│   │   └── api/routes/
│   │       ├── jobs.py               # Job CRUD + pipeline endpoints
│   │       ├── feeds.py              # RSS feed configuration CRUD
│   │       ├── live_news.py          # Monitoring lifecycle + dashboard
│   │       └── health.py             # Health check
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx                    # Router + layout
│   │   ├── components/
│   │   │   ├── Sidebar.tsx           # Navigation with Live News section
│   │   │   ├── VideoPlayer.tsx       # Video preview player
│   │   │   ├── ProgressStepper.tsx   # Pipeline progress visualization
│   │   │   ├── MonitorControls.tsx   # Start/Pause/Resume/Stop
│   │   │   ├── FeedStatusCard.tsx    # Feed health indicator
│   │   │   ├── FeedForm.tsx          # Feed CRUD form
│   │   │   ├── QueueItemCard.tsx     # Approval queue item + video/error
│   │   │   └── BreakingAlert.tsx     # Toast notifications
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx         # Main dashboard
│   │   │   ├── CreateVideo.tsx       # Multi-mode video creation
│   │   │   ├── Review.tsx            # Video review + approve/reject
│   │   │   ├── History.tsx           # All jobs table
│   │   │   ├── LiveNewsDashboard.tsx # RSS monitor dashboard
│   │   │   ├── ApprovalQueue.tsx     # Auto-generated video queue
│   │   │   └── FeedConfigPage.tsx    # Feed management
│   │   ├── stores/
│   │   │   ├── jobStore.ts           # Zustand job state
│   │   │   └── liveNewsStore.ts      # Zustand live-news + WebSocket
│   │   ├── lib/
│   │   │   ├── api.ts               # Axios API client (all endpoints)
│   │   │   └── utils.ts             # Formatting helpers
│   │   └── types/
│   │       └── index.ts              # All TypeScript interfaces
│   ├── Dockerfile
│   └── vite.config.ts
├── nginx.conf
├── docker-compose.yml
└── README.md
```

---

## Screenshots

### Dashboard
Real-time production overview with weekly chart, stat cards, and recent videos.

### Live News Monitor
Autonomous RSS monitoring with feed health, stat cards, and lifecycle controls.

### Approval Queue
Review auto-generated videos with error logs, video preview, and approve/reject actions.

### Feed Configuration
CRUD interface for managing RSS sources with health indicators and auto-approve settings.

### Create Video
Multi-step wizard supporting 5 pipeline modes with real-time progress tracking.

---

## Hackathon Context

Built for **GenAI Hackathon 2025** — demonstrating enterprise-ready AI content localization at scale with:

- 🚀 **5 video generation pipelines** (article, YouTube dub, brand ad, educational, batch)
- 📡 **Autonomous 24/7 news monitoring** with RSS feed polling and auto-video generation
- 🌐 **5 Indian languages** with natural Neural TTS voices
- 🎯 **Quality scoring** (translation accuracy + timing sync)
- 🔐 **Responsible AI** (human review gate, AI disclosure, audit trail)
- ⚡ **Real-time WebSocket** progress tracking and dashboard updates
- 🐳 **Production-ready** Docker deployment with Nginx load balancing

---

## License

MIT © 2025 VernacularCast Contributors
