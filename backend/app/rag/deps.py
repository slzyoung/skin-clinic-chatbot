from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.core.database import get_db
from app.rag.services.factory import AdapterFactory
from app.rag.services.rag_generator import GenerationPipeline

# RAG Pipeline dependencies - injected via app.state (lifespan) with dynamic DB LLM fallback
def get_vector_store(request: Request):
    return request.app.state.vector_store

def get_ingestion_pipeline(request: Request):
    return request.app.state.ingestion_pipeline

def get_bm25_index(request: Request):
    return request.app.state.bm25_index

def get_hybrid_retriever(request: Request):
    return request.app.state.hybrid_retriever

async def get_llm(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        return await AdapterFactory.get_dynamic_llm(db)
    except Exception as e:
        logger.error(f"Failed to load dynamic LLM adapter, falling back to app state LLM: {e}")
        return request.app.state.llm_adapter

async def get_generation_pipeline(request: Request, db: AsyncSession = Depends(get_db)):
    hybrid_retriever = request.app.state.hybrid_retriever
    try:
        llm_adapter = await AdapterFactory.get_dynamic_llm(db)
        if hybrid_retriever and llm_adapter:
            return GenerationPipeline(retriever=hybrid_retriever, llm_adapter=llm_adapter)
    except Exception as e:
        logger.error(f"Failed to create dynamic generation pipeline: {e}")
    return request.app.state.generation_pipeline


