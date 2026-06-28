# AI Image Generation Platform

Generate high-quality images from simple English descriptions. The system enhances your text into optimized prompts using GPT-4o, then generates images via Flux 2.0 Pro.

## Architecture

- **Frontend**: React + TypeScript + Tailwind CSS (Vite)
- **Backend**: Python FastAPI + SQLAlchemy + Celery
- **Database**: PostgreSQL 16
- **Queue**: Redis 7
- **Image Generation**: Flux 2.0 Pro (Azure AI Foundry)
- **Prompt Optimization**: Azure OpenAI GPT-4o

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Azure OpenAI and Flux API credentials (already configured in `.env`)

## Quick Start (Docker)

```bash
# 1. Clone the repo and navigate to the project root
cd C:\Users\n.sureshmanikandan\Repo1\AITextoImageApp

# 2. Start all services (postgres, redis, backend, celery worker, frontend)
docker compose up --build

# 3. Access the application
#    Frontend:  http://localhost:3000
#    Backend API Docs:  http://localhost:8001/docs
#    Backend Health:  http://localhost:8001/api/v1/health
```

> **Note:** Use `docker compose` (with a space). The older `docker-compose` (hyphenated) is deprecated.

## Run Without Docker (Local Development)

### Backend

```bash
# 1. Navigate to backend
cd backend

# 2. Create Python virtual environment (optional but recommended)
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create data directory
mkdir data\images

# 5. Start the FastAPI server (port 8001)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

> No PostgreSQL or Redis needed! Uses SQLite + in-memory task queue for local dev.

### Frontend

```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Start the development server
npm run dev

# 4. Open http://localhost:3000
```

### Access

- **Frontend UI**: http://localhost:3000
- **Backend API Docs (Swagger)**: http://localhost:8001/docs
- **Backend Health Check**: http://localhost:8001/api/v1/health

## Environment Variables

All configuration is in the `.env` file at the project root. Key variables:

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key for GPT-4o |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name (default: gpt-4o) |
| `AZURE_OPENAI_API_VERSION` | API version (default: 2024-12-01-preview) |
| `FLUX_API_URL` | Azure AI Foundry endpoint for Flux 2.0 Pro |
| `FLUX_API_KEY` | Flux API key |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `IMAGE_STORAGE_PATH` | Local path for generated images |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/generate-image` | Submit a prompt for image generation |
| GET | `/api/v1/jobs/{job_id}` | Poll job status |
| POST | `/api/v1/regenerate` | Regenerate with same/edited prompt |
| POST | `/api/v1/refine-prompt` | Save an edited prompt as new version |
| PUT | `/api/v1/prompts/{id}` | Update a prompt version |
| GET | `/api/v1/images/{id}` | Retrieve generated image binary |
| DELETE | `/api/v1/images/{id}` | Delete an image |
| GET | `/api/v1/gallery` | Browse image gallery (paginated) |
| GET | `/api/v1/history` | View prompt history (paginated) |
| POST | `/api/v1/presets` | Create a style preset |
| GET | `/api/v1/presets` | List all presets |
| PUT | `/api/v1/presets/{id}` | Update a preset |
| DELETE | `/api/v1/presets/{id}` | Delete a preset |
| GET | `/api/v1/health` | Readiness check (DB + Redis) |
| GET | `/api/v1/health/liveness` | Liveness check |

## How It Works

1. You type a simple description (e.g., "a futuristic city at night")
2. GPT-4o enhances it into a detailed prompt with style, lighting, composition, quality
3. Flux 2.0 Pro generates the image
4. You see the generated prompt and can edit it
5. Regenerate with edits or request variations with different seeds

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/v1/          # FastAPI route handlers
│   │   ├── generators/      # Image model abstraction (Flux Pro)
│   │   ├── models/          # SQLAlchemy database models
│   │   ├── services/        # Business logic layer
│   │   ├── storage/         # Image storage abstraction
│   │   ├── tasks/           # Celery async tasks
│   │   ├── celery_app.py    # Celery configuration
│   │   ├── config.py        # App settings (Pydantic)
│   │   ├── database.py      # DB engine and sessions
│   │   ├── main.py          # FastAPI app factory
│   │   └── middleware.py    # Request ID + error handling
│   ├── alembic/             # Database migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/             # API client modules
│   │   ├── components/      # Shared components (Layout, ErrorBoundary)
│   │   ├── features/        # Feature modules
│   │   │   ├── prompt/      # PromptInput, PromptEditor, DiffView, GeneratePage
│   │   │   ├── gallery/     # ImageGallery, ImageGrid, ImageCard
│   │   │   ├── generation/  # GenerationStatus (polling/loading)
│   │   │   ├── history/     # PromptHistory
│   │   │   └── presets/     # PresetManager
│   │   ├── hooks/           # React Query hooks
│   │   └── types/           # TypeScript interfaces
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml        # Full local development stack
├── docker-compose.test.yml   # Isolated test databases
├── .env                      # Environment variables
└── README.md
```

## Stopping the Application

```bash
# Stop all containers
docker compose down

# Stop and remove volumes (deletes database and images)
docker compose down -v
```

## Troubleshooting

- **Port already in use**: Stop other services on ports 3000, 8000, 5432, or 6379
- **Docker build fails**: Ensure Docker Desktop is running and has enough resources
- **Celery not processing**: Check Redis is healthy with `docker-compose logs redis`
- **Images not generating**: Verify your Flux API credentials in `.env`
- **Database errors**: Run `docker-compose down -v` to reset, then `docker-compose up --build`
