import os
import json
import asyncio
from typing import List, Optional
from loguru import logger
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks

from app.rag.schemas import (
    ChatRequest, 
    ChatResponse, 
    EvaluationItem,
    DocumentListItem,
    ApproveRequest,
    RejectRequest,
    PendingDocumentResponse,
    RefineRequest
)
from app.rag.services.rag_pipeline import IngestionPipeline
from app.rag.services.rag_retriever import HybridRetriever, BM25Index
from app.rag.services.rag_generator import GenerationPipeline
from app.rag.services.evaluation import RetrievalEvaluator
from app.rag.config import settings
from app.rag.deps import (
    get_ingestion_pipeline,
    get_hybrid_retriever,
    get_generation_pipeline,
    get_bm25_index,
    get_llm,
    get_vector_store
)
from app.rag.services.interfaces import BaseLLMAdapter, BaseVectorStoreAdapter


router = APIRouter()

async def process_ingestion_background(
    knowledge_id: str,
    file_path: str,
    file_name: str,
    pipeline: IngestionPipeline,
    llm: BaseLLMAdapter
):
    try:
        # Temporarily configure pipeline to stage file in data/pending without indexing
        original_output_dir = pipeline.output_dir
        original_store = pipeline.vector_store
        
        pipeline.output_dir = "data/pending"
        pipeline.vector_store = None
        os.makedirs(pipeline.output_dir, exist_ok=True)
        
        try:
            output_file = await asyncio.to_thread(pipeline.ingest_file, file_path)
        finally:
            pipeline.output_dir = original_output_dir
            pipeline.vector_store = original_store
            
        # Cleanup temp file
        try:
            import gc
            gc.collect()
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as cleanup_err:
            logger.warning(f"Could not delete temporary file {file_path}: {cleanup_err}")
            
        if not output_file:
            logger.error("Ingestion failed: no output file.")
            return
            
        # Load the staged JSON containing raw parsed chunks
        with open(output_file, 'r', encoding='utf-8') as f:
            enriched_chunks = json.load(f)
            
        summary = "No summary generated. LLM not available."
        text_accuracy = "N/A"
        feedback = "LLM adapter is not configured."
        
        if llm and enriched_chunks:
            try:
                # Build list of chunk texts
                chunk_texts = [c.get("text", "") for c in enriched_chunks]
                chunks_json = json.dumps(chunk_texts, ensure_ascii=False)
                
                review_prompt = f"""
                You are a medical aesthetic data validator for ERHA (PT Arya Noble) knowledge base.
                Review these text chunks extracted from a document:
                
                {chunks_json}
                
                Perform these tasks:
                1. Provide a concise, professional summary of this document (max 3 sentences).
                2. Grade the text accuracy and completeness (e.g. "95%").
                3. Provide feedback on data quality, noting if any critical information is missing or if there are typos/broken text.
                4. Self-heal and correct any typos, spelling errors, or incomplete words/sentences in the list of text chunks. Keep the size of the list EXACTLY the same.
                
                You must return a valid JSON object ONLY. Do not wrap in markdown block code like ```json.
                JSON structure:
                {{
                    "summary": "your summary",
                    "text_accuracy": "95%",
                    "feedback": "your feedback",
                    "corrected_chunks": ["corrected chunk 1 text", "corrected chunk 2 text", ...]
                }}
                """
                llm_response = await asyncio.to_thread(llm.generate, review_prompt)
                
                # Clean markdown formatting if present
                llm_response_clean = llm_response.strip()
                if llm_response_clean.startswith("```"):
                    lines = llm_response_clean.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines[-1].startswith("```"):
                        lines = lines[:-1]
                    llm_response_clean = "\n".join(lines).strip()
                    
                parsed_review = json.loads(llm_response_clean)
                summary = parsed_review.get("summary", summary)
                text_accuracy = parsed_review.get("text_accuracy", text_accuracy)
                feedback = parsed_review.get("feedback", feedback)
                corrected_chunks = parsed_review.get("corrected_chunks", [])
                
                # Apply corrected chunks back to enriched_chunks
                if len(corrected_chunks) == len(enriched_chunks):
                    for idx, corrected_txt in enumerate(corrected_chunks):
                        enriched_chunks[idx]["text"] = corrected_txt
                        
            except Exception as llm_err:
                logger.error(f"Failed to process AI review: {llm_err}")
                
        # Structure the final pending document state
        staged_document = {
            "file_name": file_name,
            "status": "On review",
            "summary": summary,
            "text_accuracy": text_accuracy,
            "feedback": feedback,
            "chunks": enriched_chunks
        }
        
        # Save back to pending folder in our rich structure format
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(staged_document, f, indent=4, ensure_ascii=False)
            
        # Update Knowledge DB table status to PENDING
        try:
            from app.core.database import AsyncSessionLocal
            from app.models.knowledge import Knowledge, KnowledgeStatus
            from sqlalchemy import select

            async with AsyncSessionLocal() as session:
                result = await session.execute(select(Knowledge).where(Knowledge.id == knowledge_id))
                k_entry = result.scalars().first()
                if k_entry:
                    k_entry.status = KnowledgeStatus.PENDING
                    k_entry.ai_summary = summary
                    k_entry.ai_confidence = float(text_accuracy.replace("%", "")) if isinstance(text_accuracy, str) and "%" in text_accuracy else 95.00
                    await session.commit()
        except Exception as db_err:
            logger.warning(f"Could not update status to PENDING in Knowledge DB table: {db_err}")

    except Exception as e:
        logger.error(f"Failed background processing for document: {e}")

@router.post("/ingest", tags=["Ingestion"])
async def ingest_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
    llm: BaseLLMAdapter = Depends(get_llm)
):
    """
    API endpoint to upload and stage a document for ingestion.
    Parses, chunks, self-heals, and summarizes the file using AI, 
    then stores it in data/pending/ for approval.
    """
    try:
        # Save file temporarily
        os.makedirs("data/temp", exist_ok=True)
        file_path = f"data/temp/{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())
            
        knowledge_id = None
        
        # Create Knowledge DB record as PROCESSING
        try:
            from app.core.database import AsyncSessionLocal
            from app.models.knowledge import Knowledge, KnowledgeStatus, KnowledgeType
            from app.models.user import User
            from sqlalchemy import select

            async with AsyncSessionLocal() as session:
                user_result = await session.execute(select(User).limit(1))
                user = user_result.scalars().first()
                if user:
                    knowledge = Knowledge(
                        type=KnowledgeType.GENERAL,
                        title=file.filename,
                        file_name=file.filename,
                        original_path=file_path,
                        mime_type=file.content_type,
                        status=KnowledgeStatus.PROCESSING,
                        uploaded_by=user.id,
                        ai_summary="Processing...",
                        ai_confidence=0.0
                    )
                    session.add(knowledge)
                    await session.commit()
                    await session.refresh(knowledge)
                    knowledge_id = str(knowledge.id)
        except Exception as db_err:
            logger.warning(f"Could not create initial Knowledge DB record: {db_err}")
            
        if not knowledge_id:
            raise HTTPException(status_code=500, detail="Failed to create Knowledge record.")

        # Dispatch background task
        background_tasks.add_task(
            process_ingestion_background,
            knowledge_id,
            file_path,
            file.filename,
            pipeline,
            llm
        )
        
        return {
            "status": "on_review", 
            "message": "Document uploaded and processing in background.", 
            "file_name": file.filename,
            "knowledge_id": knowledge_id
        }
    except Exception as e:
        logger.error(f"Failed to ingest document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ingest/pending", tags=["Ingestion"], response_model=List[str])
async def list_pending_ingestions():
    """
    Lists filenames of all documents pending approval.
    """
    pending_dir = "data/pending"
    if not os.path.exists(pending_dir):
        return []
    
    files = []
    for f in os.listdir(pending_dir):
        if f.endswith("_parsed.json"):
            orig_name = f[:-12]
            files.append(orig_name)
    return files


@router.get("/ingest/pending/{filename}", tags=["Ingestion"], response_model=PendingDocumentResponse)
async def get_pending_details(filename: str):
    """
    Retrieves the full staged review details and text chunks of a pending document for inspection.
    """
    pending_file = os.path.join("data/pending", f"{filename}_parsed.json")
    if not os.path.exists(pending_file):
        raise HTTPException(status_code=404, detail="Pending document not found.")
        
    try:
        with open(pending_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read pending document: {e}")


@router.post("/ingest/pending/{filename}/refine", tags=["Ingestion"], response_model=PendingDocumentResponse)
async def refine_pending_document(
    filename: str,
    request: RefineRequest,
    llm: BaseLLMAdapter = Depends(get_llm)
):
    """
    Interactively refine a staged document's summary, feedback, or text chunks 
    using natural language instructions (conversational feedback).
    """
    pending_file = os.path.join("data/pending", f"{filename}_parsed.json")
    if not os.path.exists(pending_file):
        found = False
        if os.path.exists("data/pending"):
            for f in os.listdir("data/pending"):
                if f.startswith(filename) and f.endswith("_parsed.json"):
                    pending_file = os.path.join("data/pending", f)
                    found = True
                    break
        if not found:
            raise HTTPException(status_code=404, detail=f"Pending document '{filename}' not found.")
            
    try:
        with open(pending_file, "r", encoding="utf-8") as f:
            staged_data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read staged document: {e}")
        
    if not llm:
        raise HTTPException(status_code=500, detail="LLM adapter is not configured. Cannot perform refinement.")
        
    try:
        # Prompt Gemini to refine the staged data based on instructions
        refine_prompt = f"""
        You are a medical aesthetic data validator for ERHA (PT Arya Noble) knowledge base.
        You are refining a staged document's review data based on a user instruction.
        
        Staged Document:
        {json.dumps(staged_data, indent=2, ensure_ascii=False)}
        
        User Instruction:
        "{request.prompt}"
        
        Refine the document as requested:
        1. If the instruction asks to update or correct a chunk's text (e.g. "tambahkan kalimat X", "ubah Y ke Z"), apply it to the corresponding text in the "chunks" list.
        2. If the instruction asks to refine the summary or category, update the "summary" or the chunks' metadata as appropriate.
        3. Recalculate or update the "text_accuracy" and "feedback" if needed.
        
        You must return a valid JSON object ONLY. Do not wrap in markdown block code like ```json.
        The JSON object must have EXACTLY the same structure as the Staged Document, containing these keys:
        {{
            "file_name": "filename",
            "status": "On review",
            "summary": "updated summary",
            "text_accuracy": "95%",
            "feedback": "updated feedback",
            "chunks": [
                {{
                    "text": "updated/healed chunk text",
                    "metadata": {{ ... }}
                }},
                ...
            ]
        }}
        """
        
        llm_response = llm.generate(refine_prompt)
        
        # Clean markdown formatting if present
        llm_response_clean = llm_response.strip()
        if llm_response_clean.startswith("```"):
            lines = llm_response_clean.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            llm_response_clean = "\n".join(lines).strip()
            
        updated_data = json.loads(llm_response_clean)
        
        # Save the updated data back
        with open(pending_file, "w", encoding="utf-8") as f:
            json.dump(updated_data, f, indent=4, ensure_ascii=False)
            
        return updated_data
    except Exception as e:
        logger.error(f"Refinement failed for document '{filename}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refine document: {e}")


@router.get("/ingest/documents", tags=["Ingestion"], response_model=List[DocumentListItem])
async def list_all_documents():
    """
    List all documents in the system with their status ('Approved' or 'On review') and basic metadata.
    """
    pending_dir = "data/pending"
    approved_dir = "data/output"
    
    docs = []
    
    # 1. Scan pending (which are nested object schemas)
    if os.path.exists(pending_dir):
        for f in os.listdir(pending_dir):
            if f.endswith("_parsed.json"):
                file_path = os.path.join(pending_dir, f)
                try:
                    with open(file_path, "r", encoding="utf-8") as f_json:
                        data = json.load(f_json)
                    if isinstance(data, dict):
                        chunks = data.get("chunks", [])
                        first_chunk_meta = chunks[0].get("metadata", {}) if chunks else {}
                        
                        docs.append(DocumentListItem(
                            file_name=data.get("file_name", f[:-12]),
                            product_name=first_chunk_meta.get("product_name"),
                            document_type=first_chunk_meta.get("document_type"),
                            status="On review",
                            processed_at=first_chunk_meta.get("processed_at"),
                            chunks_count=len(chunks)
                        ))
                except Exception as err:
                    logger.warning(f"Error parsing pending metadata for {f}: {err}")
                    
    # 2. Scan approved (which are lists of chunks)
    if os.path.exists(approved_dir):
        for f in os.listdir(approved_dir):
            if f.endswith("_parsed.json"):
                file_path = os.path.join(approved_dir, f)
                try:
                    with open(file_path, "r", encoding="utf-8") as f_json:
                        chunks = json.load(f_json)
                    if isinstance(chunks, list) and chunks:
                        first_chunk_meta = chunks[0].get("metadata", {})
                        file_name = first_chunk_meta.get("source_file", f[:-12])
                        product_name = first_chunk_meta.get("product_name")
                        doc_type = first_chunk_meta.get("document_type")
                        processed_at = first_chunk_meta.get("processed_at")
                        
                        docs.append(DocumentListItem(
                            file_name=file_name,
                            product_name=product_name,
                            document_type=doc_type,
                            status="Approved",
                            processed_at=processed_at,
                            chunks_count=len(chunks)
                        ))
                except Exception as err:
                    logger.warning(f"Error parsing approved metadata for {f}: {err}")
                    
    return docs


@router.post("/ingest/approve", tags=["Ingestion"])
async def approve_document(
    request: ApproveRequest,
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
    bm25: BM25Index = Depends(get_bm25_index)
):
    """
    Approves a staged document. Indexes its chunks into the Qdrant vector database and BM25 index,
    then moves the document's JSON representation to the approved directory.
    """
    filename = request.file_name
    pending_file = os.path.join("data/pending", f"{filename}_parsed.json")
    approved_file = os.path.join("data/output", f"{filename}_parsed.json")
    
    if not os.path.exists(pending_file):
        found = False
        if os.path.exists("data/pending"):
            for f in os.listdir("data/pending"):
                if f.startswith(filename) and f.endswith("_parsed.json"):
                    pending_file = os.path.join("data/pending", f)
                    approved_file = os.path.join("data/output", f)
                    found = True
                    break
        if not found:
            raise HTTPException(status_code=404, detail=f"Pending document '{filename}' not found.")
            
    try:
        with open(pending_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        chunks = data.get("chunks", []) if isinstance(data, dict) else data
            
        if pipeline.vector_store:
            logger.info(f"Indexing chunks from {filename} into vector store...")
            pipeline.vector_store.insert_chunks(chunks)
        else:
            logger.warning("No vector store instance available for indexing.")
            
        if bm25:
            logger.info(f"Indexing chunks from {filename} into BM25 index...")
            bm25.add_chunks(chunks)
            bm25.save(settings.bm25_index_path)
            
        os.makedirs("data/output", exist_ok=True)
        with open(approved_file, "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=4, ensure_ascii=False)
            
        if os.path.exists(pending_file):
            os.remove(pending_file)

        # Dual-sync update to Knowledge DB table
        try:
            from app.core.database import AsyncSessionLocal
            from app.models.knowledge import Knowledge, KnowledgeStatus
            from sqlalchemy import select
            async with AsyncSessionLocal() as session:
                stmt_k = select(Knowledge).where(Knowledge.file_name.ilike(f"%{filename}%"), Knowledge.deleted_at.is_(None))
                res_k = await session.execute(stmt_k)
                k_entry = res_k.scalars().first()
                if k_entry:
                    k_entry.status = KnowledgeStatus.APPROVED
                    await session.commit()
        except Exception as db_err:
            logger.warning(f"Could not dual-sync approved status to Knowledge DB table: {db_err}")

        return {"status": "success", "message": f"Document '{filename}' approved and indexed successfully."}
    except Exception as e:
        logger.error(f"Approval failed for document '{filename}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/reject", tags=["Ingestion"])
async def reject_document(request: RejectRequest):
    """
    Rejects a staged document, deleting it from the pending directory.
    """
    filename = request.file_name
    pending_file = os.path.join("data/pending", f"{filename}_parsed.json")
    
    if not os.path.exists(pending_file):
        found = False
        if os.path.exists("data/pending"):
            for f in os.listdir("data/pending"):
                if f.startswith(filename) and f.endswith("_parsed.json"):
                    pending_file = os.path.join("data/pending", f)
                    found = True
                    break
        if not found:
            raise HTTPException(status_code=404, detail=f"Pending document '{filename}' not found.")
            
    try:
        if os.path.exists(pending_file):
            os.remove(pending_file)

        # Dual-sync update to Knowledge DB table
        try:
            from app.core.database import AsyncSessionLocal
            from app.models.knowledge import Knowledge, KnowledgeStatus
            from sqlalchemy import select
            async with AsyncSessionLocal() as session:
                stmt_k = select(Knowledge).where(Knowledge.file_name.ilike(f"%{filename}%"), Knowledge.deleted_at.is_(None))
                res_k = await session.execute(stmt_k)
                k_entry = res_k.scalars().first()
                if k_entry:
                    k_entry.status = KnowledgeStatus.REJECTED
                    await session.commit()
        except Exception as db_err:
            logger.warning(f"Could not dual-sync rejected status to Knowledge DB table: {db_err}")

        return {"status": "success", "message": f"Document '{filename}' rejected and deleted."}
    except Exception as e:
        logger.error(f"Rejection failed for document '{filename}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/ingest/documents/{filename}", tags=["Ingestion"])
async def delete_document_endpoint(
    filename: str,
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
    bm25: BM25Index = Depends(get_bm25_index)
):
    """
    Deletes an approved document from Qdrant, local BM25 index, and disk, 
    or rejects it if it is still in the pending queue.
    """
    pending_file = os.path.join("data/pending", f"{filename}_parsed.json")
    if not os.path.exists(pending_file):
        if os.path.exists("data/pending"):
            for f in os.listdir("data/pending"):
                if f.startswith(filename) and f.endswith("_parsed.json"):
                    pending_file = os.path.join("data/pending", f)
                    break
                    
    if os.path.exists(pending_file):
        try:
            os.remove(pending_file)
            return {"status": "success", "message": f"Pending document '{filename}' deleted."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete pending document: {e}")
            
    approved_file = os.path.join("data/output", f"{filename}_parsed.json")
    orig_filename = filename
    if not os.path.exists(approved_file):
        found = False
        if os.path.exists("data/output"):
            for f in os.listdir("data/output"):
                if f.startswith(filename) and f.endswith("_parsed.json"):
                    approved_file = os.path.join("data/output", f)
                    orig_filename = f[:-12]
                    found = True
                    break
        if not found:
            raise HTTPException(status_code=404, detail=f"Document '{filename}' not found.")
            
    try:
        if pipeline.vector_store:
            pipeline.vector_store.delete_document(orig_filename)
            
        if bm25:
            bm25.remove_file_chunks(orig_filename)
            bm25.save(settings.bm25_index_path)
            
        if os.path.exists(approved_file):
            os.remove(approved_file)

        # Dual-sync soft-delete in Knowledge DB table
        try:
            from app.core.database import AsyncSessionLocal
            from app.models.knowledge import Knowledge
            from datetime import datetime, timezone
            from sqlalchemy import select
            async with AsyncSessionLocal() as session:
                stmt_k = select(Knowledge).where(Knowledge.file_name.ilike(f"%{filename}%"), Knowledge.deleted_at.is_(None))
                res_k = await session.execute(stmt_k)
                k_entry = res_k.scalars().first()
                if k_entry:
                    k_entry.deleted_at = datetime.now(timezone.utc)
                    await session.commit()
        except Exception as db_err:
            logger.warning(f"Could not dual-sync delete status to Knowledge DB table: {db_err}")
            
        return {"status": "success", "message": f"Approved document '{orig_filename}' completely deleted."}
    except Exception as e:
        logger.error(f"Deletion failed for document '{orig_filename}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", tags=["Retrieval"])
async def search_hybrid(
    query: str = Query(..., description="Query string to search for"),
    top_k: int = Query(5, description="Number of final matches to return"),
    rerank: bool = Query(True, description="Whether to apply Cross-Encoder rerank"),
    document_type: Optional[str] = Query(None, description="Filter by document type (e.g. product, treatment, faq, promotion, sop)"),
    section: Optional[str] = Query(None, description="Filter by section name (e.g. ACTIVE INGREDIENTS, HOW TO USE)"),
    confidence_threshold: Optional[float] = Query(None, description="Optional custom confidence threshold (0.0 to 1.0)"),
    retriever: HybridRetriever = Depends(get_hybrid_retriever)
):
    """
    Advanced search endpoint using Hybrid Search (Dense + Sparse/BM25) with RRF 
    and Cross-Encoder Reranking, supporting explicit metadata filtering by document type and section.
    """
    if not retriever:
        raise HTTPException(status_code=500, detail="Hybrid retriever is not initialized.")
        
    filter_metadata = {}
    if document_type and document_type.strip().lower() not in ("string", ""):
        filter_metadata["document_type"] = document_type
    if section and section.strip().lower() not in ("string", ""):
        filter_metadata["section"] = section
        
    parsed_filter = filter_metadata if filter_metadata else None
            
    try:
        hits = retriever.retrieve(
            query=query, 
            top_k=top_k, 
            filter_metadata=parsed_filter, 
            rerank=rerank,
            rerank_top_n=top_k,
            confidence_threshold=confidence_threshold
        )
        return hits
    except Exception as e:
        logger.error(f"Search endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat", response_model=ChatResponse, tags=["Generation"])
async def chat_endpoint(
    request: ChatRequest,
    pipeline: GenerationPipeline = Depends(get_generation_pipeline)
):
    """
    RAG chat endpoint. Generates a doctor-aligned response using context-enriched retrieval and LLM.
    Supports filters (document_type, section), confidence thresholds, and multi-turn chat history.
    """
    if not pipeline:
        raise HTTPException(status_code=500, detail="Generation pipeline is not initialized. Please ensure your LLM API keys are configured correctly.")
        
    filter_metadata = {}
    if request.document_type and request.document_type.strip().lower() not in ("string", ""):
        filter_metadata["document_type"] = request.document_type
    if request.section and request.section.strip().lower() not in ("string", ""):
        filter_metadata["section"] = request.section
        
    parsed_filter = filter_metadata if filter_metadata else None
    
    # Convert Pydantic chat message history to raw list of dicts for generator
    raw_history = [{"role": msg.role, "content": msg.content} for msg in request.history]
    
    try:
        response = pipeline.generate_answer(
            query=request.query,
            top_k=request.top_k,
            filter_metadata=parsed_filter,
            rerank=request.rerank,
            confidence_threshold=request.confidence_threshold,
            history=raw_history
        )
        return response
    except Exception as e:
        logger.error(f"Chat generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search/evaluate", tags=["Retrieval"])
async def evaluate_retrieval_endpoint(
    dataset: List[EvaluationItem],
    retriever: HybridRetriever = Depends(get_hybrid_retriever)
):
    """
    Evaluates search pipeline metrics (Hit Rate and MRR) over a test dataset.
    """
    if not retriever:
        raise HTTPException(status_code=500, detail="Hybrid retriever is not initialized.")
    try:
        raw_dataset = [{"query": item.query, "ground_truth": item.ground_truth} for item in dataset]
        metrics = RetrievalEvaluator.evaluate_dataset(
            retriever=retriever,
            dataset=raw_dataset,
            top_k=5,
            rerank=True,
            rerank_top_n=3
        )
        return metrics
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/reset", tags=["Ingestion"])
async def reset_database(
    vector_store: BaseVectorStoreAdapter = Depends(get_vector_store),
    bm25: BM25Index = Depends(get_bm25_index)
):
    """
    Clears the entire RAG knowledge base. Drops and recreates the PGVector collection, 
    resets the BM25 index, and deletes all files inside data/pending/ and data/output/.
    """
    try:
        # 1. Clear vector store
        if vector_store:
            logger.info("Clearing PGVector database...")
            vector_store.clear_all()
        else:
            logger.warning("No vector store instance available for clearing.")
            
        # 2. Clear BM25
        if bm25:
            logger.info("Clearing BM25 index...")
            bm25.clear()
            bm25.save(settings.bm25_index_path)
            
        # 3. Clean files in data/pending/ and data/output/
        for folder in ["data/pending", "data/output"]:
            if os.path.exists(folder):
                for f in os.listdir(folder):
                    if f.endswith("_parsed.json"):
                        try:
                            os.remove(os.path.join(folder, f))
                        except Exception as file_err:
                            logger.warning(f"Could not remove file {f}: {file_err}")
                            
        return {"status": "success", "message": "Knowledge base (PGVector, BM25, and staged/approved files) has been successfully cleared."}
    except Exception as e:
        logger.error(f"Reset database failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

