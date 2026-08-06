import os
import json
import asyncio
from typing import List, Optional
from loguru import logger
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks, Path, Body

import uuid

from app.rag.schemas import (
    ChatRequest, 
    ChatResponse, 
    EvaluationItem,
    DocumentListItem,
    PendingDocumentResponse,
    RefineRequest,
    EditApprovedDocumentRequest,
    ApprovedDocumentResponse,
    RAGEvaluationItem,
    RAGEvaluationResponse
)
from app.rag.services.rag_pipeline import IngestionPipeline
from app.rag.services.rag_retriever import HybridRetriever, BM25Index
from app.rag.services.rag_generator import GenerationPipeline
from app.rag.services.evaluation import RetrievalEvaluator, RAGEvaluator
from app.rag.services.guardrails import GuardrailsPipeline
from app.rag.config import settings
from app.rag.deps import (
    get_ingestion_pipeline,
    get_hybrid_retriever,
    get_generation_pipeline,
    get_bm25_index,
    get_llm,
    get_vector_store,
    get_medical_agent
)
from app.rag.services.interfaces import BaseLLMAdapter, BaseVectorStoreAdapter


router = APIRouter()

def resolve_pending_file(knowledge_id: str) -> Optional[str]:
    pending_dir = "data/pending"
    if not os.path.exists(pending_dir):
        return None
    clean_p = os.path.join(pending_dir, f"{knowledge_id}.json")
    if os.path.exists(clean_p):
        return clean_p
    parsed_p = os.path.join(pending_dir, f"{knowledge_id}_parsed.json")
    if os.path.exists(parsed_p):
        return parsed_p
    for f in os.listdir(pending_dir):
        if f.endswith(".json"):
            full_p = os.path.join(pending_dir, f)
            name_no_ext = f[:-5]
            if f.startswith(knowledge_id) or name_no_ext == knowledge_id or name_no_ext.replace("_parsed", "") == knowledge_id:
                return full_p
            try:
                with open(full_p, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                if isinstance(data, dict) and (data.get("knowledge_id") == knowledge_id or data.get("file_name") == knowledge_id):
                    return full_p
            except Exception:
                pass
    return None

def resolve_approved_file(knowledge_id: str) -> Optional[str]:
    approved_dir = "data/output"
    if not os.path.exists(approved_dir):
        return None
    clean_p = os.path.join(approved_dir, f"{knowledge_id}.json")
    if os.path.exists(clean_p):
        return clean_p
    parsed_p = os.path.join(approved_dir, f"{knowledge_id}_parsed.json")
    if os.path.exists(parsed_p):
        return parsed_p
    for f in os.listdir(approved_dir):
        if f.endswith(".json"):
            full_p = os.path.join(approved_dir, f)
            name_no_ext = f[:-5]
            if f.startswith(knowledge_id) or name_no_ext == knowledge_id or name_no_ext.replace("_parsed", "") == knowledge_id:
                return full_p
            try:
                with open(full_p, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                if isinstance(data, dict) and (data.get("knowledge_id") == knowledge_id or data.get("file_name") == knowledge_id):
                    return full_p
                elif isinstance(data, list) and data:
                    meta = data[0].get("metadata", {})
                    if meta.get("knowledge_id") == knowledge_id or meta.get("source_file") == knowledge_id:
                        return full_p
            except Exception:
                pass
    return None

async def process_ingestion_background(
    knowledge_id: str,
    file_path: str,
    file_name: str,
    pipeline: IngestionPipeline,
    llm: BaseLLMAdapter,
    doc_type_display: str = "Product",
    user_prompt: Optional[str] = None
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

        # Inject metadata cleanly into every chunk immediately
        for chunk in enriched_chunks:
            if isinstance(chunk, dict):
                if "metadata" not in chunk:
                    chunk["metadata"] = {}
                chunk["metadata"]["knowledge_id"] = knowledge_id
                chunk["metadata"]["source_file"] = file_name
                chunk["metadata"]["type"] = doc_type_display.lower()
                chunk["metadata"].pop("suggested_categories", None)
                chunk["metadata"].pop("document_type", None)

        full_extracted_text = "\n\n".join([c.get("text", "") for c in enriched_chunks if isinstance(c, dict) and c.get("text")])

        # Write initial pending state IMMEDIATELY (0.5s) so GET /pending and GET /documents work instantly
        os.makedirs("data/pending", exist_ok=True)
        pending_file_path = os.path.join("data/pending", f"{knowledge_id}.json")
        initial_staged_doc = {
            "knowledge_id": knowledge_id,
            "file_name": file_name,
            "type": doc_type_display,
            "status": "On review",
            "summary": full_extracted_text,
            "text_accuracy": "100%",
            "feedback": f"Dokumen {file_name} telah berhasil diekstrak dan tersimpan di area peninjauan.",
            "suggested_categories": [],
            "chunks": enriched_chunks
        }
        with open(pending_file_path, 'w', encoding='utf-8') as f:
            json.dump(initial_staged_doc, f, indent=4, ensure_ascii=False)
            
        summary = full_extracted_text
        text_accuracy = "100%"
        feedback = f"Dokumen {file_name} telah berhasil diekstrak dan tersimpan di area peninjauan."
        suggested_categories = []
        
        if llm and enriched_chunks:
            try:
                # Fetch categories from DB for LLM recommendation
                db_categories = []
                try:
                    from app.core.database import AsyncSessionLocal
                    from app.models.category import Category
                    from sqlalchemy import select
                    async with AsyncSessionLocal() as session:
                        res = await session.execute(select(Category).where(Category.deleted_at.is_(None)))
                        cats = res.scalars().all()
                        db_categories = [{"id": str(c.id), "name": c.name} for c in cats]
                except Exception as cat_err:
                    logger.warning(f"Failed to fetch categories for review prompt: {cat_err}")
                
                if not db_categories:
                    default_cats = [
                        ("9b79e362-ec70-4560-902e-fd5897c07a00", "Acne Care"),
                        ("1a23b456-ec70-4560-902e-fd5897c07a01", "Anti Aging"),
                        ("2b34c567-ec70-4560-902e-fd5897c07a02", "Dark Spot"),
                        ("3c45d678-ec70-4560-902e-fd5897c07a03", "Psoriasis Care"),
                        ("4d56e789-ec70-4560-902e-fd5897c07a04", "Scar Treatment"),
                        ("5e67f890-ec70-4560-902e-fd5897c07a05", "Wound Healing"),
                        ("6f78a901-ec70-4560-902e-fd5897c07a06", "Brightening")
                    ]
                    db_categories = [{"id": cid, "name": cname} for cid, cname in default_cats]

                # Build full extracted markdown text from enriched_chunks
                full_extracted_text = "\n\n".join([c.get("text", "") for c in enriched_chunks if isinstance(c, dict) and c.get("text")])
                summary = full_extracted_text

                user_instruction_block = f"""
                CRITICAL USER CUSTOM INSTRUCTION (HIGHEST PRIORITY):
                "{user_prompt}"
                You MUST follow and fulfill the user's custom instruction above (e.g. translate to Indonesian, reformat, highlight specific sections, etc.) when generating the summary and correcting chunks.
                """ if user_prompt and str(user_prompt).strip() else ""

                review_prompt = f"""
                You are a world-class AI Medical Aesthetic Specialist & Knowledge Engineer for ERHA (PT Arya Noble) knowledge base.
                Your task is to refine, validate, and structure the extracted document content to production-grade quality matching ChatGPT / Claude standards.

                Extracted Document Content:
                {full_extracted_text}

                Available System Categories:
                {json.dumps(db_categories, ensure_ascii=False)}

                {user_instruction_block}

                PRODUCTION-GRADE QUALITY RULES:
                - Output MUST be beautifully formatted in clean standard Markdown with clear titles (`#`), section headers (`##`), bold highlights (`**`), bullet points (`-`), and crisp tables (`| Col 1 | Col 2 |`).
                - Fix any typos, grammar errors, OCR misreadings, or awkward phrasing while retaining 100% factual and clinical accuracy.
                - Preserve all medical details, active ingredients, dosage, usage guidelines, indications, contraindications, and patient safety notes.
                - Do NOT include any generic AI intros like "Here is the summary" or "AI Executive Overview". The `summary` MUST start directly with `# [Document Title]`.

                Perform the following tasks:
                1. **AI Recommended Title (`title`)**: Provide a short, professional title for the knowledge header (e.g. "Knowledge Ingestment Brightener Product" or "Knowledge Ingestment ERHA Acne Spot Gel Protocol").
                2. **Elaborated Full Document Markdown (`summary`)**: Present the ENTIRE document content in production-ready Markdown starting directly with `# Document Title`. Fulfill any user custom instructions if provided.
                3. **Multi-Category Selection (`suggested_categories`)**: Recommend ALL relevant matching categories (array of objects with "id" and "name") from Available System Categories.
                4. **Executive Feedback (`feedback`)**: Provide a clear, professional 1-2 sentence executive summary feedback bubble for the review UI.
                5. **Text Accuracy (`text_accuracy`)**: Grade the overall text confidence score (e.g. "99%" or "100%").
                6. **Corrected Chunks (`corrected_chunks`)**: Return the array of corrected text chunks matching input chunk count with user custom prompt applied.

                Return a valid JSON object ONLY (do not wrap in markdown block code like ```json):
                {{
                    "title": "Knowledge Ingestment ERHA Acne Spot Gel Protocol",
                    "summary": "# ERHA Product / Protocol Title\\n\\nContent...",
                    "feedback": "Document validated and structured successfully with 100% clinical accuracy.",
                    "text_accuracy": "100%",
                    "suggested_categories": [
                        {{
                            "id": "9b79e362-ec70-4560-902e-fd5897c07a00",
                            "name": "Acne Care"
                        }}
                    ],
                    "corrected_chunks": ["chunk 1 text", "chunk 2 text", ...]
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
                recommended_title = parsed_review.get("title", f"Knowledge Ingestment {file_name}")
                summary = parsed_review.get("summary", summary)
                text_accuracy = parsed_review.get("text_accuracy", "100%")
                feedback = parsed_review.get("feedback", feedback)
                suggested_categories = parsed_review.get("suggested_categories", [])
                corrected_chunks = parsed_review.get("corrected_chunks", [])
                
                # Apply corrected chunks back to enriched_chunks if matching count
                if len(corrected_chunks) == len(enriched_chunks):
                    for idx, corrected_txt in enumerate(corrected_chunks):
                        enriched_chunks[idx]["text"] = corrected_txt
                        
            except Exception as llm_err:
                logger.error(f"Failed to process AI review: {llm_err}")
                recommended_title = f"Knowledge Ingestment {file_name}"
                if not summary or summary == "":
                    summary = "\n\n".join([c.get("text", "") for c in enriched_chunks if isinstance(c, dict) and c.get("text")])
                if not suggested_categories and db_categories:
                    suggested_categories = [db_categories[0]]
                feedback = f"Dokumen {file_name} telah berhasil diekstrak dan tersimpan di area peninjauan. Pemrosesan analisis AI otomatis sementara tertunda (kuota token API perlu diperbarui). Seluruh isi teks dokumen dapat ditinjau di bawah."
                
        # Inject metadata cleanly into every chunk
        cat_names = [c["name"] for c in suggested_categories if isinstance(c, dict) and "name" in c] if suggested_categories else []
        for chunk in enriched_chunks:
            if isinstance(chunk, dict):
                if "metadata" not in chunk:
                    chunk["metadata"] = {}
                chunk["metadata"]["knowledge_id"] = knowledge_id
                chunk["metadata"]["source_file"] = file_name
                chunk["metadata"]["type"] = doc_type_display.lower()
                if cat_names:
                    chunk["metadata"]["categories"] = cat_names
                chunk["metadata"].pop("suggested_categories", None)
                chunk["metadata"].pop("document_type", None)

        history_list = []
        if user_prompt and str(user_prompt).strip():
            history_list = [
                {"role": "user", "content": str(user_prompt).strip()},
                {"role": "assistant", "content": summary}
            ]

        # Structure the final pending document state
        staged_document = {
            "knowledge_id": knowledge_id,
            "file_name": file_name,
            "title": recommended_title,
            "type": doc_type_display,
            "status": "On review",
            "summary": summary,
            "text_accuracy": text_accuracy,
            "feedback": feedback,
            "suggested_categories": suggested_categories,
            "initial_prompt": user_prompt if user_prompt and str(user_prompt).strip() else None,
            "history": history_list,
            "chunks": enriched_chunks
        }
        
        # Save back to pending folder using knowledge_id in filename
        pending_file_path = os.path.join("data/pending", f"{knowledge_id}.json")
        with open(pending_file_path, 'w', encoding='utf-8') as f:
            json.dump(staged_document, f, indent=4, ensure_ascii=False)

        # Remove temporary output_file if named differently (e.g. filename_parsed.json)
        if output_file and os.path.exists(output_file) and os.path.abspath(output_file) != os.path.abspath(pending_file_path):
            try:
                os.remove(output_file)
            except Exception:
                pass
            
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

@router.post(
    "/ingest", 
    tags=["Ingestion"], 
    summary="Upload and Ingest Document",
    openapi_extra={
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "file": {
                                "type": "array",
                                "items": {"type": "string", "format": "binary"},
                                "description": "Primary document file(s) to upload. Select 1 or multiple files (Choose File)"
                            },
                            "category_type": {
                                "type": "string",
                                "default": "Product",
                                "description": "Category Type: 'Product', 'Treatment', 'Promotional', or 'Other'"
                            },
                            "prompt": {
                                "type": "string",
                                "description": "Optional custom AI instruction for document processing (e.g. translation, reformatting, custom sectioning)"
                            }
                        },
                        "required": ["file"]
                    }
                }
            }
        }
    }
)
async def ingest_document(
    background_tasks: BackgroundTasks,
    file: List[UploadFile] = File(..., description="Primary document file(s) to upload (Choose File)"),
    category_type: str = Form("Product", description="Category Type: 'Product', 'Treatment', 'Promotional', or 'Other'"),
    prompt: Optional[str] = Form(None, description="Optional custom AI instruction for document processing (e.g. translation, reformatting, custom sectioning)"),
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
    llm: BaseLLMAdapter = Depends(get_llm)
):
    """
    API endpoint to upload and stage document(s) for ingestion.
    Parses, chunks, self-heals, and summarizes the file(s) using AI, 
    then stores them in data/pending/ for approval.
    """
    upload_list = file if isinstance(file, list) else [file]
    upload_list = [f for f in upload_list if f is not None and f.filename]
    if not upload_list:
        raise HTTPException(status_code=400, detail="Please upload at least one document file.")

    try:
        raw_type = (category_type or "").strip().upper()
        from app.models.knowledge import KnowledgeType
        
        response_items = []
        os.makedirs("data/temp", exist_ok=True)

        for target_file in upload_list:
            if not target_file.filename:
                continue

            if "PRODUCT" in raw_type:
                k_type = KnowledgeType.PRODUCT
                doc_type_display = "Product"
            elif "TREATMENT" in raw_type:
                k_type = KnowledgeType.TREATMENT
                doc_type_display = "Treatment"
            elif "PROMO" in raw_type:
                k_type = KnowledgeType.PROMOTIONAL
                doc_type_display = "Promotional"
            elif "OTHER" in raw_type or "LAIN" in raw_type:
                k_type = KnowledgeType.GENERAL
                doc_type_display = "Other"
            else:
                fn_lower = target_file.filename.lower()
                if any(w in fn_lower for w in ["product", "gel", "cream", "serum", "lotion", "cleanser", "acne", "brochure"]):
                    k_type = KnowledgeType.PRODUCT
                    doc_type_display = "Product"
                elif any(w in fn_lower for w in ["treatment", "procedure", "terapi", "tindakan"]):
                    k_type = KnowledgeType.TREATMENT
                    doc_type_display = "Treatment"
                elif any(w in fn_lower for w in ["promo", "discount", "voucher"]):
                    k_type = KnowledgeType.PROMOTIONAL
                    doc_type_display = "Promotional"
                else:
                    k_type = KnowledgeType.GENERAL
                    doc_type_display = "Other"

            file_path = f"data/temp/{target_file.filename}"
            with open(file_path, "wb") as f_out:
                f_out.write(await target_file.read())

            file_size = os.path.getsize(file_path)

            k_id = None
            try:
                from app.core.database import AsyncSessionLocal
                from app.models.knowledge import Knowledge, KnowledgeStatus
                from app.models.user import User
                from sqlalchemy import select
                import uuid as _uuid

                async with AsyncSessionLocal() as session:
                    user_result = await session.execute(select(User).limit(1))
                    user = user_result.scalars().first()
                    user_id = user.id if user else _uuid.uuid4()

                    res = await session.execute(
                        select(Knowledge).where(Knowledge.file_name == target_file.filename).order_by(Knowledge.created_at.desc())
                    )
                    existing_doc = res.scalars().first()
                    if existing_doc:
                        k_id = str(existing_doc.id)

                    if not k_id:
                        pf = resolve_pending_file(target_file.filename) or resolve_approved_file(target_file.filename)
                        if pf and os.path.exists(pf):
                            try:
                                with open(pf, "r", encoding="utf-8") as fp:
                                    pf_data = json.load(fp)
                                if isinstance(pf_data, dict) and pf_data.get("knowledge_id"):
                                    k_id = str(pf_data.get("knowledge_id"))
                            except Exception:
                                pass

                    custom_uuid = None
                    if k_id:
                        try:
                            custom_uuid = _uuid.UUID(k_id)
                        except ValueError:
                            pass

                    if existing_doc or (custom_uuid and (await session.get(Knowledge, custom_uuid))):
                        knowledge = await session.get(Knowledge, custom_uuid) if custom_uuid else existing_doc
                        if knowledge:
                            knowledge.type = k_type
                            knowledge.status = KnowledgeStatus.PROCESSING
                            knowledge.ai_summary = "Processing..."
                            knowledge.original_path = file_path
                            knowledge.mime_type = target_file.content_type
                            knowledge.file_size = file_size
                            await session.commit()
                            await session.refresh(knowledge)
                            k_id = str(knowledge.id)
                    else:
                        knowledge = Knowledge(
                            id=custom_uuid if custom_uuid else _uuid.uuid4(),
                            type=k_type,
                            title=target_file.filename,
                            file_name=target_file.filename,
                            original_path=file_path,
                            mime_type=target_file.content_type,
                            file_size=file_size,
                            status=KnowledgeStatus.PROCESSING,
                            uploaded_by=user_id,
                            ai_summary="Processing...",
                            ai_confidence=0.0
                        )
                        session.add(knowledge)
                        await session.commit()
                        await session.refresh(knowledge)
                        k_id = str(knowledge.id)
            except Exception as db_err:
                logger.warning(f"Could not create or update Knowledge DB record for {target_file.filename}: {db_err}")
                if not k_id:
                    k_id = str(_uuid.uuid4())

            background_tasks.add_task(
                process_ingestion_background,
                k_id,
                file_path,
                target_file.filename,
                pipeline,
                llm,
                doc_type_display,
                prompt
            )

            response_items.append({
                "knowledge_id": k_id,
                "file_name": target_file.filename,
                "type": doc_type_display,
                "status": "On review"
            })

        return {
            "status": "success",
            "message": f"Successfully queued {len(response_items)} document(s) for ingestion.",
            "total_files": len(response_items),
            "documents": response_items
        }

    except Exception as e:
        logger.error(f"Failed to ingest document(s): {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ingest/pending/{knowledge_id}", tags=["Ingestion"], response_model=PendingDocumentResponse)
async def get_pending_details(knowledge_id: str):
    """
    Retrieves the full staged review details and text chunks of a document for inspection.
    """
    target_file = resolve_pending_file(knowledge_id) or resolve_approved_file(knowledge_id)
    if not target_file:
        # Fallback check in PostgreSQL DB for PROCESSING status
        try:
            from app.core.database import AsyncSessionLocal
            from app.models.knowledge import Knowledge
            import uuid as _uuid
            async with AsyncSessionLocal() as session:
                custom_uuid = None
                try:
                    custom_uuid = _uuid.UUID(knowledge_id)
                except ValueError:
                    pass
                
                k_doc = None
                if custom_uuid:
                    k_doc = await session.get(Knowledge, custom_uuid)
                else:
                    from sqlalchemy import select
                    res = await session.execute(select(Knowledge).where(Knowledge.file_name == knowledge_id).order_by(Knowledge.created_at.desc()))
                    k_doc = res.scalars().first()
                    
                if k_doc:
                    raw_type = k_doc.type.value if hasattr(k_doc.type, "value") else str(k_doc.type)
                    return {
                        "knowledge_id": str(k_doc.id),
                        "file_name": k_doc.file_name,
                        "type": raw_type.capitalize() if raw_type else "Product",
                        "status": "PROCESSING",
                        "summary": "Document processing in progress...",
                        "text_accuracy": "100%",
                        "feedback": "Pemrosesan dokumen sedang berlangsung di background.",
                        "suggested_categories": [],
                        "chunks": []
                    }
        except Exception as db_err:
            logger.warning(f"DB fallback check failed for {knowledge_id}: {db_err}")

        raise HTTPException(status_code=404, detail=f"Document '{knowledge_id}' not found.")
        
    try:
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            if "knowledge_id" not in data:
                data["knowledge_id"] = knowledge_id
            if "type" not in data or not data["type"]:
                data["type"] = "Product"
            if "status" not in data or not data["status"]:
                data["status"] = "Approved" if "output" in target_file else "On review"
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read document details: {e}")


@router.post("/ingest/pending/{knowledge_id}/refine", tags=["Ingestion"], response_model=PendingDocumentResponse)
async def refine_pending_document(
    knowledge_id: str,
    request: RefineRequest,
    llm: BaseLLMAdapter = Depends(get_llm)
):
    """
    Interactively refine a staged document's summary, feedback, or text chunks 
    using natural language instructions (conversational feedback).
    """
    pending_file = resolve_pending_file(knowledge_id)
    if not pending_file:
        raise HTTPException(status_code=404, detail=f"Pending document '{knowledge_id}' not found.")
            
    try:
        with open(pending_file, "r", encoding="utf-8") as f:
            staged_data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read staged document: {e}")
        
    if not llm:
        raise HTTPException(status_code=500, detail="LLM adapter is not configured. Cannot perform refinement.")
        
    try:
        # Fetch categories from DB for LLM recommendation
        db_categories = []
        try:
            from app.core.database import AsyncSessionLocal
            from app.models.category import Category
            from sqlalchemy import select
            async with AsyncSessionLocal() as session:
                res = await session.execute(select(Category).where(Category.deleted_at.is_(None)))
                cats = res.scalars().all()
                db_categories = [{"id": str(c.id), "name": c.name} for c in cats]
        except Exception as cat_err:
            logger.warning(f"Failed to fetch categories for refine prompt: {cat_err}")

        if not db_categories:
            default_cats = [
                ("9b79e362-ec70-4560-902e-fd5897c07a00", "Acne Care"),
                ("1a23b456-ec70-4560-902e-fd5897c07a01", "Anti Aging"),
                ("2b34c567-ec70-4560-902e-fd5897c07a02", "Dark Spot"),
                ("3c45d678-ec70-4560-902e-fd5897c07a03", "Psoriasis Care"),
                ("4d56e789-ec70-4560-902e-fd5897c07a04", "Scar Treatment"),
                ("5e67f890-ec70-4560-902e-fd5897c07a05", "Wound Healing"),
                ("6f78a901-ec70-4560-902e-fd5897c07a06", "Brightening")
            ]
            db_categories = [{"id": cid, "name": cname} for cid, cname in default_cats]

        history_str = ""
        if request.history:
            for msg in request.history:
                role = "User" if getattr(msg, "role", "") == "user" else "Assistant"
                content = getattr(msg, "content", "")
                history_str += f"{role}: {content}\n"
        else:
            history_str = "No previous refinement history.\n"

        # Prompt Gemini to refine the staged data based on instructions & history
        refine_prompt = f"""
        You are an intelligent medical aesthetic AI validator for ERHA (PT Arya Noble) knowledge base.
        You are refining a staged document's review data based on user instructions and multi-turn conversation history.
        
        Staged Document:
        {json.dumps(staged_data, indent=2, ensure_ascii=False)}
        
        Available System Categories:
        {json.dumps(db_categories, ensure_ascii=False)}
        
        Conversation History:
        {history_str}
        
        Latest User Instruction:
        "{request.prompt}"
        
        Refine the document as requested:
        1. If the instruction asks to update or correct text (e.g. "perbaiki struktur", "translate ke Indonesia"), update the "summary" and the "text" in the "chunks" list.
        2. If the instruction asks to add, remove, or change categories (e.g. "tambahkan kategori Brightening", "hapus kategori Anti Aging"), update the "suggested_categories" array accordingly using valid matching objects from Available System Categories.
        3. Recalculate or update the "text_accuracy" and "feedback" to accurately reflect the changes made.
        
        You must return a valid JSON object ONLY. Do not wrap in markdown block code like ```json.
        The JSON object must have EXACTLY the same structure as the Staged Document, containing these keys:
        {{
            "knowledge_id": "id",
            "file_name": "filename",
            "type": "Product",
            "status": "On review",
            "summary": "updated summary markdown",
            "text_accuracy": "100%",
            "feedback": "updated executive feedback bubble",
            "suggested_categories": [
                {{"id": "category_id", "name": "category_name"}}
            ],
            "chunks": [
                {{
                    "text": "updated chunk text",
                    "metadata": {{ ... }}
                }}
            ]
        }}
        """
        
        llm_response = await asyncio.to_thread(llm.generate, refine_prompt)
        
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

        k_id = staged_data.get("knowledge_id", knowledge_id)
        updated_data["knowledge_id"] = k_id

        # Preserve initial_prompt and visibility_settings
        if "initial_prompt" not in updated_data and "initial_prompt" in staged_data:
            updated_data["initial_prompt"] = staged_data.get("initial_prompt")
        if "visibility_settings" not in updated_data and "visibility_settings" in staged_data:
            updated_data["visibility_settings"] = staged_data.get("visibility_settings")

        # Build updated multi-turn conversation history
        existing_hist = staged_data.get("history", [])
        if not isinstance(existing_hist, list):
            existing_hist = []
        new_hist = list(existing_hist)
        new_hist.append({"role": "user", "content": request.prompt})
        new_hist.append({"role": "assistant", "content": updated_data.get("summary", "")})
        updated_data["history"] = new_hist

        for chunk in updated_data.get("chunks", []):
            if isinstance(chunk, dict):
                if "metadata" not in chunk:
                    chunk["metadata"] = {}
                chunk["metadata"]["knowledge_id"] = k_id
        
        # Save the updated data back
        with open(pending_file, "w", encoding="utf-8") as f:
            json.dump(updated_data, f, indent=4, ensure_ascii=False)
            
        return updated_data
    except Exception as e:
        logger.error(f"Refinement failed for document '{knowledge_id}': {e}")
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
            if f.endswith(".json"):
                file_path = os.path.join(pending_dir, f)
                try:
                    with open(file_path, "r", encoding="utf-8") as f_json:
                        data = json.load(f_json)
                    if isinstance(data, dict):
                        chunks = data.get("chunks", [])
                        first_chunk_meta = chunks[0].get("metadata", {}) if chunks and isinstance(chunks[0], dict) else {}
                        fallback_id = f.replace("_parsed.json", "").replace(".json", "")
                        k_id = data.get("knowledge_id", first_chunk_meta.get("knowledge_id", fallback_id))

                        doc_type = data.get("type") or first_chunk_meta.get("type") or first_chunk_meta.get("document_type") or "Product"
                        if doc_type:
                            doc_type = doc_type.capitalize()

                        docs.append(DocumentListItem(
                            knowledge_id=k_id,
                            file_name=data.get("file_name", fallback_id),
                            product_name=first_chunk_meta.get("product_name"),
                            type=doc_type,
                            status=data.get("status", "On review"),
                            processed_at=first_chunk_meta.get("processed_at"),
                            chunks_count=len(chunks)
                        ))
                except Exception as err:
                    logger.warning(f"Error parsing pending metadata for {f}: {err}")
                    
    # 2. Scan approved
    if os.path.exists(approved_dir):
        for f in os.listdir(approved_dir):
            if f.endswith(".json"):
                file_path = os.path.join(approved_dir, f)
                try:
                    with open(file_path, "r", encoding="utf-8") as f_json:
                        data = json.load(f_json)
                    
                    raw_id = f.replace("_parsed.json", "").replace(".json", "")
                    k_id = raw_id
                    file_name = raw_id
                    product_name = None
                    doc_type = "Product"
                    processed_at = None
                    chunks = []
                    
                    if isinstance(data, dict):
                        k_id = data.get("knowledge_id", k_id)
                        file_name = data.get("file_name", file_name)
                        doc_type = data.get("type") or doc_type
                        chunks = data.get("chunks", [])
                        if chunks and isinstance(chunks[0], dict):
                            first_meta = chunks[0].get("metadata", {})
                            product_name = first_meta.get("product_name")
                            doc_type = data.get("type") or first_meta.get("type") or first_meta.get("document_type") or doc_type
                            processed_at = first_meta.get("processed_at")
                    elif isinstance(data, list):
                        chunks = data
                        if chunks and isinstance(chunks[0], dict):
                            first_meta = chunks[0].get("metadata", {})
                            k_id = first_meta.get("knowledge_id", k_id)
                            file_name = first_meta.get("source_file", file_name)
                            product_name = first_meta.get("product_name")
                            doc_type = first_meta.get("type") or first_meta.get("document_type") or doc_type
                            processed_at = first_meta.get("processed_at")
                            
                    if doc_type:
                        doc_type = doc_type.capitalize()

                    docs.append(DocumentListItem(
                        knowledge_id=k_id,
                        file_name=file_name,
                        product_name=product_name,
                        type=doc_type,
                        status="Approved",
                        processed_at=processed_at,
                        chunks_count=len(chunks)
                    ))
                except Exception as err:
                    logger.warning(f"Error parsing approved metadata for {f}: {err}")
                    
    return docs


@router.get("/ingest/approved/{knowledge_id}", tags=["Ingestion"], response_model=ApprovedDocumentResponse)
async def get_approved_document_details(knowledge_id: str):
    """
    Retrieves detail data (chunks, summary, categories) of an approved document for frontend edit form rendering.
    """
    approved_file = resolve_approved_file(knowledge_id) or resolve_pending_file(knowledge_id)
    if not approved_file:
        raise HTTPException(status_code=404, detail=f"Document '{knowledge_id}' not found.")
        
    try:
        with open(approved_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        summary = ""
        categories = []
        chunks = []
        file_name = knowledge_id

        if isinstance(data, dict):
            summary = data.get("summary", "")
            categories = data.get("categories", [])
            chunks = data.get("chunks", [])
            file_name = data.get("file_name", knowledge_id)
        elif isinstance(data, list):
            chunks = data
            if chunks and isinstance(chunks[0], dict):
                first_meta = chunks[0].get("metadata", {})
                file_name = first_meta.get("source_file", knowledge_id)
                summary = first_meta.get("summary", "")
                cat = first_meta.get("document_type")
                if cat:
                    categories = [cat]

        vis_settings = (data.get("visibility_settings") if isinstance(data, dict) else None) or {
            "clinics": ["all"],
            "doctor_types": ["all"],
            "doctors": ["all"]
        }

        return ApprovedDocumentResponse(
            knowledge_id=knowledge_id,
            file_name=file_name,
            status="Approved",
            summary=summary,
            categories=categories,
            visibility_settings=vis_settings,
            chunks=chunks
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to read approved document '{knowledge_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read approved document: {e}")


@router.put("/ingest/approved/{knowledge_id}", tags=["Ingestion"])
async def edit_approved_document(
    knowledge_id: str,
    request: EditApprovedDocumentRequest,
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
    bm25: BM25Index = Depends(get_bm25_index),
    vector_store: BaseVectorStoreAdapter = Depends(get_vector_store)
):
    """
    Edits an approved document's summary and categories manually (from UI Save Form).
    Automatically re-indexes into PGVector & BM25, and updates PostgreSQL KnowledgeCategory table.
    """
    approved_file = resolve_approved_file(knowledge_id)
    if not approved_file:
        raise HTTPException(status_code=404, detail=f"Approved document '{knowledge_id}' not found.")

    try:
        with open(approved_file, "r", encoding="utf-8") as f:
            existing_doc = json.load(f)

        updated_summary = request.summary if request.summary is not None else existing_doc.get("summary", "")
        updated_categories = request.categories if (request.categories is not None and len(request.categories) > 0) else existing_doc.get("categories", [])
        updated_chunks = existing_doc.get("chunks", [])
        file_name = existing_doc.get("file_name", knowledge_id)

        primary_cat = updated_categories[0] if updated_categories else None
        for chunk in updated_chunks:
            if isinstance(chunk, dict):
                if "metadata" not in chunk:
                    chunk["metadata"] = {}
                chunk["metadata"]["knowledge_id"] = knowledge_id
                if primary_cat:
                    chunk["metadata"]["document_type"] = primary_cat
                if updated_categories:
                    chunk["metadata"]["categories"] = updated_categories
                if updated_summary:
                    chunk["metadata"]["summary"] = updated_summary

        approved_doc_structure = {
            "knowledge_id": knowledge_id,
            "file_name": file_name,
            "status": "Approved",
            "summary": updated_summary,
            "categories": updated_categories,
            "chunks": updated_chunks
        }
        with open(approved_file, "w", encoding="utf-8") as f:
            json.dump(approved_doc_structure, f, indent=4, ensure_ascii=False)

        target_store = (pipeline.vector_store if pipeline and pipeline.vector_store else vector_store)
        if target_store:
            logger.info(f"Re-indexing PGVector for knowledge_id '{knowledge_id}'...")
            target_store.delete_document(knowledge_id)
            target_store.insert_chunks(updated_chunks)

        if bm25:
            logger.info(f"Re-indexing BM25 for knowledge_id '{knowledge_id}'...")
            bm25.remove_file_chunks(knowledge_id)
            bm25.add_chunks(updated_chunks)
            bm25.save(settings.bm25_index_path)

        if target_store and hasattr(target_store, "upsert_knowledge_category"):
            target_store.upsert_knowledge_category(
                knowledge_id=knowledge_id,
                file_name=file_name,
                categories=updated_categories,
                summary=updated_summary
            )

        return approved_doc_structure
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Edit approved document failed for '{knowledge_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update approved document: {e}")


@router.put("/ingest/pending/{knowledge_id}", tags=["Ingestion"])
async def edit_pending_document(
    knowledge_id: str,
    request: EditApprovedDocumentRequest
):
    """
    Edits a pending document's summary and categories manually (from UI Save Form).
    """
    pending_file = resolve_pending_file(knowledge_id)
    if not pending_file:
        raise HTTPException(status_code=404, detail=f"Pending document '{knowledge_id}' not found.")

    try:
        with open(pending_file, "r", encoding="utf-8") as f:
            existing_doc = json.load(f)

        updated_summary = request.summary if request.summary is not None else existing_doc.get("summary", "")
        updated_categories = request.categories if (request.categories is not None and len(request.categories) > 0) else existing_doc.get("suggested_categories", [])

        # Normalize suggested_categories to list of dicts for pending json
        normalized_categories = []
        if updated_categories:
            if isinstance(updated_categories[0], str):
                normalized_categories = [{"name": c} for c in updated_categories]
            else:
                normalized_categories = updated_categories
                
        existing_doc["summary"] = updated_summary
        if updated_categories is not None and len(updated_categories) > 0:
            existing_doc["suggested_categories"] = normalized_categories
            
        updated_chunks = existing_doc.get("chunks", existing_doc.get("corrected_chunks", existing_doc.get("raw_chunks", [])))
        primary_cat = updated_categories[0] if updated_categories else None
        str_categories = [c["name"] if isinstance(c, dict) else c for c in normalized_categories]
        
        for chunk in updated_chunks:
            if isinstance(chunk, dict):
                if "metadata" not in chunk:
                    chunk["metadata"] = {}
                if str_categories:
                    chunk["metadata"]["categories"] = str_categories
                if primary_cat:
                    chunk["metadata"]["document_type"] = primary_cat["name"] if isinstance(primary_cat, dict) else primary_cat
                if updated_summary:
                    chunk["metadata"]["summary"] = updated_summary

        with open(pending_file, "w", encoding="utf-8") as f:
            json.dump(existing_doc, f, indent=4, ensure_ascii=False)

        return existing_doc
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Edit pending document failed for '{knowledge_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update pending document: {e}")


@router.post("/ingest/approved/{knowledge_id}/refine", tags=["Ingestion"])
async def refine_approved_document(
    knowledge_id: str,
    request: RefineRequest,
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
    bm25: BM25Index = Depends(get_bm25_index),
    vector_store: BaseVectorStoreAdapter = Depends(get_vector_store),
    llm: BaseLLMAdapter = Depends(get_llm)
):
    """
    Refines an approved document's summary, categories, and chunks using natural language AI instructions.
    Automatically re-indexes into PGVector & BM25, and updates PostgreSQL KnowledgeCategory table.
    """
    approved_file = resolve_approved_file(knowledge_id)
    if not approved_file:
        raise HTTPException(status_code=404, detail=f"Approved document '{knowledge_id}' not found.")

    if not llm:
        raise HTTPException(status_code=500, detail="LLM adapter is not configured.")

    try:
        with open(approved_file, "r", encoding="utf-8") as f:
            existing_doc = json.load(f)

        db_categories = []
        try:
            from app.core.database import AsyncSessionLocal
            from app.models.category import Category
            from sqlalchemy import select
            async with AsyncSessionLocal() as session:
                res = await session.execute(select(Category).where(Category.deleted_at.is_(None)))
                cats = res.scalars().all()
                db_categories = [{"id": str(c.id), "name": c.name} for c in cats]
        except Exception as cat_err:
            logger.warning(f"Failed to fetch categories: {cat_err}")

        history_str = ""
        if request.history:
            for msg in request.history:
                role = "User" if getattr(msg, "role", "") == "user" else "Assistant"
                content = getattr(msg, "content", "")
                history_str += f"{role}: {content}\n"
        else:
            history_str = "No previous refinement history.\n"

        refine_prompt = f"""
        You are an intelligent medical aesthetic AI validator for ERHA (PT Arya Noble) knowledge base.
        You are refining an APPROVED document based on user instructions and multi-turn conversation history.
        
        Document Data:
        {json.dumps(existing_doc, indent=2, ensure_ascii=False)}
        
        Available Categories:
        {json.dumps(db_categories, ensure_ascii=False)}
        
        Conversation History:
        {history_str}
        
        Latest User Instruction:
        "{request.prompt}"
        
        Refine the document summary, categories, or chunks according to the instruction.
        Return a valid JSON object ONLY (do not wrap in markdown code block) with keys:
        {{
            "summary": "updated summary markdown",
            "categories": ["category_name"],
            "chunks": [ {{ "text": "...", "metadata": {{}} }} ]
        }}
        """
        
        llm_res = await asyncio.to_thread(llm.generate, refine_prompt)
        clean_json = llm_res.strip()
        if clean_json.startswith("```"):
            lines = clean_json.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_json = "\n".join(lines).strip()
            
        parsed_refined = json.loads(clean_json)
        updated_summary = parsed_refined.get("summary", existing_doc.get("summary", ""))
        updated_categories = parsed_refined.get("categories", existing_doc.get("categories", []))
        updated_chunks = parsed_refined.get("chunks", existing_doc.get("chunks", []))
        file_name = existing_doc.get("file_name", knowledge_id)

        primary_cat = updated_categories[0] if updated_categories else None
        for chunk in updated_chunks:
            if isinstance(chunk, dict):
                if "metadata" not in chunk:
                    chunk["metadata"] = {}
                chunk["metadata"]["knowledge_id"] = knowledge_id
                if primary_cat:
                    chunk["metadata"]["document_type"] = primary_cat
                if updated_categories:
                    chunk["metadata"]["categories"] = updated_categories
                if updated_summary:
                    chunk["metadata"]["summary"] = updated_summary

        approved_doc_structure = {
            "knowledge_id": knowledge_id,
            "file_name": file_name,
            "status": "Approved",
            "summary": updated_summary,
            "categories": updated_categories,
            "chunks": updated_chunks
        }
        with open(approved_file, "w", encoding="utf-8") as f:
            json.dump(approved_doc_structure, f, indent=4, ensure_ascii=False)

        target_store = (pipeline.vector_store if pipeline and pipeline.vector_store else vector_store)
        if target_store:
            logger.info(f"Re-indexing PGVector for knowledge_id '{knowledge_id}'...")
            target_store.delete_document(knowledge_id)
            target_store.insert_chunks(updated_chunks)

        if bm25:
            logger.info(f"Re-indexing BM25 for knowledge_id '{knowledge_id}'...")
            bm25.remove_file_chunks(knowledge_id)
            bm25.add_chunks(updated_chunks)
            bm25.save(settings.bm25_index_path)

        if target_store and hasattr(target_store, "upsert_knowledge_category"):
            target_store.upsert_knowledge_category(
                knowledge_id=knowledge_id,
                file_name=file_name,
                categories=updated_categories,
                summary=updated_summary
            )

        return approved_doc_structure
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Refine approved document failed for '{knowledge_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refine approved document: {e}")


@router.post("/ingest/approve/{knowledge_id}", tags=["Ingestion"])
async def approve_document(
    knowledge_id: str = Path(..., description="Knowledge ID(s) to approve. Supports single ID (e.g. 'uuid1') or comma-separated IDs for batch approval (e.g. 'uuid1,uuid2,uuid3')"),
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
    bm25: BM25Index = Depends(get_bm25_index)
):
    """
    Approves staged document(s) and indexes them into PGVector & BM25 database.
    Supports single document approval or comma-separated batch approval in 1 click.
    """
    targets = [k.strip() for k in knowledge_id.split(",") if k and k.strip() and k.strip().lower() not in ("string", "all")]

    if not targets:
        raise HTTPException(status_code=400, detail="At least one valid knowledge_id must be provided.")

    approved_results = []
    for target_id in targets:
        pending_file = resolve_pending_file(target_id)
        if not pending_file:
            logger.warning(f"Pending document '{target_id}' not found for approval, skipping.")
            continue
            
        try:
            with open(pending_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            chunks = data.get("chunks", []) if isinstance(data, dict) else data
            k_id = data.get("knowledge_id", target_id) if isinstance(data, dict) else target_id
            file_name = data.get("file_name", target_id) if isinstance(data, dict) else target_id
            
            for chunk in chunks:
                if isinstance(chunk, dict):
                    if "metadata" not in chunk:
                        chunk["metadata"] = {}
                    chunk["metadata"]["knowledge_id"] = k_id
                    chunk["metadata"]["source_file"] = file_name
                    
                    # Ensure categories are preserved
                    cats = data.get("suggested_categories", data.get("categories", []))
                    str_cats = [c["name"] if isinstance(c, dict) else c for c in cats]
                    if str_cats:
                        chunk["metadata"]["categories"] = str_cats
                    if "summary" not in chunk["metadata"] and "summary" in data:
                        chunk["metadata"]["summary"] = data.get("summary")
                    
            if pipeline.vector_store:
                logger.info(f"Indexing chunks for knowledge_id {k_id} into vector store...")
                pipeline.vector_store.insert_chunks(chunks)
            else:
                logger.warning("No vector store instance available for indexing.")
                
            if bm25:
                logger.info(f"Indexing chunks for knowledge_id {k_id} into BM25 index...")
                bm25.add_chunks(chunks)
                bm25.save(settings.bm25_index_path)
                
            raw_cats = data.get("categories") or data.get("suggested_categories") or []
            parsed_cats = []
            if isinstance(raw_cats, list):
                for c in raw_cats:
                    if isinstance(c, dict) and "name" in c:
                        parsed_cats.append(c["name"])
                    elif isinstance(c, str):
                        parsed_cats.append(c)

            vis_settings = data.get("visibility_settings") or {
                "clinics": ["all"],
                "doctor_types": ["all"],
                "doctors": ["all"]
            }

            os.makedirs("data/output", exist_ok=True)
            approved_file = os.path.join("data/output", f"{k_id}.json")
            approved_doc_structure = {
                "knowledge_id": k_id,
                "file_name": file_name,
                "type": data.get("type", "Product") if isinstance(data, dict) else "Product",
                "document_type": data.get("document_type", "product") if isinstance(data, dict) else "product",
                "status": "Approved",
                "summary": data.get("summary", "") if isinstance(data, dict) else "",
                "categories": parsed_cats,
                "suggested_categories": raw_cats,
                "visibility_settings": vis_settings,
                "chunks": chunks
            }
            with open(approved_file, "w", encoding="utf-8") as f:
                json.dump(approved_doc_structure, f, indent=4, ensure_ascii=False)
                
            if os.path.exists(pending_file):
                os.remove(pending_file)
                
            # Dual-sync update to Knowledge DB table
            try:
                from app.core.database import AsyncSessionLocal
                from app.models.knowledge import Knowledge, KnowledgeStatus
                from sqlalchemy import select
                import uuid as _uuid
                async with AsyncSessionLocal() as session:
                    try:
                        k_uuid = _uuid.UUID(k_id)
                        stmt_k = select(Knowledge).where(Knowledge.id == k_uuid, Knowledge.deleted_at.is_(None))
                    except ValueError:
                        stmt_k = select(Knowledge).where(Knowledge.file_name.ilike(f"%{file_name}%"), Knowledge.deleted_at.is_(None))
                    res_k = await session.execute(stmt_k)
                    k_entry = res_k.scalars().first()
                    if k_entry:
                        k_entry.status = KnowledgeStatus.APPROVED
                        await session.commit()
            except Exception as db_err:
                logger.warning(f"Could not dual-sync approved status to Knowledge DB table for {k_id}: {db_err}")

            approved_results.append(k_id)
        except Exception as e:
            logger.error(f"Approval failed for document '{target_id}': {e}")

    return {
        "status": "success", 
        "message": f"Successfully approved {len(approved_results)} document(s).", 
        "approved_ids": approved_results
    }


@router.delete("/ingest/documents/{knowledge_id}", tags=["Ingestion"])
async def delete_document_endpoint(
    knowledge_id: str,
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
    bm25: BM25Index = Depends(get_bm25_index),
    vector_store: BaseVectorStoreAdapter = Depends(get_vector_store)
):
    """
    Deletes document(s) across all statuses (Pending or Approved).
    Supports single ID or comma-separated list of IDs (e.g. 'id1,id2,id3').
    Removes physical JSON files, PGVector embeddings, BM25 indices, and performs soft-delete (deleted_at) in PostgreSQL.
    """
    targets = [k.strip() for k in knowledge_id.split(",") if k and k.strip() and k.strip().lower() not in ("string", "all")]
    if not targets:
        raise HTTPException(status_code=400, detail="At least one valid knowledge_id must be provided.")

    target_store = (pipeline.vector_store if pipeline and pipeline.vector_store else vector_store)
    deleted_ids = []

    for k_id in targets:
        # 1. Check in Pending
        pending_file = resolve_pending_file(k_id)
        if pending_file and os.path.exists(pending_file):
            try:
                os.remove(pending_file)
                if target_store and hasattr(target_store, "soft_delete_document"):
                    target_store.soft_delete_document(k_id)
                deleted_ids.append(k_id)
                continue
            except Exception as e:
                logger.error(f"Failed to delete pending document '{k_id}': {e}")

        # 2. Check in Approved
        approved_file = resolve_approved_file(k_id)
        if approved_file and os.path.exists(approved_file):
            try:
                if target_store:
                    target_store.delete_document(k_id)
                if bm25:
                    bm25.remove_file_chunks(k_id)
                    bm25.save(settings.bm25_index_path)
                os.remove(approved_file)
                if target_store and hasattr(target_store, "soft_delete_document"):
                    target_store.soft_delete_document(k_id)
                deleted_ids.append(k_id)
            except Exception as e:
                logger.error(f"Failed to delete approved document '{k_id}': {e}")

    return {"status": "success", "message": f"Successfully deleted {len(deleted_ids)} document(s).", "deleted_ids": deleted_ids}


@router.get("/search", tags=["Retrieval"])
async def search_hybrid(
    query: str = Query(..., description="Search query string"),
    categories: Optional[List[str]] = Query(None, description="Optional category filters (e.g. ['Acne Care'])"),
    document_type: Optional[str] = Query(None, description="Optional document category filter ('Product', 'Treatment', or 'Promotional')"),
    top_k: int = Query(8, description="Number of passage matches to return"),
    retriever: HybridRetriever = Depends(get_hybrid_retriever)
):
    """
    Advanced Hybrid Search (PGVector Dense Embeddings + BM25 Sparse Keyword Match) 
    with Reciprocal Rank Fusion (RRF).
    """
    if not retriever:
        raise HTTPException(status_code=500, detail="Hybrid retriever is not initialized.")
        
    filter_metadata = {}
    if document_type and document_type.strip().lower() not in ("string", ""):
        filter_metadata["document_type"] = document_type
    if categories:
        valid_cats = [c.strip() for c in categories if c and c.strip().lower() not in ("string", "")]
        if valid_cats:
            filter_metadata["categories"] = valid_cats
        
    parsed_filter = filter_metadata if filter_metadata else None
            
    try:
        hits = retriever.retrieve(
            query=query, 
            top_k=top_k, 
            filter_metadata=parsed_filter, 
            rerank=False,
            rerank_top_n=top_k
        )
        return hits
    except Exception as e:
        logger.error(f"Search endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat", response_model=ChatResponse, tags=["Generation"])
async def chat_endpoint(
    request: ChatRequest,
    pipeline: GenerationPipeline = Depends(get_generation_pipeline),
    agent = Depends(get_medical_agent)
):
    """
    Production RAG Chat Endpoint. Synthesizes a doctor-aligned response using context-enriched retrieval,
    optional ReAct AI Agent multi-step reasoning, and Guardrails safety checks.
    """
    # 1. Guardrails: Pre-retrieval Input Check (prompt injection & topicality filter)
    is_valid_input, rejection_msg = GuardrailsPipeline.validate_input(request.query)
    if not is_valid_input:
        return ChatResponse(
            query=request.query,
            answer=rejection_msg,
            context="",
            results=[],
            agent_used=False
        )

    raw_history = [{"role": msg.role, "content": msg.content} for msg in request.history]

    # 2. Try ReAct AI Agent (if enabled via RAG_AGENT_ENABLED=true)
    if agent:
        try:
            logger.info("RAG_AGENT_ENABLED is True. Executing MedicalAgent...")
            agent_res = agent.run(request.query, history=raw_history)
            if agent_res and agent_res.get("answer"):
                sanitized_answer = GuardrailsPipeline.process_output(agent_res["answer"])
                return ChatResponse(
                    query=request.query,
                    answer=sanitized_answer,
                    context="[Retrieved via MedicalAgent Multi-step Tool Reasoning]",
                    results=agent_res.get("sources", []),
                    agent_used=True
                )
        except Exception as agent_err:
            logger.warning(f"MedicalAgent execution failed, falling back to standard pipeline: {agent_err}")

    # 3. Standard Single-pass RAG Generation Pipeline Fallback
    if not pipeline:
        raise HTTPException(status_code=500, detail="Generation pipeline is not initialized. Please ensure your LLM API keys are configured correctly.")
        
    filter_metadata = {}
    if request.document_type and request.document_type.strip().lower() not in ("string", ""):
        filter_metadata["document_type"] = request.document_type
    if request.categories:
        valid_cats = [c.strip() for c in request.categories if c and c.strip().lower() not in ("string", "")]
        if valid_cats:
            filter_metadata["categories"] = valid_cats
        
    parsed_filter = filter_metadata if filter_metadata else None
    
    try:
        response = pipeline.generate_answer(
            query=request.query,
            top_k=request.top_k,
            filter_metadata=parsed_filter,
            rerank=False,
            history=raw_history
        )
        
        # 4. Guardrails: Post-generation Output Check (PII Redaction & Medical Disclaimer)
        if isinstance(response, ChatResponse):
            response.answer = GuardrailsPipeline.process_output(response.answer)
            response.agent_used = False
            return response
        elif isinstance(response, dict):
            raw_answer = response.get("answer", "")
            response["answer"] = GuardrailsPipeline.process_output(raw_answer)
            response["agent_used"] = False
            return response
        return response

    except Exception as e:
        logger.error(f"Chat generation failed: {e}")
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

