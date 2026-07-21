import uuid
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.rag.core.interfaces import BaseVectorStoreAdapter
from app.models.knowledge import KnowledgeChunk

class PgVectorAdapter(BaseVectorStoreAdapter):
    def __init__(self, session: AsyncSession, embeddings_model):
        self.session = session
        self.embeddings_model = embeddings_model

    async def insert_chunks(self, chunks: List[Dict]):
        objects = []
        for chunk in chunks:
            embedding = chunk.get("embedding")
            if not embedding:
                embedding = await self.embeddings_model.aembed_query(chunk["content"])
                
            k_id = chunk["knowledge_id"]
            if isinstance(k_id, str):
                k_id = uuid.UUID(k_id)

            obj = KnowledgeChunk(
                knowledge_id=k_id,
                chunk_index=chunk["chunk_index"],
                content=chunk["content"],
                embedding=embedding,
                metadata_=chunk.get("metadata", {})
            )
            objects.append(obj)
            
        self.session.add_all(objects)
        await self.session.commit()

    async def search(self, query: str, top_k: int = 5, filter_metadata: Any = None) -> List[Dict]:
        query_embedding = await self.embeddings_model.aembed_query(query)
        
        stmt = select(KnowledgeChunk).order_by(
            KnowledgeChunk.embedding.cosine_distance(query_embedding)
        ).limit(top_k)
        
        result = await self.session.execute(stmt)
        chunks = result.scalars().all()
        
        return [
            {
                "id": str(c.knowledge_id),
                "chunk_index": c.chunk_index,
                "content": c.content,
                "metadata": c.metadata_
            } for c in chunks
        ]
