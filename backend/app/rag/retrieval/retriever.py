import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.knowledge import KnowledgeChunk
from loguru import logger

class HybridRetriever:
    def __init__(self, session: AsyncSession, embeddings_model, reranker=None):
        self.session = session
        self.embeddings_model = embeddings_model
        self.reranker = reranker

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        rerank: bool = True,
        rerank_top_n: int = 3,
        confidence_threshold: Optional[float] = None
    ) -> List[Dict]:
        
        candidate_count = max(20, top_k * 2)

        # 1. Semantic Search (Dense)
        query_embedding = await self.embeddings_model.aembed_query(query)
        dense_stmt = select(KnowledgeChunk).order_by(
            KnowledgeChunk.embedding.cosine_distance(query_embedding)
        ).limit(candidate_count)

        if filter_metadata:
            for k, v in filter_metadata.items():
                if k == "knowledge_id":
                    dense_stmt = dense_stmt.where(KnowledgeChunk.knowledge_id == v)
                else:
                    dense_stmt = dense_stmt.where(KnowledgeChunk.metadata_[k].astext == str(v))
                
        dense_results = await self.session.execute(dense_stmt)
        dense_chunks = dense_results.scalars().all()

        # 2. Full-Text Search (Sparse)
        sparse_stmt = select(KnowledgeChunk).where(
            KnowledgeChunk.searchable_content.op('@@')(func.websearch_to_tsquery('english', query))
        ).order_by(
            func.ts_rank(KnowledgeChunk.searchable_content, func.websearch_to_tsquery('english', query)).desc()
        ).limit(candidate_count)

        if filter_metadata:
            for k, v in filter_metadata.items():
                if k == "knowledge_id":
                    sparse_stmt = sparse_stmt.where(KnowledgeChunk.knowledge_id == v)
                else:
                    sparse_stmt = sparse_stmt.where(KnowledgeChunk.metadata_[k].astext == str(v))

        sparse_results = await self.session.execute(sparse_stmt)
        sparse_chunks = sparse_results.scalars().all()

        # 3. Reciprocal Rank Fusion (RRF)
        rrf_k = 60
        scores = {}
        chunks_map = {}

        for rank, chunk in enumerate(dense_chunks):
            chunk_id = f"{chunk.knowledge_id}_{chunk.chunk_index}"
            chunks_map[chunk_id] = chunk
            scores[chunk_id] = 1.0 / (rrf_k + rank + 1)

        for rank, chunk in enumerate(sparse_chunks):
            chunk_id = f"{chunk.knowledge_id}_{chunk.chunk_index}"
            if chunk_id not in chunks_map:
                chunks_map[chunk_id] = chunk
                scores[chunk_id] = 0.0
            scores[chunk_id] += 1.0 / (rrf_k + rank + 1)

        sorted_chunk_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        top_candidates = [
            {
                "id": str(chunks_map[cid].knowledge_id),
                "chunk_index": chunks_map[cid].chunk_index,
                "content": chunks_map[cid].content,
                "metadata": chunks_map[cid].metadata_,
                "score": scores[cid]
            }
            for cid in sorted_chunk_ids[:candidate_count]
        ]

        if not top_candidates:
            return []

        # Filter by threshold if requested (before reranking)
        if confidence_threshold is not None:
            # We scale the RRF scores loosely, but normally thresholding is better done after reranking
            # We will rely on the reranker to output confidence if possible.
            pass

        # 4. Reranking (External)
        if rerank and self.reranker:
            top_candidates = await self.reranker.rerank(query, top_candidates, top_n=rerank_top_n)
        else:
            top_candidates = top_candidates[:top_k]

        return top_candidates
