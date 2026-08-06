from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import uuid
import json
import os

from app.core.database import get_db
from app.api.dependencies import get_current_user, RequireAccess
from app.models.user import User, UserType
from app.models.knowledge import Knowledge, KnowledgeStatus, KnowledgeType
from app.schemas.knowledge import KnowledgeCreate, KnowledgeUpdateStatus, KnowledgeResponse
from datetime import datetime, timezone

from app.rag.deps import get_ingestion_pipeline, get_llm, get_bm25_index, get_vector_store, get_generation_pipeline, get_medical_agent
from app.rag.services.interfaces import BaseLLMAdapter
from app.rag.router import (
    ingest_document, 
    approve_document, 
    edit_approved_document,
    edit_pending_document,
    refine_pending_document,
    refine_approved_document,
    delete_document_endpoint,
    resolve_pending_file,
    resolve_approved_file,
    chat_endpoint
)
from app.rag.schemas import EditApprovedDocumentRequest, RefineRequest, ChatRequest, ChatResponse

router = APIRouter(tags=["Knowledge"])

@router.get("/", response_model=List[KnowledgeResponse])
async def list_knowledge(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireAccess("knowledge:read"))
):
    stmt = select(Knowledge).where(Knowledge.deleted_at.is_(None)).order_by(Knowledge.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{knowledge_id}", response_model=KnowledgeResponse)
async def get_knowledge(
    knowledge_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireAccess("knowledge:read"))
):
    # 1. Try fetching from DB (ignoring soft-delete filter to prevent 404)
    stmt = select(Knowledge).where(Knowledge.id == knowledge_id)
    result = await db.execute(stmt)
    knowledge = result.scalar_one_or_none()
    
    if knowledge:
        # OUT-OF-BAND SYNC: Fetch latest AI summary from RAG JSON files
        try:
            target_file = resolve_pending_file(str(knowledge_id)) or resolve_approved_file(str(knowledge_id))
            if target_file and os.path.exists(target_file):
                with open(target_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                latest_summary = data.get("summary", "")
                if latest_summary and knowledge.ai_summary != latest_summary:
                    knowledge.ai_summary = latest_summary
                    await db.commit()
                    await db.refresh(knowledge)
                # Inject full RAG data into metadata manually
                knowledge_dict = KnowledgeResponse.model_validate(knowledge).model_dump(by_alias=False)
                knowledge_dict["metadata_"] = data
                return knowledge_dict
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error loading RAG JSON: {e}")
            
        return knowledge

    # 2. Fallback check in RAG staging files (data/pending or data/output)
    target_file = resolve_pending_file(str(knowledge_id)) or resolve_approved_file(str(knowledge_id))
    now = datetime.now(timezone.utc)
    
    if target_file and os.path.exists(target_file):
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            doc_status = KnowledgeStatus.APPROVED if "output" in target_file else KnowledgeStatus.PENDING
            if isinstance(data, dict):
                file_name = data.get("file_name", "document.pdf")
                summary = data.get("summary", "")
                raw_type = str(data.get("type", "PRODUCT")).upper()
                k_type = KnowledgeType.PRODUCT
                if "TREATMENT" in raw_type:
                    k_type = KnowledgeType.TREATMENT
                elif "PROMO" in raw_type:
                    k_type = KnowledgeType.PROMOTIONAL

                return KnowledgeResponse(
                    id=knowledge_id,
                    title=file_name,
                    content=summary,
                    file_name=file_name,
                    original_path=f"data/temp/{file_name}",
                    mime_type="application/pdf",
                    file_size=None,
                    type=k_type,
                    status=doc_status,
                    ai_summary=summary,
                    ai_confidence=95.0,
                    uploaded_by=current_user.id,
                    approved_by=None,
                    metadata_=data,
                    created_at=now,
                    updated_at=now
                )
        except Exception as err:
            pass

    # 3. Dynamic processing fallback (for documents still being parsed in background)
    return KnowledgeResponse(
        id=knowledge_id,
        title="Processing Document...",
        content="Document is currently being parsed and vectorized in background...",
        file_name="processing_document.pdf",
        original_path="data/temp/processing_document.pdf",
        mime_type="application/pdf",
        file_size=None,
        type=KnowledgeType.PRODUCT,
        status=KnowledgeStatus.PROCESSING,
        ai_summary="Document processing in progress...",
        ai_confidence=0.0,
        uploaded_by=current_user.id,
        approved_by=None,
        metadata_={"status": "PROCESSING"},
        created_at=now,
        updated_at=now
    )

@router.post("/chat", response_model=ChatResponse)
async def knowledge_chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireAccess("knowledge:read")),
    pipeline = Depends(get_generation_pipeline),
    agent = Depends(get_medical_agent)
):
    return await chat_endpoint(request=request, pipeline=pipeline, agent=agent)

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "image/jpeg",
    "image/png"
}

@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_knowledge_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category_type: str = Form("Product"),
    prompt: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireAccess("knowledge:write")),
    llm: BaseLLMAdapter = Depends(get_llm)
):
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"File type {file.content_type} not allowed for file {file.filename}")
        
    pipeline = get_ingestion_pipeline(request)
    
    return await ingest_document(
        background_tasks=background_tasks,
        file=file,
        category_type=category_type,
        prompt=prompt,
        pipeline=pipeline,
        llm=llm
    )

@router.put("/{knowledge_id}/status", response_model=KnowledgeResponse)
@router.patch("/{knowledge_id}/status", response_model=KnowledgeResponse)
async def update_knowledge_status(
    knowledge_id: uuid.UUID,
    status_in: KnowledgeUpdateStatus,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireAccess("knowledge:write"))
):
    # 1. Try DB lookup (without deleted_at filter)
    stmt = select(Knowledge).where(Knowledge.id == knowledge_id)
    result = await db.execute(stmt)
    knowledge = result.scalar_one_or_none()
    
    if not knowledge:
        # Fallback: check RAG staging file to auto-create Knowledge DB record if missing
        target_file = resolve_pending_file(str(knowledge_id)) or resolve_approved_file(str(knowledge_id))
        
        file_name = "document.pdf"
        summary = ""
        k_type = KnowledgeType.PRODUCT
        
        if target_file and os.path.exists(target_file):
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    file_name = data.get("file_name", file_name)
                    summary = data.get("summary", "")
                    raw_type = str(data.get("type", "PRODUCT")).upper()
                    if "TREATMENT" in raw_type:
                        k_type = KnowledgeType.TREATMENT
                    elif "PROMO" in raw_type:
                        k_type = KnowledgeType.PROMOTIONAL
            except Exception:
                pass
                
        knowledge = Knowledge(
            id=knowledge_id,
            title=file_name,
            file_name=file_name,
            original_path=f"data/temp/{file_name}",
            mime_type="application/pdf",
            type=k_type,
            status=status_in.status,
            ai_summary=summary,
            ai_confidence=95.0,
            uploaded_by=current_user.id
        )
        db.add(knowledge)
    else:
        knowledge.status = status_in.status
        knowledge.deleted_at = None

    if status_in.status == KnowledgeStatus.APPROVED:
        knowledge.approved_by = current_user.id
        
    await db.commit()
    await db.refresh(knowledge)
    return knowledge

@router.post("/{knowledge_id}/approve")
async def approve_knowledge(
    request: Request,
    knowledge_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireAccess("knowledge:write"))
):
    pipeline = get_ingestion_pipeline(request)
    bm25 = get_bm25_index(request)
    
    res = await approve_document(str(knowledge_id), pipeline=pipeline, bm25=bm25)
    
    # Ensure DB status is updated
    stmt = select(Knowledge).where(Knowledge.id == knowledge_id)
    result = await db.execute(stmt)
    k_entry = result.scalar_one_or_none()
    if k_entry:
        k_entry.status = KnowledgeStatus.APPROVED
        k_entry.approved_by = current_user.id
        await db.commit()
        
    return res

@router.put("/{knowledge_id}")
async def edit_knowledge(
    request: Request,
    knowledge_id: uuid.UUID,
    payload: EditApprovedDocumentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireAccess("knowledge:write"))
):
    pipeline = get_ingestion_pipeline(request)
    bm25 = get_bm25_index(request)
    vector_store = get_vector_store(request)
    
    p_file = resolve_pending_file(str(knowledge_id))
    if p_file:
        res = await edit_pending_document(
            knowledge_id=str(knowledge_id),
            request=payload
        )
    else:
        res = await edit_approved_document(
            knowledge_id=str(knowledge_id),
            request=payload,
            pipeline=pipeline,
            bm25=bm25,
            vector_store=vector_store
        )
    return res

@router.post("/{knowledge_id}/refine")
async def refine_knowledge(
    request: Request,
    knowledge_id: uuid.UUID,
    payload: RefineRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireAccess("knowledge:write")),
    llm: BaseLLMAdapter = Depends(get_llm)
):
    p_file = resolve_pending_file(str(knowledge_id))
    a_file = resolve_approved_file(str(knowledge_id))
    
    if p_file:
        return await refine_pending_document(str(knowledge_id), payload, llm)
    elif a_file:
        pipeline = get_ingestion_pipeline(request)
        bm25 = get_bm25_index(request)
        vector_store = get_vector_store(request)
        return await refine_approved_document(str(knowledge_id), payload, pipeline, bm25, vector_store, llm)
    else:
        raise HTTPException(status_code=404, detail="Document not found for refinement.")

@router.delete("/{knowledge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge(
    request: Request,
    knowledge_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(RequireAccess("knowledge:delete"))
):
    # 1. Soft-delete DB record if present
    stmt = select(Knowledge).where(Knowledge.id == knowledge_id)
    result = await db.execute(stmt)
    knowledge = result.scalar_one_or_none()
    
    if knowledge:
        knowledge.deleted_at = datetime.now(timezone.utc)
        await db.commit()
        
    # 2. Hard delete vector store embeddings and JSON files via RAG subsystem
    pipeline = get_ingestion_pipeline(request)
    bm25 = get_bm25_index(request)
    vector_store = get_vector_store(request)
    
    try:
        await delete_document_endpoint(str(knowledge_id), pipeline, bm25, vector_store)
    except Exception:
        pass
                
    return None
