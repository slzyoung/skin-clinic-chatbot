# RAG & Core API Integration Plan (Modular Monolith)

## Overview
This document outlines the architecture and integration plan for combining the experimental RAG system (`eksperimen-rag`) with the main backend (`backend`). 
To keep the codebase manageable for two engineers (Backend Engineer and AI Engineer), we will use a **Modular Monolith** architecture. They will share the same FastAPI application and database, but their code domains and dependencies will remain strictly separated.

## Folder Structure
All code will live inside the `backend/` folder. We will create a clear boundary between standard API logic and AI logic.

```text
backend/
├── requirements-core.txt    # Fast lightweight deps (FastAPI, SQLAlchemy, asyncpg)
├── requirements-rag.txt     # Heavy AI deps (Torch, OpenAI, Qdrant/pgvector, Docling)
├── app/
│   ├── main.py              # The entry point that glues both domains together
│   ├── core/                # Shared settings & security
│   ├── models/              # Shared Database Models (User, ChatHistory, KnowledgeChunk)
│   │
│   ├── api/                 # 👨‍💻 BACKEND ENGINEER'S DOMAIN
│   │   ├── routers/         # Standard endpoints (/users, /auth, /cis-sync)
│   │   └── dependencies.py  # DB sessions, Auth extractors
│   ├── services/            # Standard business logic
│   │   ├── auth_service.py
│   │   └── cis_sync.py
│   │
│   └── rag/                 # 🤖 AI ENGINEER'S DOMAIN (Migrated from eksperimen-rag)
│       ├── __init__.py
│       ├── ingestion/       # Document parsing, docling, & chunking logic
│       ├── retrieval/       # pgvector search, bm25, & reranking
│       ├── generation/      # LLM prompts, generation pipeline
│       └── router.py        # RAG specific endpoints (/chat, /ingest)
```

## Rules of Separation

1. **Isolation of Work:** 
   - The **Backend Engineer** only works in `app/api/` and `app/services/`.
   - The **AI Engineer** only works in `app/rag/`.
2. **Shared Resources:** 
   - Both use the same Postgres database. The AI engineer will map their vector embeddings to a table like `knowledge_chunk` inside `app/models/`.
3. **No Cross-Contamination:** 
   - Standard backend services should not directly import AI logic. All AI endpoints are exposed via `app/rag/router.py` and connected at the top level in `main.py`.

## Managing Dependencies (The "Heavy Library" Problem)
AI libraries are massive. To prevent the Backend Engineer from being forced to install gigabytes of AI dependencies (like PyTorch) on their local machine just to test standard auth routes, we will implement **Dynamic Feature Flags** in `main.py`.

### Example `app/main.py`:
```python
from fastapi import FastAPI
from app.api.routers import auth_router

app = FastAPI(title="Arya Noble CIS & AI Backend")

# 1. Load standard lightweight backend routes
app.include_router(auth_router, prefix="/api/v1")

# 2. Try to load AI routes (Fails gracefully if AI libraries are missing)
try:
    from app.rag.router import rag_router
    app.include_router(rag_router, prefix="/api/v1/ai", tags=["RAG"])
    print("✅ AI Module loaded successfully!")
except ImportError as e:
    print(f"⚠️ Running in Core-Only mode. AI module skipped due to missing dependencies: {e}")
```

### Local Development Workflows
*   **Backend Engineer Local Setup:** Runs `pip install -r requirements-core.txt`. The server boots up instantly, skipping the AI endpoints.
*   **AI Engineer Local Setup:** Runs `pip install -r requirements-core.txt -r requirements-rag.txt`. The server boots up with full capabilities.
*   **Production/Docker:** The `Dockerfile` will install BOTH requirements files so the production server has all endpoints active.

## Migration Steps (from `eksperimen-rag` to `backend`)

1. **Move Files:** Copy the folders (`ingestion`, `retrieval`, `generation`, `core`) from `eksperimen-rag/app/` into `backend/app/rag/`.
2. **Setup DB:** Modify the AI engineer's ingestion pipeline to use PostgreSQL (`pgvector`) instead of the local `Qdrant` instance. Ensure SQLAlchemy models are updated.
3. **Extract Requirements:** Move the AI-specific libraries into `backend/requirements-rag.txt`.
4. **Wire Routers:** Take the endpoints from `eksperimen-rag/app/main.py` (`/ingest`, `/search`, `/chat`) and put them into `backend/app/rag/router.py`. Connect this router to `backend/app/main.py` using the try/except block shown above.

## Future Adjustment: Dynamic Model & API Key Selection

To support a feature where the active model (GPT, Gemini, DeepSeek) can be dynamically selected and API keys managed globally from a dashboard (instead of relying solely on `.env`), the architecture requires the following adjustments:

### 1. Database Storage for Global Settings (AppConfig)
Instead of creating a new table or managing per-user API keys (which is bad UX for doctors/staff), we will use the existing `AppConfig` table (`app_config` in PostgreSQL) to securely store global AI settings.
- **Example Keys in `AppConfig`**:
  - `LLM_ACTIVE_PROVIDER` (e.g., `"openai"`, `"deepseek"`, `"gemini"`)
  - `LLM_ACTIVE_MODEL_NAME` (e.g., `"gpt-4o"`, `"deepseek-chat"`)
  - `LLM_API_KEY` (Must be encrypted at rest - corresponds to the active provider)

The frontend can override the active model by passing a `model_name` parameter in chat requests, and the backend will fetch the corresponding global `LLM_API_KEY` from `AppConfig` or `.env`.

### 2. "On-Demand" Factory Pattern
Do not initialize the LLM client globally at server startup. Change the endpoints in `backend/app/rag/router.py` to fetch the user's settings from the DB and pass them to a dynamic factory function.

### 3. Using OpenAI Compatible Endpoints
Since DeepSeek, open-source models, and Gemini (via proxy) support the OpenAI standard, you only need the `langchain-openai` library to support multiple providers dynamically.

**Example Implementation (`backend/app/rag/generation/generator.py`):**
```python
from langchain_openai import ChatOpenAI

def get_dynamic_llm(api_key: str, model_name: str, base_url: str = None):
    """
    Instantiates any OpenAI-compatible LLM fully dynamically.
    No if/else required. The dashboard or database simply passes the correct base_url.
    - OpenAI: base_url = None
    - DeepSeek: base_url = "https://api.deepseek.com/v1"
    - Gemini: base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    """
    return ChatOpenAI(
        api_key=api_key, 
        model=model_name,
        base_url=base_url
    )
```

### 4. Security & Guardrails
- **Validation**: On the dashboard, perform a lightweight test call to validate the API key before saving it to the DB.
- **Statelessness**: Ensure the `api_key` is cleared from memory after generation to prevent token leakage.
- **Error Handling**: Gracefully catch `401 Unauthorized` and `429 Too Many Requests` to notify the user via the frontend if their API key is invalid or out of quota.

## Production Considerations for RAG API

Before fully implementing the RAG API, adhere to these architectural considerations to ensure production readiness:

### 1. Pydantic Schemas Boundary
To maintain the Modular Monolith structure, **do not** put AI-specific Pydantic schemas (like `ChatRequest`, `ChatResponse`) inside the core backend's `app/schemas/` folder. Create an `app/rag/schemas.py` file specifically for the AI module.

### 2. Handling Slow Document Parsing (Docling)
`Docling` is highly accurate but computationally expensive (blocking). The `/ingest` route must not block the HTTP thread waiting for Docling to finish. 
- The route should save the file, update the `Knowledge` database status to `PROCESSING`, and trigger the ingestion pipeline as an asynchronous **Background Task** (via FastAPI `BackgroundTasks` or the existing `apscheduler`).
- Return a `202 Accepted` to the frontend immediately.

### 3. File Storage for Uploads
For containerized deployments, local `data/temp/` folders do not persist. Update `app/core/config.py` to point to a permanent storage solution for document uploads (e.g., a mapped Docker Volume like `/app/uploads` or an S3/GCP bucket).
