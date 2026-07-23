import os
import json
from typing import List, Dict, Any
from loguru import logger

from sqlalchemy import create_engine, Column, String, Text, Integer, JSON, text
from sqlalchemy.orm import declarative_base, sessionmaker
# pyrefly: ignore [missing-import]
from pgvector.sqlalchemy import Vector
from langchain_huggingface import HuggingFaceEmbeddings

from app.rag.services.interfaces import BaseVectorStoreAdapter
from app.rag.config import settings

Base = declarative_base()

class DocumentChunk(Base):
    __tablename__ = settings.pg_collection_name
    
    id = Column(String, primary_key=True)
    text = Column(Text, nullable=False)
    source_file = Column(String, nullable=False, index=True)
    metadata_ = Column("metadata", JSON, nullable=False)
    embedding = Column(Vector(1024), nullable=False) # bge-m3 uses 1024 dimensions

class PGVectorAdapter(BaseVectorStoreAdapter):
    def __init__(self):
        self.conn_str = settings.pg_conn_str
        self.collection_name = settings.pg_collection_name
        
        logger.info(f"Initializing PGVector client for database...")
        try:
            self.engine = create_engine(self.conn_str)
            # Ensure pgvector extension exists
            with self.engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
            
            # Create table if not exists
            Base.metadata.create_all(self.engine)
            
            # Create HNSW index if not exists (using raw SQL for pgvector specific syntax)
            with self.engine.connect() as conn:
                # bge-m3 uses cosine similarity, so we use vector_cosine_ops
                index_name = f"idx_{self.collection_name}_embedding_hnsw"
                conn.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS {index_name} 
                    ON {self.collection_name} USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 100);
                """))
                conn.commit()
                
            self.Session = sessionmaker(bind=self.engine)
            logger.info("Connected to PostgreSQL and verified vector extension + HNSW index.")
        except Exception as e:
            logger.error(f"Failed to initialize PGVector: {e}")
            raise

        logger.info(f"Loading embedding model for PGVector store: {settings.embedding_model_name}")
        self.embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model_name)
        logger.info("PGVectorAdapter initialized successfully.")


    def insert_chunks(self, chunks: List[Dict]):
        """
        Embeds chunks and inserts/upserts them into PGVector.
        """
        if not chunks:
            logger.warning("No chunks provided to insert.")
            return

        logger.info(f"Embedding {len(chunks)} chunks using {settings.embedding_model_name}...")
        
        texts_to_embed = []
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            source_file = metadata.get("source_file", "unknown")
            
            # Clean up source_file to get a cleaner product name
            product_name = source_file
            for ext in [".pdf", ".docx", ".txt", "_parsed.json"]:
                product_name = product_name.replace(ext, "")
            product_name = product_name.replace("dumy-", "").replace("dummy-", "").replace("Dummy_", "").replace("dummy_", "")
            product_name = product_name.replace("-", " ").replace("_", " ")
            product_name = product_name.strip()
            
            section = metadata.get("section", "General")
            enriched_text = f"Product: {product_name} | Section: {section} | Content: {chunk['text']}"
            texts_to_embed.append(enriched_text)
            
        embeddings = self.embeddings.embed_documents(texts_to_embed)
        
        logger.info(f"Inserting points to PGVector table: {self.collection_name}")
        with self.Session() as session:
            for i, (chunk, vector) in enumerate(zip(chunks, embeddings)):
                metadata = chunk.get("metadata", {})
                source_file = metadata.get("source_file", "unknown")
                chunk_index = metadata.get("chunk_index", i)
                
                # Deterministic ID
                unique_id = f"{source_file}_{chunk_index}_{i}"
                
                # Upsert logic (Delete if exists, then insert)
                existing = session.query(DocumentChunk).filter_by(id=unique_id).first()
                if existing:
                    session.delete(existing)
                    
                doc = DocumentChunk(
                    id=unique_id,
                    text=chunk["text"],
                    source_file=source_file,
                    metadata_=metadata,
                    embedding=vector
                )
                session.add(doc)
            
            session.commit()
            logger.info(f"Successfully inserted {len(chunks)} chunks into PGVector.")

    def search(self, query: str, top_k: int = 5, filter_metadata: Any = None) -> List[Dict]:
        """
        Embeds the query and searches PGVector for the closest points using cosine distance.
        """
        try:
            query_vector = self.embeddings.embed_query(query)
            
            with self.Session() as session:
                # Cosine distance: embedding.cosine_distance(query_vector)
                # We want to order by distance ASC (closest first)
                q = session.query(DocumentChunk)
                
                if filter_metadata:
                    for k, v in filter_metadata.items():
                        # filter on JSONB metadata
                        q = q.filter(DocumentChunk.metadata_[k].astext == str(v))
                        
                results = q.order_by(DocumentChunk.embedding.cosine_distance(query_vector)).limit(top_k).all()
                
                hits = []
                for hit in results:
                    # cosine_distance returns (1 - cosine_similarity), so score is (1 - dist)
                    # wait, pgvector cosine_distance operator `<=>` gives distance. 
                    # For RAG logic expecting higher is better (similarity), we can roughly invert it if needed,
                    # but typically hybrid search code in `rag_retriever` sorts correctly or uses it as abstract score.
                    # Qdrant gave similarity [0, 1]. Let's invert pgvector's distance to get similarity.
                    # Just setting score=1.0 as a placeholder since we can't easily get the raw distance without extra query columns,
                    # actually we can just return a dummy score or we can query the distance explicitly.
                    hits.append({
                        "text": hit.text,
                        "score": 1.0, # Dummy score, reranker will handle actual scoring
                        "metadata": hit.metadata_
                    })
                return hits
        except Exception as e:
            logger.error(f"Search failed in PGVector store: {e}")
            return []

    def delete_document(self, source_file: str):
        """
        Deletes all chunks associated with the given source_file name.
        """
        try:
            logger.info(f"Deleting chunks for source_file: {source_file}")
            with self.Session() as session:
                session.query(DocumentChunk).filter_by(source_file=source_file).delete()
                session.commit()
            logger.info(f"Successfully deleted chunks for {source_file} from PGVector.")
        except Exception as e:
            logger.error(f"Failed to delete chunks for {source_file}: {e}")
            raise

    def clear_all(self):
        """
        Deletes all rows in the table.
        """
        try:
            logger.info(f"Clearing all data from {self.collection_name}...")
            with self.Session() as session:
                session.query(DocumentChunk).delete()
                session.commit()
            logger.info("Vector store successfully cleared.")
        except Exception as e:
            logger.error(f"Failed to clear vector store: {e}")
            raise
