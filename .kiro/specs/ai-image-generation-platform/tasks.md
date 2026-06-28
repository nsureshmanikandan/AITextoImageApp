# Implementation Plan: AI Image Generation Platform

## Overview

This plan implements the AI Image Generation Platform as a full-stack application with a Python FastAPI backend, React + TypeScript frontend, Celery workers for async image generation, and PostgreSQL for persistence. Tasks are ordered to build foundational layers first (project structure, database, core abstractions) then progressively wire in services, API endpoints, frontend components, and observability.

## Tasks

- [x] 1. Set up backend project structure and dependencies
  - [x] 1.1 Initialize Python project with FastAPI, Celery, SQLAlchemy, and testing dependencies
    - Create `backend/` directory with `pyproject.toml` or `requirements.txt`
    - Include: fastapi, uvicorn, celery[redis], sqlalchemy[asyncio], asyncpg, pydantic, httpx, python-dotenv, alembic
    - Include dev deps: pytest, pytest-asyncio, hypothesis, httpx (for test client)
    - Create `backend/app/__init__.py`, `backend/app/main.py` with FastAPI app factory
    - Set up environment variable loading from `.env` file
    - _Requirements: 13.2, 10.4_

  - [x] 1.2 Configure Alembic for database migrations
    - Initialize Alembic in `backend/alembic/`
    - Configure `alembic.ini` and `env.py` to use async SQLAlchemy engine
    - Ensure migration scripts use the database URL from environment variables
    - _Requirements: 13.3_

  - [x] 1.3 Set up project configuration module
    - Create `backend/app/config.py` with Pydantic Settings class
    - Include settings for: database URL, Redis URL, Azure OpenAI endpoint/key, Azure AI Foundry endpoint/key, image storage path, allowed model name
    - Support environment-based overrides
    - _Requirements: 13.2, 15.3_

- [x] 2. Set up frontend project structure and dependencies
  - [x] 2.1 Initialize React + TypeScript project with Vite
    - Create `frontend/` directory using Vite with React + TypeScript template
    - Install dependencies: react-query (@tanstack/react-query), axios, react-router-dom, tailwindcss (or CSS framework of choice)
    - Install dev deps: vitest, @testing-library/react, @testing-library/jest-dom, @testing-library/user-event
    - Set up path aliases and base configuration
    - _Requirements: 14.1, 14.2_

  - [x] 2.2 Configure frontend folder structure and base layout
    - Create feature-based folder structure: `src/features/`, `src/components/`, `src/api/`, `src/hooks/`, `src/types/`
    - Create base `Layout` component with responsive shell (sidebar + main content area)
    - Set up React Query provider and error boundary wrapper
    - Configure API base URL from environment variable
    - _Requirements: 14.1, 14.4, 14.5_

- [x] 3. Implement database models and initial migration
  - [x] 3.1 Create SQLAlchemy models
    - Create `backend/app/models/` package with: `prompt_input.py`, `prompt_version.py`, `job.py`, `image_metadata.py`, `preset.py`
    - Implement all models as defined in the design (PromptInput, PromptVersion, Job, ImageMetadata, Preset)
    - Include relationships, indexes, and constraints (e.g., JSONB for params/result, UUID primary keys)
    - _Requirements: 2.5, 3.3, 6.1, 8.2, 11.1_

  - [x] 3.2 Generate and apply initial Alembic migration
    - Auto-generate migration from models
    - Verify migration creates all tables with correct columns, types, foreign keys, and indexes
    - _Requirements: 13.3_

  - [ ]* 3.3 Write property tests for data models
    - **Property 3: Prompt Versioning Integrity** — verify version_number strictly increments, timestamps are non-decreasing, and source is correctly set for any sequence of operations
    - **Validates: Requirements 2.5, 4.3, 4.5, 6.1**

- [x] 4. Implement model abstraction layer and storage backend
  - [x] 4.1 Create image generator abstraction
    - Create `backend/app/generators/__init__.py` with `ImageGeneratorBase` ABC, `GenerationRequest`, and `GenerationResult` dataclasses
    - Implement `FluxProGenerator` class that calls Azure AI Foundry REST API for Flux 2.0 Pro
    - Include error handling for service unavailability and timeouts
    - Implement factory function to instantiate the active generator from config
    - _Requirements: 15.1, 15.2, 15.3, 15.4_

  - [x] 4.2 Create storage backend abstraction
    - Create `backend/app/storage/__init__.py` with `StorageBackend` ABC (store, retrieve, delete methods)
    - Implement `LocalFilesystemStorage` with path pattern `/data/images/{YYYY}/{MM}/{image_id}.png`
    - Include directory creation and error handling
    - Implement factory function to instantiate storage from config
    - _Requirements: 9.4, 13.4_

  - [ ]* 4.3 Write property test for model abstraction interface conformance
    - **Property 17: Model Abstraction Interface Conformance** — verify any valid GenerationRequest is accepted and returns a valid GenerationResult with all required fields
    - **Validates: Requirements 15.4**

- [x] 5. Implement core backend services
  - [x] 5.1 Implement PromptService
    - Create `backend/app/services/prompt_service.py`
    - Implement `optimize_prompt()`: call Azure OpenAI GPT-4o to enhance user input into a detailed prompt with negative prompt; apply preset parameters if provided
    - Implement `create_version()`: create a new PromptVersion record with auto-incrementing version number
    - Implement `get_history()`: paginated query with date range and search term filters, ordered by created_at DESC
    - Implement `get_version()`: retrieve a specific prompt version by ID
    - Include retry logic (3 retries, exponential backoff) for GPT-4o calls
    - _Requirements: 2.1, 2.2, 2.3, 2.5, 2.6, 4.3, 6.1, 6.2, 8.3_

  - [x] 5.2 Implement ImageService
    - Create `backend/app/services/image_service.py`
    - Implement `generate()`: enqueue Celery tasks with unique seeds per variation
    - Implement `store_image()`: save binary to storage backend and create ImageMetadata record
    - Implement `get_image()`: retrieve image binary from storage by ID
    - Implement `delete_image()`: soft-delete (set is_deleted, deleted_at, remove from storage)
    - _Requirements: 3.1, 3.3, 7.2, 9.2, 9.5_

  - [x] 5.3 Implement JobService
    - Create `backend/app/services/job_service.py`
    - Implement `create_job()`: create job record with status "queued"
    - Implement `update_status()`: transition job status and set result/completed_at as appropriate
    - Implement `get_job()`: retrieve job with results
    - Implement `get_user_jobs()`: list jobs with optional status filter
    - Implement `timeout_stale_jobs()`: mark processing jobs older than 5 minutes as timed_out
    - _Requirements: 11.1, 11.3, 11.4, 11.5_

  - [x] 5.4 Implement PresetService
    - Create `backend/app/services/preset_service.py`
    - Implement CRUD operations: create, update, delete, list
    - Enforce maximum 20 presets limit on create
    - _Requirements: 8.2, 8.4_

  - [ ]* 5.5 Write property tests for core services
    - **Property 4: History Pagination Ordering** — verify paginated results are always ordered by created_at DESC with correct total count and page_size limits
    - **Property 10: Preset Persistence Round-Trip** — verify saving and retrieving a preset returns matching field values
    - **Property 11: Preset Limit Enforcement** — verify that a 21st preset creation is rejected when 20 exist
    - **Property 14: Job Lifecycle State Management** — verify completed jobs have non-null completed_at and accessible results
    - **Property 15: Job Timeout Enforcement** — verify jobs processing > 5 min are marked timed_out, and those within 5 min are not
    - **Validates: Requirements 6.2, 8.2, 8.4, 11.3, 11.4**

- [x] 6. Checkpoint - Backend services validation
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement Celery worker tasks
  - [x] 7.1 Configure Celery application
    - Create `backend/app/celery_app.py` with Celery instance configured to use Redis as broker and result backend
    - Set up task autodiscovery for `backend/app/tasks/`
    - Configure task serialization (JSON), result expiration, and concurrency settings
    - _Requirements: 11.1, 13.2_

  - [x] 7.2 Implement image generation task
    - Create `backend/app/tasks/generate_image.py`
    - Implement `generate_image_task`: retrieve prompt version → call image generator → store image → update job status
    - Handle failures: update job status to "failed", log error with full context (prompt_version_id, job_id, error details)
    - Support retries (max 2 with exponential backoff for transient errors)
    - _Requirements: 3.1, 3.2, 3.3, 3.5, 11.1_

  - [x] 7.3 Implement prompt optimization task
    - Create `backend/app/tasks/optimize_prompt.py`
    - Implement `optimize_prompt_task`: call GPT-4o for optimization → store prompt version → enqueue generation task(s) with unique seeds
    - Handle preset application: merge preset parameters into the optimization call
    - Retry up to 3 times with exponential backoff on failure
    - _Requirements: 2.1, 2.3, 2.6, 7.2, 8.3_

  - [ ]* 7.4 Write property tests for worker tasks
    - **Property 5: Image Storage Dual-Write Consistency** — verify successful generation creates both a storage file and a matching ImageMetadata record
    - **Property 8: Multi-Variation Unique Seeds** — verify N variations produce exactly N tasks with distinct seeds
    - **Property 9: Partial Failure Preserves Successes** — verify successful results are preserved when some variations fail
    - **Validates: Requirements 3.3, 7.2, 7.4**

- [x] 8. Implement API endpoints
  - [x] 8.1 Implement generate-image endpoint
    - Create `backend/app/api/v1/generate.py` with `POST /api/v1/generate-image`
    - Validate request body (prompt 1-2000 chars, num_variations 1-4, optional preset_id)
    - Create job record, enqueue optimization + generation pipeline
    - Return 202 Accepted with job_id
    - _Requirements: 1.3, 1.4, 3.2, 10.1, 10.2_

  - [x] 8.2 Implement job status endpoint
    - Create `backend/app/api/v1/jobs.py` with `GET /api/v1/jobs/{job_id}`
    - Return job status, results (if completed), and error details (if failed)
    - Include proper 404 handling for unknown job IDs
    - _Requirements: 3.4, 11.3, 11.5_

  - [x] 8.3 Implement history endpoint
    - Create `backend/app/api/v1/history.py` with `GET /api/v1/history`
    - Accept query params: page, page_size, date_from, date_to, search
    - Return paginated results with total count
    - _Requirements: 6.2, 6.3, 10.5_

  - [x] 8.4 Implement regenerate endpoint
    - Create `backend/app/api/v1/regenerate.py` with `POST /api/v1/regenerate`
    - Accept image_id and optional edited_prompt
    - If edited_prompt provided: create new version, generate with new prompt
    - If no edited_prompt: regenerate with same prompt but different seed
    - _Requirements: 5.1, 5.3, 5.5, 10.5_

  - [x] 8.5 Implement prompt refinement and image retrieval endpoints
    - Create `POST /api/v1/refine-prompt` — save edited prompt as new version
    - Create `GET /api/v1/images/{id}` — return image binary with caching headers (Cache-Control, ETag)
    - Create `PUT /api/v1/prompts/{id}` — update prompt text and create version
    - _Requirements: 4.3, 9.2, 10.5_

  - [x] 8.6 Implement preset CRUD endpoints
    - Create `backend/app/api/v1/presets.py` with full CRUD: POST, GET (list), PUT, DELETE
    - Enforce 20-preset limit on POST
    - Validate preset fields (name 1-100 chars)
    - _Requirements: 8.2, 8.4, 10.5_

  - [x] 8.7 Implement health check endpoint
    - Create `GET /api/v1/health` returning service status, database connectivity, Redis connectivity
    - Implement liveness probe (simple 200 OK) and readiness probe (checks DB + Redis)
    - _Requirements: 13.5_

  - [x] 8.8 Configure error handling middleware and request ID injection
    - Create middleware that generates a unique request_id for each request
    - Implement global exception handler returning consistent error structure: {error_code, message, request_id}
    - Map specific exceptions to appropriate HTTP status codes per error table in design
    - _Requirements: 10.3, 12.4_

  - [ ]* 8.9 Write property tests for API validation
    - **Property 1: Request Validation Rejects Invalid Payloads** — verify invalid requests (empty prompt, > 2000 chars, num_variations outside 1-4) return 422 with no side effects
    - **Property 2: Error Response Structure Consistency** — verify all error responses contain error_code, message, and request_id
    - **Validates: Requirements 1.3, 1.4, 7.1, 10.2, 10.3**

- [x] 9. Checkpoint - Backend API validation
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implement frontend API client and shared types
  - [x] 10.1 Create TypeScript types and API client
    - Create `frontend/src/types/` with interfaces: GenerateImageParams, JobStatus, ImageResult, PromptVersion, Preset, ErrorResponse, PaginatedResponse
    - Create `frontend/src/api/client.ts` with axios instance (base URL, error interceptor, request ID header)
    - Create API service modules: `generateApi.ts`, `jobsApi.ts`, `historyApi.ts`, `presetsApi.ts`, `imagesApi.ts`
    - _Requirements: 10.1, 14.2_

  - [x] 10.2 Create React Query hooks
    - Create `frontend/src/hooks/` with custom hooks for each API operation
    - Implement `useGenerateImage` mutation, `useJobStatus` polling query (2s interval, stops on completion/failure), `useHistory` paginated query, `usePresets` CRUD hooks
    - Configure stale time, cache time, and background refetching
    - _Requirements: 11.2, 14.2_

- [x] 11. Implement frontend prompt input and generation flow
  - [x] 11.1 Build PromptInput component
    - Create `frontend/src/features/prompt/PromptInput.tsx`
    - Text input field with character counter (max 2000), submit button, loading state
    - Variation count selector (1-4)
    - Preset selector dropdown
    - Client-side validation with inline error messages
    - Keyboard accessibility (submit on Enter/Ctrl+Enter)
    - _Requirements: 1.1, 1.5, 7.1, 8.5, 14.3_

  - [x] 11.2 Build job status polling and loading indicator
    - Create `frontend/src/features/generation/GenerationStatus.tsx`
    - Display loading spinner/progress while job is queued/processing
    - Show elapsed time
    - Auto-transition to result display on completion
    - Show error message with retry button on failure/timeout
    - _Requirements: 1.5, 3.4, 11.2, 14.6_

  - [ ]* 11.3 Write unit tests for prompt input component
    - Test input validation (empty, max length), submission flow, loading state transitions, accessibility attributes
    - _Requirements: 1.1, 1.5, 14.3_

- [x] 12. Implement frontend prompt editor and diff view
  - [x] 12.1 Build PromptEditor component
    - Create `frontend/src/features/prompt/PromptEditor.tsx`
    - Editable text area displaying the generated prompt
    - Save button to persist edits (creates new version)
    - Regenerate button to resubmit edited prompt
    - Character count and validation
    - _Requirements: 4.1, 4.2, 5.1_

  - [x] 12.2 Build PromptDiffView component
    - Create `frontend/src/features/prompt/PromptDiffView.tsx`
    - Display visual diff between current and previous prompt versions
    - Highlight additions and deletions
    - Toggle between diff view and plain text view
    - _Requirements: 4.4_

  - [ ]* 12.3 Write unit tests for prompt editor
    - Test edit flow, save action, diff rendering, accessibility
    - _Requirements: 4.1, 4.2, 4.4_

- [x] 13. Implement frontend image gallery
  - [x] 13.1 Build ImageGallery and ImageGrid components
    - Create `frontend/src/features/gallery/ImageGallery.tsx` and `ImageGrid.tsx`
    - Paginated grid layout for generated images
    - Filter controls: date range picker, search input, parameter filters
    - Responsive grid (1-4 columns based on viewport)
    - Lazy loading for images
    - _Requirements: 9.1, 9.3, 14.5_

  - [x] 13.2 Build ImageCard component with actions
    - Create `frontend/src/features/gallery/ImageCard.tsx`
    - Display thumbnail with metadata overlay (date, model, seed)
    - Action buttons: regenerate, delete, view full size, view prompt
    - Confirmation dialog for delete action
    - Side-by-side comparison when viewing regenerated images
    - _Requirements: 5.2, 5.4, 9.5_

  - [ ]* 13.3 Write unit tests for gallery components
    - Test grid rendering, filtering, pagination, delete confirmation, accessibility
    - _Requirements: 9.1, 9.3, 9.5_

- [x] 14. Implement frontend history and presets
  - [x] 14.1 Build PromptHistory component
    - Create `frontend/src/features/history/PromptHistory.tsx`
    - Paginated list of past prompts ordered by date DESC
    - Filter by date range and search term
    - Click to load prompt into editor for reuse
    - Display version count and most recent generated image thumbnail
    - _Requirements: 6.2, 6.3, 6.4_

  - [x] 14.2 Build PresetManager component
    - Create `frontend/src/features/presets/PresetManager.tsx`
    - List existing presets with edit/delete actions
    - Create preset form with fields: name, style, lighting, composition, quality, negative prompt
    - Display count indicator (X/20 presets used)
    - Selectable preset cards in prompt input area
    - _Requirements: 8.1, 8.4, 8.5_

  - [ ]* 14.3 Write unit tests for history and preset components
    - Test pagination, filtering, preset CRUD interactions, limit display, accessibility
    - _Requirements: 6.2, 6.3, 8.1, 8.4_

- [x] 15. Checkpoint - Frontend components validation
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 16. Implement observability
  - [ ] 16.1 Set up structured logging
    - Create `backend/app/logging_config.py` with JSON-formatted structured logging
    - Include request_id, timestamp, severity level in all log entries
    - Configure log levels per environment (DEBUG for dev, INFO for prod)
    - Add correlation ID propagation through service calls and Celery tasks
    - _Requirements: 12.1, 12.4_

  - [ ] 16.2 Set up metrics and tracing
    - Integrate OpenTelemetry SDK for distributed tracing
    - Create Prometheus metrics: request_count, request_latency_seconds, error_rate, celery_queue_depth
    - Expose metrics endpoint at `/metrics`
    - Instrument FastAPI routes, Celery tasks, and external HTTP calls
    - _Requirements: 12.2, 12.3_

  - [ ]* 16.3 Write property test for log correlation
    - **Property 16: Log Correlation ID Consistency** — verify all log entries from a single request share the same correlation/request_id
    - **Validates: Requirements 12.4**

- [ ] 17. Implement remaining property tests
  - [ ]* 17.1 Write property test for regeneration linking
    - **Property 6: Regeneration Image-to-Version Linking** — verify ImageMetadata.prompt_version_id points to the exact version used for regeneration
    - **Validates: Requirements 5.3**

  - [ ]* 17.2 Write property test for regeneration seed variation
    - **Property 7: Regeneration Seed Variation** — verify regeneration without edit uses same prompt text but different seed
    - **Validates: Requirements 5.5**

  - [ ]* 17.3 Write property test for image deletion completeness
    - **Property 13: Image Deletion Completeness** — verify deletion removes storage file and sets is_deleted + deleted_at, and image is excluded from queries
    - **Validates: Requirements 9.5**

  - [ ]* 17.4 Write property test for gallery filtering
    - **Property 12: Gallery Filtering Correctness** — verify filtered results contain only images matching ALL criteria with no omissions
    - **Validates: Requirements 9.3**

- [x] 18. Docker containerization and orchestration
  - [x] 18.1 Create backend Dockerfile
    - Multi-stage build: install dependencies → copy app → run with uvicorn
    - Include health check instruction
    - Set proper user permissions (non-root)
    - _Requirements: 13.1_

  - [x] 18.2 Create frontend Dockerfile
    - Multi-stage build: install deps → build static assets → serve with nginx
    - Configure nginx for SPA routing (fallback to index.html)
    - _Requirements: 13.1_

  - [x] 18.3 Create docker-compose.yml for local development
    - Services: backend, frontend, celery-worker, postgres, redis
    - Volume mounts for code hot-reload in development
    - Environment variable configuration via `.env` file
    - Health checks and dependency ordering
    - Expose ports: frontend (3000), backend (8000), postgres (5432), redis (6379)
    - _Requirements: 13.1, 13.2, 13.3, 13.5_

  - [x] 18.4 Create docker-compose.test.yml for test environment
    - Services: test-db (postgres), test-redis
    - Isolated from development data
    - Used by CI and local test runs
    - _Requirements: 13.1_

- [x] 19. Final checkpoint - Full integration validation
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP delivery
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at logical boundaries
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The backend uses Python (FastAPI, SQLAlchemy, Celery, Hypothesis) and the frontend uses TypeScript (React, React Query, Vitest)
- No authentication is implemented in this phase — all data is treated as single-user
- Local filesystem storage is used for MVP; the StorageBackend abstraction enables future cloud migration
