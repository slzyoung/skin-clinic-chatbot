from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.routers import auth, users, branches, categories, knowledge, chats, webhooks
from app.services.cis_sync import setup_cis_scheduler

scheduler = setup_cis_scheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    scheduler.start()
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

@app.get("/health")
async def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}
