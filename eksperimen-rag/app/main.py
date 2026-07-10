import os
import json
import uvicorn
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from loguru import logger

from evaluation.logger import setup_logging
from ingestion.pipeline import IngestionPipeline
from core.adapters import AdapterFactory

# Initialize FastAPI app
app = FastAPI(
    title="Arya Noble - RAG API (Sprint 3)",
    description="API for Document Ingestion, Hybrid Search (Dense + Sparse), Cross-Encoder Reranking, and Retrieval Evaluation",
    version="0.3.0"
)

# Add CORS Middleware to prevent browser CORS block issues
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Logging
setup_logging("INFO")

# Global variables for pipeline components
ingestion_pipeline = None
vector_store = None
bm25_index = None
reranker = None
hybrid_retriever = None
llm_adapter = None
generation_pipeline = None

@app.on_event("startup")
async def startup_event():
    global ingestion_pipeline, vector_store, bm25_index, reranker, hybrid_retriever, llm_adapter, generation_pipeline
    
    # 1. Initialize Qdrant Vector Store
    logger.info("Initializing Vector Store Adapter...")
    try:
        vector_store = AdapterFactory.get_vector_store()
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {e}")
        vector_store = None
        
    # 2. Initialize Ingestion Pipeline
    logger.info("Initializing Sprint 3 Ingestion Pipeline...")
    ingestion_pipeline = IngestionPipeline(vector_store=vector_store)
    
    # 3. Initialize BM25 Index
    logger.info("Initializing BM25 Index...")
    from retrieval.bm25 import BM25Index
    from configs.settings import settings
    bm25_index = BM25Index()
    try:
        bm25_index.load(settings.bm25_index_path)
    except Exception as e:
        logger.error(f"Failed to load BM25 index: {e}")
        
    # 4. Initialize Cross-Encoder Reranker
    logger.info("Initializing Reranker...")
    from retrieval.reranker import Reranker
    try:
        reranker = Reranker(model_name=settings.reranker_model_name)
    except Exception as e:
        logger.error(f"Failed to initialize reranker: {e}")
        reranker = None
        
    # 5. Initialize Hybrid Retriever
    logger.info("Initializing Hybrid Retriever...")
    from retrieval.retriever import HybridRetriever
    try:
        hybrid_retriever = HybridRetriever(
            vector_store=vector_store,
            bm25_index=bm25_index,
            reranker=reranker
        )
    except Exception as e:
        logger.error(f"Failed to initialize hybrid retriever: {e}")
        hybrid_retriever = None

    # 6. Initialize LLM Adapter and Generation Pipeline
    logger.info("Initializing LLM Adapter and Generation Pipeline...")
    from generation.generator import GenerationPipeline
    try:
        llm_adapter = AdapterFactory.get_llm()
    except Exception as e:
        logger.warning(f"Failed to initialize LLM Adapter (check your API keys): {e}")
        llm_adapter = None

    if hybrid_retriever and llm_adapter:
        try:
            generation_pipeline = GenerationPipeline(retriever=hybrid_retriever, llm_adapter=llm_adapter)
        except Exception as e:
            logger.error(f"Failed to initialize Generation Pipeline: {e}")
            generation_pipeline = None
    else:
        generation_pipeline = None
        
    logger.info("Sprint 4 Pipeline Initialized Successfully.")

@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint to verify the API is running and AI-ready.
    """
    global vector_store
    
    # Fallback to the Factory singleton if global namespace was shadowed/reset
    if vector_store is None:
        try:
            vector_store = AdapterFactory.get_vector_store()
        except Exception as e:
            logger.error(f"Health check fallback failed to get vector store: {e}")
            
    return {
        "status": "ok",
        "vector_store_initialized": vector_store is not None,
        "bm25_index_size": len(bm25_index.chunks) if bm25_index else 0,
        "reranker_initialized": reranker is not None,
        "hybrid_retriever_initialized": hybrid_retriever is not None,
        "llm_initialized": llm_adapter is not None,
        "generation_pipeline_initialized": generation_pipeline is not None
    }

@app.post("/ingest", tags=["Ingestion"])
async def ingest_document(
    file: UploadFile = File(...),
    index: bool = Query(True, description="Whether to index parsed chunks into Qdrant & BM25")
):
    """
    API endpoint to upload and ingest a document.
    Outputs the processed JSON to data/output/ and optionally indexes it in Qdrant & BM25.
    """
    try:
        # Save file temporarily
        os.makedirs("data/temp", exist_ok=True)
        file_path = f"data/temp/{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())
            
        # Temporarily configure indexing for this request
        original_store = ingestion_pipeline.vector_store
        if not index:
            ingestion_pipeline.vector_store = None
            
        # Ingest (Docling -> Custom Chunker -> JSON -> Qdrant if enabled)
        output_file = ingestion_pipeline.ingest_file(file_path)
        
        # Restore original vector store mapping
        ingestion_pipeline.vector_store = original_store
        
        # If output_file was generated and index=True, index in BM25 too
        if output_file and index and bm25_index:
            try:
                from configs.settings import settings
                with open(output_file, 'r', encoding='utf-8') as f_json:
                    enriched_chunks = json.load(f_json)
                logger.info(f"Indexing chunks from {file.filename} into BM25 index...")
                bm25_index.add_chunks(enriched_chunks)
                bm25_index.save(settings.bm25_index_path)
                logger.info(f"Successfully indexed chunks from {file.filename} into BM25.")
            except Exception as bm25_err:
                logger.error(f"Failed to index chunks into BM25: {bm25_err}")
        
        # Cleanup temp file
        try:
            import gc
            gc.collect()
            os.remove(file_path)
        except Exception as cleanup_err:
            logger.warning(f"Could not delete temporary file {file_path}: {cleanup_err}")
        
        if output_file:
            return {
                "message": f"Successfully ingested {file.filename}",
                "output_json": output_file,
                "indexed": index and vector_store is not None
            }
        else:
            raise HTTPException(status_code=500, detail="Ingestion failed. Check logs.")
    except Exception as e:
        logger.error(f"Failed to process document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search", tags=["Retrieval"])
async def search_hybrid(
    query: str = Query(..., description="Query string to search for"),
    top_k: int = Query(5, description="Number of final matches to return"),
    rerank: bool = Query(True, description="Whether to apply Cross-Encoder rerank"),
    document_type: Optional[str] = Query(None, description="Filter by document type (e.g. product, treatment, faq, promotion, sop)"),
    section: Optional[str] = Query(None, description="Filter by section name (e.g. ACTIVE INGREDIENTS, HOW TO USE)"),
    confidence_threshold: Optional[float] = Query(None, description="Optional custom confidence threshold (0.0 to 1.0)")
):
    """
    Advanced search endpoint using Hybrid Search (Dense + Sparse/BM25) with RRF 
    and Cross-Encoder Reranking, supporting explicit metadata filtering by document type and section.
    """
    if not hybrid_retriever:
        raise HTTPException(status_code=500, detail="Hybrid retriever is not initialized.")
        
    filter_metadata = {}
    if document_type and document_type.strip().lower() not in ("string", ""):
        filter_metadata["document_type"] = document_type
    if section and section.strip().lower() not in ("string", ""):
        filter_metadata["section"] = section
        
    parsed_filter = filter_metadata if filter_metadata else None
            
    try:
        hits = hybrid_retriever.retrieve(
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

class EvaluationItem(BaseModel):
    query: str = Field(..., description="Evaluation query string")
    ground_truth: Dict[str, Any] = Field(..., description="Expected metadata matches, e.g., {'source_file': 'x.pdf'}")

@app.post("/search/evaluate", tags=["Retrieval"])
async def evaluate_retrieval_endpoint(dataset: List[EvaluationItem]):
    """
    Evaluates search pipeline metrics (Hit Rate and MRR) over a test dataset.
    Dataset items format:
    [
      {
        "query": "kandungan ERHA Acne Clear Gel",
        "ground_truth": {
          "source_file": "dumy-ERHA-Acne-Clear-Gel.docx",
          "section": "ACTIVE INGREDIENTS"
        }
      }
    ]
    """
    if not hybrid_retriever:
        raise HTTPException(status_code=500, detail="Hybrid retriever is not initialized.")
    try:
        # Convert Pydantic models back to raw dicts for evaluator
        raw_dataset = [{"query": item.query, "ground_truth": item.ground_truth} for item in dataset]
        from retrieval.evaluation import RetrievalEvaluator
        metrics = RetrievalEvaluator.evaluate_dataset(
            retriever=hybrid_retriever,
            dataset=raw_dataset,
            top_k=5,
            rerank=True,
            rerank_top_n=3
        )
        return metrics
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the sender, e.g. 'user' or 'assistant'")
    content: str = Field(..., description="Content of the message")

class ChatRequest(BaseModel):
    query: str = Field(..., description="The user's query/message")
    top_k: int = Field(5, description="Number of final matches to retrieve")
    rerank: bool = Field(True, description="Whether to apply Cross-Encoder rerank")
    document_type: Optional[str] = Field(None, description="Filter by document type (e.g. product, treatment, faq, promotion, sop)")
    section: Optional[str] = Field(None, description="Filter by section name (e.g. ACTIVE INGREDIENTS, HOW TO USE)")
    confidence_threshold: Optional[float] = Field(None, description="Optional custom confidence threshold")
    history: List[ChatMessage] = Field(default=[], description="Chat history context")

class ChatResponse(BaseModel):
    query: str
    answer: str
    context: str
    results: List[Dict[str, Any]]

@app.post("/chat", response_model=ChatResponse, tags=["Generation"])
async def chat_endpoint(request: ChatRequest):
    """
    RAG chat endpoint. Generates a doctor-aligned response using context-enriched retrieval and LLM.
    Supports filters (document_type, section), confidence thresholds, and multi-turn chat history.
    """
    if not generation_pipeline:
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
        response = generation_pipeline.generate_answer(
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

if __name__ == "__main__":
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
