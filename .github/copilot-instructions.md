# SCI Platform - AI Coding Agent Instructions

## Architecture Overview

**Full-Stack Scientific Data Management Platform**: FastAPI backend + Vue 3 (Vben Admin) frontend for neuroscience research data analysis, with a focus on fluorescence signal processing.

```
Backend (FastAPI)          Frontend (Vue 3 + Vben)
├── Routers (API layer)    ├── Views (pages)
├── Services (business)    ├── Store (Pinia state)
├── Models (SQLAlchemy)    ├── API clients
├── Schemas (Pydantic)     └── Router (dynamic menu)
└── Utils + Algorithms
```

### Critical Design Patterns

**1. Unified Response Wrapper** (Backend)
- ALL JSON responses wrapped as `{code: 0, data: {...}, message: ""}` via `WrapResponseMiddleware` in `backend/app/main.py`
- Success: `code: 0`, Error: `code: HTTP_STATUS`
- Non-JSON responses (file downloads) bypass wrapper
- Docs/OpenAPI endpoints excluded from wrapping

**2. JWT Authentication Flow**
- Token creation/verification: `backend/app/services/auth_service.py`
- Frontend auto-refresh: `frontend/apps/web-antd/src/api/request.ts` → `authenticateResponseInterceptor`
- Access dependency: `backend/app/dependencies/auth.py::require_access_token`
- Roles stored as JSON string in `User.roles` (e.g., `'["admin","researcher"]'`)

**3. Tag-Based Data Selection**
- `backend/app/utils/tag_selector.py` provides AND/OR logic for filtering DataItems by tags
- Pattern: `{"and": [tagId1, tagId2], "or": [tagId3]}` means (tag1 AND tag2) OR (tag3 OR tag4)
- Used extensively in fluorescence analysis data selection

## Development Workflow

### Quick Start
```bash
# Start both services (VS Code task "Start Frontend and Backend")
# OR manually:

# Backend (from /backend):
uvicorn app.main:app --reload --port 8000

# Frontend (from /frontend):
pnpm dev:antd  # Runs on Vite dev server
```

### Database Setup
- MySQL database auto-created on startup via `backend/app/database.py`
- Schema defined in `backend/sql.sql` and SQLAlchemy models in `backend/app/models/`
- Default admin user: `admin` / `wtq123456` (password hash in sql.sql)
- **Required env vars**: `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `JWT_SECRET`

### Testing
- Backend: No test framework currently configured (manual testing via `/docs` Swagger UI)
- Frontend: Playwright configured in `frontend/playground/playwright.config.ts`

## Key Subsystems

### Fluorescence Analysis Pipeline
**Multi-stage wizard workflow** spanning upload → configuration → analysis → results visualization.

**Backend**: `backend/app/routers/fluorescence.py` + `backend/app/services/fluorescence_service.py`
- CSV preview: `/api/fluorescence/preview` (reads first N rows)
- Analysis submission: `/api/fluorescence/analyze` → returns `jobId`
- Job polling: `/api/fluorescence/{projectId}/jobs/{jobId}/status`
- Results retrieval: `/api/fluorescence/{projectId}/jobs/{jobId}/results`

**Frontend State Management** (Pinia stores in `frontend/apps/web-antd/src/store/fluorescence/`):
- `upload.ts`: File upload state
- `params.ts`: Analysis parameters (event types, time windows, normalization)
- `jobs.ts`: Job polling with 2s intervals, auto-stops on success/failure
- `results.ts`: Matrix/curve results cache
- `masks.ts`: Label mapping for behavior events

**Analysis Algorithm Contract** (`backend/app/services/algorithms/fluorescence_algo.py`):
- Single-event: Align signals to one event type (e.g., reward delivery)
- Multi-event: Time-warp across multiple consecutive trials
- Expected input: `Dataset` with fluorescence CSV + label CSV pairs
- Returns: `AnalysisResult` with matrices (trial × timepoints) and metadata

### Job Registry Pattern
**In-memory task tracking** with optional JSON persistence (`backend/app/services/job_registry.py`):
- Singleton pattern: `job_registry = JobRegistry()`
- States: `QUEUED` → `RUNNING` → `SUCCEEDED`/`FAILED`
- Progress tracking: 0-100 percentage
- Used for long-running fluorescence analyses (background tasks)

### File Storage Structure
```
backend/uploads/
└── {projectId}/
    └── {dataItemId}/
        ├── fluorescence_data.csv
        └── label_data.csv
```
- Managed via `backend/app/routers/files.py`
- `DataItem` model stores `filePath`, `fileName`, `fileType`, `dataType` (raw/processed/result)

## Project-Specific Conventions

### Backend Patterns

**1. Service Layer Functions** (not classes)
- Functions named as `{verb}_{entity}` (e.g., `create_project`, `get_user_by_username`)
- No class-based services—all stateless functions taking `db: Session` as first param
- Example: `backend/app/services/project_service.py`

**2. Router Structure**
```python
router = APIRouter(
    prefix="/entity",
    tags=["entity"],
    dependencies=[Depends(require_access_token)]  # Applied to ALL routes
)

@router.get("/{id}", response_model=EntitySchema)
def get_entity(id: int, db: Session = Depends(get_db)):
    # Service call
    return entity_service.get_entity(db, id)
```

**3. Schema Validation** (Pydantic V2)
- Request: `*CreateRequest`, `*UpdateRequest`
- Response: `*Response` with `model_config = ConfigDict(from_attributes=True)`
- No `orm_mode`—use `from_attributes=True` for ORM conversion

### Frontend Patterns

**1. Vben Admin Adapters**
- Forms: `useVbenForm()` from `@vben/common-ui`
- Tables: `useVbenVxeGrid()` with VxeTable integration
- Modals: `useVbenModal()` for dialogs
- Example: `frontend/apps/web-antd/src/views/project/index.vue`

**2. API Client Structure**
```typescript
// All API calls go through requestClient (auto-handles token refresh)
import { requestClient } from '#/api/request';

export async function getEntity(id: number) {
  return requestClient.get(`/entity/${id}`);
}
```

**3. Dynamic Routing**
- Menu fetched from backend `/api/menu/all` on login
- Routes generated via `generateAccessible()` in `frontend/apps/web-antd/src/router/access.ts`
- Nested routes use route params (e.g., `/projects/:projectId/fluorescence`)

## Common Tasks

### Add New Entity CRUD

**Backend**:
1. Model: `backend/app/models/entity.py` (inherit `Base`)
2. Schema: `backend/app/schemas/entity.py` (Pydantic)
3. Service: `backend/app/services/entity_service.py` (functions)
4. Router: `backend/app/routers/entity.py` (mount in `main.py`)

**Frontend**:
1. API: `frontend/apps/web-antd/src/api/entity.ts`
2. View: `frontend/apps/web-antd/src/views/entity/index.vue`
3. Route: `frontend/apps/web-antd/src/router/routes/modules/entity.ts`

### Debug Fluorescence Analysis
1. Check job status: `GET /api/fluorescence/{projectId}/jobs/{jobId}/status`
2. Backend logs: Watch uvicorn console for algorithm errors
3. Frontend polling: Check `useFluorescenceJobsStore` in Vue DevTools
4. Validate CSV format: Use `/api/fluorescence/preview` to inspect uploaded files

### Handle Database Schema Changes
1. Update `backend/sql.sql` (reference schema)
2. Modify SQLAlchemy model in `backend/app/models/`
3. **No migrations framework**—manual SQL execution or recreate database
4. Update corresponding Pydantic schemas

## Critical Files Reference

- **Backend Entry**: `backend/app/main.py` (middleware, router registration)
- **Auth Logic**: `backend/app/services/auth_service.py` (JWT creation/verification)
- **Database Config**: `backend/app/database.py` (SQLAlchemy setup)
- **Frontend Entry**: `frontend/apps/web-antd/src/main.ts`
- **API Client**: `frontend/apps/web-antd/src/api/request.ts` (token refresh interceptor)
- **Design Docs**: `backend/docs/backend_design.md`, `frontend/docs/frontend-system-design.md`

## Known Issues & Gotchas

1. **JWT_SECRET must be set** or backend startup fails (intentional security check)
2. **No database migrations**—schema changes require manual SQL or DB recreation
3. **File uploads must use FormData** with `'Content-Type': 'multipart/form-data'`
4. **Fluorescence CSV format** expects specific columns (validated in `csv_reader.py`)
5. **Job polling doesn't persist**—page refresh loses polling state (intentional for MVP)
6. **Role checking** uses string JSON array—deserialize with `app/utils/roles.py::deserialize_roles()`
7. **Monorepo structure**: Frontend uses pnpm workspaces + Turbo, backend is standalone

## External Dependencies

- **Backend**: MySQL 8.0+, Python 3.10+, numpy/pandas for signal processing
- **Frontend**: Node 18+, pnpm 8+, Ant Design Vue 4.x
- **Infrastructure**: File storage at `backend/uploads/`, no S3/cloud storage integration

---

**When uncertain about patterns**: Check existing implementations in `backend/app/routers/fluorescence.py` (complex workflow example) or `frontend/apps/web-antd/src/views/fluorescence/` (multi-step wizard with state management).
