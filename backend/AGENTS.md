# AGENTS.md — Arya Noble Backend Agent Configuration

> **Core Directive:** This file serves as the source of truth for the FastAPI backend architecture, tech stack, and conventions. Always refer back to this document when generating new APIs or models.

## Project Context
We are building the backend for the **Arya Noble AI Chatbot (Clinic Information System)**. 
- **Goal**: Serve as a robust standard API for user authentication, CRUD operations, and syncing data from the CIS.
- **Scope Split**: The core API, Auth, and DB logic is handled here. The AI/RAG (Langchain) logic will be handled by a partner developer later. The backend must provide clear integration points (e.g., stub services) for the partner to inject Langchain code.

## Technology Stack
| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Database | PostgreSQL with `pgvector` |
| ORM | SQLAlchemy 2.0 (Async) |
| DB Driver | `asyncpg` |
| Auth | JWT stored in `HttpOnly` cookies |
| Background Tasks | `APScheduler` (for CIS syncing) |

## Project Structure
We follow a strictly layered architecture to ensure maintainability without over-engineering:
```text
backend/
├── app/
│   ├── api/
│   │   ├── routers/        # Endpoint definitions grouped by resource
│   │   └── dependencies.py # Reusable deps (e.g., get_db_session, get_current_user)
│   ├── core/
│   │   ├── config.py       # Pydantic BaseSettings
│   │   └── security.py     # JWT hashing and cookie management
│   ├── models/             # SQLAlchemy ORM models
│   ├── schemas/            # Pydantic schemas for requests/responses
│   ├── services/
│   │   ├── auth_service.py # Business logic for login
│   │   ├── cis_sync.py     # Background task fetching CIS data
│   │   └── rag_service.py  # Interface/stubs for the Langchain partner
│   └── main.py             # App entrypoint
```

## Core Agent Rules & Workflows
1. **Asynchronous First**: Always use `async`/`await` for DB queries (`AsyncSession`, `execute()`, `scalars()`) and API endpoints.
2. **Cookie-Based JWT Auth**: 
   - Never send tokens directly in JSON response bodies. 
   - Always set tokens via `response.set_cookie(key="access_token", value=..., httponly=True)`.
3. **Database Models**: 
   - Ensure SQLAlchemy models perfectly mirror `infra/schema.sql`.
   - Use `pgvector` library types (e.g., `Vector`) for embedding columns.
4. **Soft Deletes**: Respect the `deleted_at` column in tables like `users` and `branches`. Do not issue raw `DELETE` statements; update `deleted_at` to `now()` instead.

## Commands
| Action | Command (from `backend/` directory) |
|---|---|
| Install Deps | `pip install -r requirements.txt` (or via `uv` / `poetry` if configured) |
| Run Server | `uvicorn app.main:app --reload` |
