from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.routers import auth, users, branches, categories, knowledge, chats, webhooks, config, sync
from app.services.cis_sync import setup_cis_scheduler

scheduler = setup_cis_scheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    scheduler.start()
    try:
        from app.rag.embeddings import ensure_embedding_dimension_synced
        await ensure_embedding_dimension_synced()
    except Exception as e:
        print(f"Skipped startup embedding dimension check: {e}")
    yield
    # Shutdown
    scheduler.shutdown()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Arya Noble AI Chatbot",
    version="1.0.0",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True}
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(branches.router, prefix="/api/branches")
app.include_router(categories.router, prefix="/api/categories")
app.include_router(knowledge.router, prefix="/api/knowledge")
app.include_router(chats.router, prefix="/api/chats")
app.include_router(webhooks.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(sync.router, prefix="/api")

# --- RAG Integration (Dynamic Load) ---
try:
    # Attempt to import the AI router; fails gracefully if RAG dependencies in requirements.txt are missing
    from app.rag.router import rag_router
    app.include_router(rag_router, prefix="/api/ai", tags=["RAG"])
    print("AI Module loaded successfully!")
except ImportError as e:
    print(f"Running in Core-Only mode. AI module skipped due to missing dependencies: {e}")

@app.get("/health")
async def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}
