from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.rag.generation.factory import get_dynamic_llm
from app.rag.retrieval.retriever import HybridRetriever

async def generate_document_summary(
    session: AsyncSession,
    knowledge_id: str,
    embeddings
) -> str:
    """
    Retrieves document chunks and generates a structured executive markdown summary using the active LLM.
    """
    try:
        llm = await get_dynamic_llm(session)
        retriever = HybridRetriever(session=session, embeddings_model=embeddings, reranker=None)
        
        results = await retriever.retrieve(
            query="Provide a comprehensive summary of this document, including key points and important details.",
            top_k=5,
            filter_metadata={"knowledge_id": str(knowledge_id)}
        )
        
        if results:
            context = "\n\n".join([r.get("content", "") for r in results])
            prompt = f"Provide a clear, well-structured executive summary of the following document in markdown format:\n\n{context}"
            res = await llm.ainvoke(prompt)
            return res.content if hasattr(res, 'content') else str(res)
        
        return "Document successfully parsed and indexed."
    except Exception as e:
        logger.warning(f"Failed to generate AI summary for {knowledge_id}: {e}")
        return "Document ingested and ready for review."
