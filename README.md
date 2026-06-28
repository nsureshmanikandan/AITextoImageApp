# VernacularCast

> **AI-powered multilingual podcast & narration platform — your content, every language, every voice.**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=flat-square&logo=fastapi&logoColor=white)
![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4o-0078D4?style=flat-square&logo=microsoft-azure&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)

---

## What Is VernacularCast?

VernacularCast is an enterprise-grade AI narration and localization pipeline that transforms long-form content — articles, reports, scripts — into broadcast-quality multilingual audio. It leverages Azure GPT-4o for context-aware translation and script adaptation, Azure Neural TTS for natural-sounding voice synthesis, and FFmpeg for professional audio mastering. Every generated asset carries a responsible-AI disclosure watermark, and a human-review gate ensures editorial quality before distribution.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Browser Client                      │
│              React 18 + Vite + Tailwind CSS              │
└───────────────────────┬─────────────────────────────────┘
                        │ REST /api/*  │  WebSocket /ws/*
                        ▼
┌─────────────────────────────────────────────────────────┐
│              Nginx Reverse Proxy (port 80)               │
│          Load-balances across 2 FastAPI replicas         │
└────────┬──────────────────────────────┬─────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────┐            ┌─────────────────┐
│  FastAPI        │            │  FastAPI        │
│  Replica 1      │            │  Replica 2      │
│  (port 8000)    │            │  (port 8000)    │
└────────┬────────┘            └────────┬────────┘
         │                              │
         └──────────────┬───────────────┘
                        │
          ┌─────────────┼─────────────────┐
          ▼             ▼                 ▼
  ┌──────────────┐ ┌──────────┐ ┌──────────────────┐
  │ Azure GPT-4o │ │Azure TTS │ │     FFmpeg        │
  │ Translation  │ │  Voice   │ │  Audio Mastering  │
  │ & Script     │ │Synthesis │ │  (normalize,      │
  │ Adaptation   │ │(Neural)  │ │   compress, tag)  │
  └──────────────┘ └──────────┘ └──────────────────┘
          │                              │
          └──────────────┬───────────────┘
                         ▼
              ┌──────────────────────┐
              │  SQLite / Azure Blob │
              │  (media + metadata)  │
              └──────────────────────┘
```

---

## Quick Start

### Prerequisites

| Option | Requirements |
|--------|-------------|
| Docker (recommended) | Docker Desktop 4.x |
| Manual | Python 3.12, Node 18+, `ffmpeg` in PATH |

### 1 — Clone & Configure

```bash
git clone https://github.com/your-org/vernacularcast.git
cd vernacularcast

# Copy the placeholder env file
cp .env .env.local     # or just edit .env directly for the hackathon
```

Open `.env` and fill in your Azure credentials:

```
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_KEY=<your-key>
AZURE_SPEECH_KEY=<your-speech-key>
AZURE_SPEECH_REGION=eastus
```

### 2 — Run with Docker (recommended)

```bash
docker-compose up --build
```

| Service  | URL                        |
|----------|----------------------------|
| App (via Nginx) | http://localhost       |
| Frontend (direct) | http://localhost:5173 |
| API (direct)      | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

### 3 — Run Manually (no Docker)

**Backend**

```bash
cd backend
python -m venv .venv
cd C:\Users\n.sureshmanikandan\Repo1\VernacularCast\backend
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend** (new terminal)

```bash
cd frontend
npm install
npm run dev          # starts on http://localhost:5173
```

> **ffmpeg** must be installed and on `PATH`. On macOS: `brew install ffmpeg`. On Ubuntu: `sudo apt install ffmpeg`. On Windows: [ffmpeg.org/download.html](https://ffmpeg.org/download.html).

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI resource endpoint URL | Yes |
| `AZURE_OPENAI_KEY` | Azure OpenAI API key | Yes |
| `AZURE_OPENAI_DEPLOYMENT` | Deployment name (default: `gpt-4o`) | Yes |
| `AZURE_SPEECH_KEY` | Azure Cognitive Services Speech key | Yes |
| `AZURE_SPEECH_REGION` | Azure region for Speech (e.g. `eastus`) | Yes |
| `STORAGE_BACKEND` | `local` or `azure_blob` | No (default: `local`) |
| `LOCAL_MEDIA_DIR` | Path to local media directory | No (default: `./media`) |
| `AZURE_BLOB_CONNECTION_STRING` | Azure Blob Storage connection string | Only if `STORAGE_BACKEND=azure_blob` |
| `AZURE_BLOB_CONTAINER` | Blob container name | Only if `STORAGE_BACKEND=azure_blob` |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check — returns `{"status": "ok"}` |
| `GET` | `/docs` | Interactive Swagger UI (FastAPI auto-generated) |
| `POST` | `/api/jobs` | Submit a new transcription/translation job |
| `GET` | `/api/jobs` | List all jobs with status |
| `GET` | `/api/jobs/{job_id}` | Get status and metadata for a specific job |
| `DELETE` | `/api/jobs/{job_id}` | Cancel or delete a job |
| `GET` | `/api/jobs/{job_id}/audio` | Download the generated audio file |
| `POST` | `/api/jobs/{job_id}/review` | Submit human-review decision (approve/reject) |
| `GET` | `/api/languages` | List supported target languages |
| `GET` | `/api/voices` | List available Azure Neural TTS voices |
| `WS` | `/ws/jobs/{job_id}` | WebSocket stream for real-time job progress events |

---

## Responsible AI

VernacularCast is designed with responsible AI principles embedded at every layer:

| Safeguard | Implementation |
|-----------|---------------|
| **Disclosure Watermark** | All AI-generated audio files are tagged with ID3/XMP metadata identifying them as AI-synthesised content |
| **Source Citation** | Original source text and translation provenance are stored alongside every generated asset |
| **Human Review Gate** | Jobs are held in `PENDING_REVIEW` state until an editor approves via `/api/jobs/{id}/review` — no auto-publish |
| **Azure Content Safety** | Input text is screened through Azure Content Safety before translation begins |
| **Audit Trail** | All job state transitions are timestamped and stored in SQLite for full traceability |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite 5, TypeScript, Tailwind CSS 3 |
| Backend | Python 3.12, FastAPI 0.110, Uvicorn |
| AI Translation | Azure OpenAI GPT-4o |
| Voice Synthesis | Azure Cognitive Services Neural TTS |
| Audio Processing | FFmpeg (normalize, compress, metadata tagging) |
| Database | SQLite (dev/hackathon) → PostgreSQL (production path) |
| Storage | Local filesystem / Azure Blob Storage |
| Containerisation | Docker, Docker Compose, Nginx |
| CI/CD | GitHub Actions (lint → test → build → push) |

---

## Project Structure

```
VernacularCast/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app + router registration
│   │   ├── models.py        # SQLAlchemy ORM models
│   │   ├── schemas.py       # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── translation.py   # Azure OpenAI integration
│   │   │   ├── tts.py           # Azure Speech SDK integration
│   │   │   ├── audio.py         # FFmpeg processing pipeline
│   │   │   └── storage.py       # Local / Blob storage abstraction
│   │   └── routers/
│   │       ├── jobs.py
│   │       ├── languages.py
│   │       └── websocket.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Route-level page components
│   │   ├── hooks/           # Custom React hooks (useWebSocket, useJob)
│   │   ├── api/             # Typed API client (fetch wrappers)
│   │   └── main.tsx
│   ├── Dockerfile
│   ├── nginx-frontend.conf
│   └── vite.config.ts
├── nginx.conf               # Production reverse proxy + load balancer
├── docker-compose.yml
├── .env                     # Placeholder credentials (safe to commit)
└── .vscode/
    ├── extensions.json
    └── settings.json
```

---

## Hackathon Context

Built for **[Hackathon Name] 2025** — demonstrating enterprise-ready AI localization at scale, with responsible AI guardrails, production-grade containerisation, and a clean developer experience out of the box.

---

## License

MIT © 2025 VernacularCast Contributors
