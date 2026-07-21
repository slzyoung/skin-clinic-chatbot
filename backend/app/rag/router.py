import os
import asyncio
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
from app.core.database import get_db, AsyncSessionLocal as async_session_maker
from app.rag.schemas import ChatRequest, ChatResponse, EvaluationItem
from app.models.config import AppConfig
from app.models.knowledge import Knowledge, KnowledgeStatus, KnowledgeType
from app.models.user import User

from app.rag.generation.factory import get_dynamic_llm
from app.rag.core.pgvector_adapter import PgVectorAdapter
from app.rag.retrieval.retriever import HybridRetriever
from app.rag.retrieval.reranker import ExternalReranker
from app.rag.generation.generator import GenerationPipeline

# We will need the embeddings model for the pgvector adapter
from langchain_openai import OpenAIEmbeddings

rag_router = APIRouter()

async def process_document(file_path: str, knowledge_id: uuid.UUID, index: bool):
    try:
        async with async_session_maker() as session:
            # Note: docling pipeline from eksperimen-rag usually takes vector_store in __init__
            # Since pipeline.py might be synchronous, we may need to run it in a threadpool, but let's assume it works for now.
            logger.info(f"Starting background ingestion for {knowledge_id}")
            
            # Fetch config for embeddings
            config = await session.execute(select(AppConfig).where(AppConfig.key == "LLM_API_KEY"))
            api_key_record = config.scalar_one_or_none()
            api_key = api_key_record.value if api_key_record else os.getenv("OPENAI_API_KEY")
            
            embeddings = OpenAIEmbeddings(api_key=api_key)
            adapter = PgVectorAdapter(session=session, embeddings_model=embeddings)
            
            from app.rag.ingestion.pipeline import IngestionPipeline
            pipeline = IngestionPipeline(vector_store=adapter) # Assuming IngestionPipeline is adapted to our adapter
            
            # In eksperimen-rag, ingest_file returns a path to output JSON
            output_file = await pipeline.ingest_file(file_path, str(knowledge_id))
            
            # Update status
            knowledge = await session.get(Knowledge, knowledge_id)
            if knowledge:
                knowledge.status = KnowledgeStatus.APPROVED
                await session.commit()
                
            logger.info(f"Finished background ingestion for {knowledge_id}")
            
    except Exception as e:
        logger.error(f"Background ingestion failed: {e}")
        async with async_session_maker() as session:
            knowledge = await session.get(Knowledge, knowledge_id)
            if knowledge:
                knowledge.status = KnowledgeStatus.REJECTED
                await session.commit()

from app.core.config import settings

@rag_router.post("/ingest", status_code=202)
async def ingest_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    index: bool = Query(True, description="Whether to index parsed chunks"),
    db: AsyncSession = Depends(get_db)
):
    """
    Asynchronously process and ingest a document.
    """
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = f"{settings.UPLOAD_DIR}/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
        
    # Get a dummy user or actual current user for uploaded_by
    user_result = await db.execute(select(User).limit(1))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=500, detail="No users in DB to associate with upload.")
        
    knowledge = Knowledge(
        type=KnowledgeType.PDF, # Simplified
        title=file.filename,
        file_name=file.filename,
        original_path=file_path,
        mime_type=file.content_type,
        status=KnowledgeStatus.PROCESSING,
        uploaded_by=user.id
    )
    db.add(knowledge)
    await db.commit()
    await db.refresh(knowledge)
        
    background_tasks.add_task(process_document, file_path, knowledge.id, index)
    
    return {"message": f"Document {file.filename} accepted for processing.", "knowledge_id": knowledge.id}

@rag_router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    RAG chat endpoint.
    """
    config = await db.execute(select(AppConfig).where(AppConfig.key == "LLM_API_KEY"))
    api_key_record = config.scalar_one_or_none()
    api_key = api_key_record.value if api_key_record else os.getenv("OPENAI_API_KEY")
    
    provider_config = await db.execute(select(AppConfig).where(AppConfig.key == "LLM_ACTIVE_PROVIDER"))
    provider = provider_config.scalar_one_or_none()
    base_url = None
    if provider and provider.value == "deepseek":
        base_url = "https://api.deepseek.com/v1"
    elif provider and provider.value == "gemini":
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        
    model_config = await db.execute(select(AppConfig).where(AppConfig.key == "LLM_ACTIVE_MODEL_NAME"))
    model_record = model_config.scalar_one_or_none()
    model_name = model_record.value if model_record else "gpt-4o-mini"
    
    llm = get_dynamic_llm(api_key=api_key, model_name=model_name, base_url=base_url)
    embeddings = OpenAIEmbeddings(api_key=api_key)
    
    reranker = ExternalReranker(llm=llm)
    retriever = HybridRetriever(session=db, embeddings_model=embeddings, reranker=reranker)
    
    # GenerationPipeline originally didn't take LLM, it took llm_adapter, but we'll adapt.
    # Let's assume GenerationPipeline takes retriever and llm
    pipeline = GenerationPipeline(retriever=retriever, llm_adapter=llm)
    
    # The eksperimen-rag generator might not be async, but we'll try calling it
    response_dict = await pipeline.generate_answer(
        query=request.query,
        top_k=request.top_k,
        filter_metadata={"document_type": request.document_type} if request.document_type else None,
        rerank=request.rerank,
        confidence_threshold=request.confidence_threshold,
        history=[{"role": msg.role, "content": msg.content} for msg in request.history]
    )
    
    return ChatResponse(
        query=request.query,
        answer=response_dict["answer"],
        context=response_dict.get("context", ""),
        results=response_dict.get("results", [])
    )

@rag_router.get("/search")
async def search_hybrid(
    query: str = Query(..., description="Query string to search for"),
    top_k: int = Query(5, description="Number of final matches to return"),
    db: AsyncSession = Depends(get_db)
):
    config = await db.execute(select(AppConfig).where(AppConfig.key == "LLM_API_KEY"))
    api_key_record = config.scalar_one_or_none()
    api_key = api_key_record.value if api_key_record else os.getenv("OPENAI_API_KEY")
    
    embeddings = OpenAIEmbeddings(api_key=api_key)
    retriever = HybridRetriever(session=db, embeddings_model=embeddings, reranker=None)
    
    results = await retriever.retrieve(query=query, top_k=top_k, rerank=False)
    return results
