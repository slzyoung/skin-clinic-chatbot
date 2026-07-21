import os
import asyncio
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from loguru import logger
from app.models.config import AppConfig
from app.core.database import AsyncSessionLocal

async def get_dynamic_embeddings(session: Optional[AsyncSession] = None):
    """
    Dynamically returns a LangChain Embeddings instance based on AppConfig DB settings or env vars.
    Supports:
    - HuggingFace / Local (e.g. BAAI/bge-m3)
    - OpenAI (e.g. text-embedding-3-small)
    - Gemini / Google
    """
    provider = os.getenv("EMBEDDING_PROVIDER", "huggingface").lower()
    model_name = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-m3")
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")

    if session is not None:
        try:
            res_provider = await session.execute(select(AppConfig).where(AppConfig.key == "EMBEDDING_PROVIDER"))
            provider_rec = res_provider.scalar_one_or_none()
            if provider_rec and provider_rec.value:
                provider = provider_rec.value.lower()

            res_model = await session.execute(select(AppConfig).where(AppConfig.key == "EMBEDDING_MODEL_NAME"))
            model_rec = res_model.scalar_one_or_none()
            if model_rec and model_rec.value:
                model_name = model_rec.value

            res_key = await session.execute(select(AppConfig).where(AppConfig.key == "LLM_API_KEY"))
            key_rec = res_key.scalar_one_or_none()
            if key_rec and key_rec.value:
                api_key = key_rec.value
        except Exception as e:
            logger.warning(f"Could not read embedding config from DB, using defaults: {e}")

    logger.info(f"Initializing embedding model: provider='{provider}', model_name='{model_name}'")

    if provider in ["huggingface", "local"]:
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name=model_name)

    elif provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        kwargs = {"model": model_name}
        if api_key:
            kwargs["api_key"] = api_key
        return OpenAIEmbeddings(**kwargs)

    elif provider in ["google", "gemini"]:
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            return GoogleGenerativeAIEmbeddings(model=model_name, google_api_key=api_key)
        except ImportError:
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(
                model=model_name,
                api_key=api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )

    else:
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name=model_name)


async def get_embedding_dimension(embeddings) -> int:
    """Returns the output vector dimension for an Embeddings instance."""
    try:
        sample = await embeddings.aembed_query("test dimension sync")
        return len(sample)
    except Exception:
        sample = embeddings.embed_query("test dimension sync")
        return len(sample)


async def reindex_all_chunks(embeddings):
    """Re-calculates embeddings for all existing KnowledgeChunk records in batches."""
    from app.models.knowledge import KnowledgeChunk
    logger.info("Starting background re-indexing of all existing knowledge chunks...")
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(KnowledgeChunk))
            chunks = result.scalars().all()
            if not chunks:
                logger.info("No existing knowledge chunks found to re-index.")
                return

            logger.info(f"Re-indexing {len(chunks)} chunks with new embedding model...")
            batch_size = 50
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                texts = [c.content for c in batch]
                try:
                    new_vectors = await embeddings.aembed_documents(texts)
                except Exception:
                    new_vectors = [embeddings.embed_query(t) for t in texts]

                for chunk, vec in zip(batch, new_vectors):
                    chunk.embedding = vec
                await session.commit()
                logger.info(f"Re-indexed batch {i // batch_size + 1}/{(len(chunks) - 1) // batch_size + 1}")

            logger.info("Successfully completed background re-indexing of all knowledge chunks!")
        except Exception as e:
            logger.error(f"Error during background chunk re-indexing: {e}")
            await session.rollback()


async def ensure_embedding_dimension_synced(session: Optional[AsyncSession] = None):
    """
    Checks the active embedding model's dimension against PostgreSQL's knowledge_chunk.embedding column.
    If dimensions differ, alters table column type, drops/recreates HNSW index, and re-indexes existing chunks.
    """
    should_close = False
    if session is None:
        session = AsyncSessionLocal()
        should_close = True

    try:
        embeddings = await get_dynamic_embeddings(session)
        target_dim = await get_embedding_dimension(embeddings)

        query = text("""
            SELECT atttypmod 
            FROM pg_attribute 
            WHERE attrelid = 'knowledge_chunk'::regclass 
              AND attname = 'embedding';
        """)
        res = await session.execute(query)
        current_dim = res.scalar_one_or_none()

        logger.info(f"Embedding dimension check: target_dim={target_dim}, current_db_dim={current_dim}")

        if current_dim is not None and current_dim != target_dim:
            logger.warning(
                f"Embedding dimension mismatch detected! DB column has {current_dim} dimensions, "
                f"but configured model produces {target_dim} dimensions. Syncing database schema..."
            )
            # 1. Drop HNSW index
            await session.execute(text("DROP INDEX IF EXISTS ix_knowledge_chunk_embedding;"))

            # 2. Alter column vector dimension
            await session.execute(text(f"ALTER TABLE knowledge_chunk ALTER COLUMN embedding TYPE vector({target_dim});"))

            # 3. Re-create HNSW index with new dimension
            await session.execute(text("""
                CREATE INDEX ix_knowledge_chunk_embedding 
                ON knowledge_chunk USING hnsw (embedding vector_cosine_ops) 
                WITH (m = 16, ef_construction = 64);
            """))
            await session.commit()
            logger.info(f"Database vector column successfully updated to vector({target_dim})!")

            # 4. Trigger background re-indexing of existing chunks
            asyncio.create_task(reindex_all_chunks(embeddings))

    except Exception as e:
        logger.error(f"Error during embedding dimension sync check: {e}")
        await session.rollback()
    finally:
        if should_close:
            await session.close()
