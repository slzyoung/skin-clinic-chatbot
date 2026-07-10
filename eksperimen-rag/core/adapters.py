import os
import uuid
from typing import List, Dict, Any
from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_huggingface import HuggingFaceEmbeddings

from .interfaces import BaseLLMAdapter, BaseVectorStoreAdapter
from configs.settings import settings

# --- Qdrant Vector Store Adapter ---

class QdrantAdapter(BaseVectorStoreAdapter):
    def __init__(self):
        self.collection_name = settings.qdrant_collection_name
        url = settings.qdrant_url
        
        logger.info(f"Initializing Qdrant client with destination: {url}")
        if url == ":memory:":
            self.client = QdrantClient(location=":memory:")
        elif url.startswith("http://") or url.startswith("https://") or url.startswith("grpc://"):
            self.client = QdrantClient(url=url)
        else:
            # Local disk persistent storage
            parent_dir = os.path.dirname(os.path.abspath(url))
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            self.client = QdrantClient(path=url)
            
        logger.info(f"Loading embedding model for Qdrant store: {settings.embedding_model_name}")
        self.embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model_name)
        
        # Ensure collection exists at startup
        try:
            if not self.client.collection_exists(self.collection_name):
                logger.info(f"Creating collection {self.collection_name} in Qdrant...")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
                )
        except Exception as e:
            logger.error(f"Failed to check/create collection in Qdrant startup: {e}")
            
        logger.info("QdrantAdapter initialized successfully.")

    def insert_chunks(self, chunks: List[Dict]):
        """
        Embeds chunks and inserts/upserts them into Qdrant.
        Each chunk is a dict of the form:
        {
            "text": str,
            "metadata": Dict[str, Any]
        }
        """
        if not chunks:
            logger.warning("No chunks provided to insert.")
            return

        # Ensure collection exists
        try:
            if not self.client.collection_exists(self.collection_name):
                logger.info(f"Creating collection {self.collection_name} in Qdrant...")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
                )
        except Exception as e:
            logger.error(f"Failed to check/create collection in Qdrant: {e}")
            raise

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
        
        logger.info(f"Upserting points to Qdrant collection: {self.collection_name}")
        points = []
        for i, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            metadata = chunk.get("metadata", {})
            source_file = metadata.get("source_file", "unknown")
            chunk_index = metadata.get("chunk_index", i)
            
            # Generate deterministic UUID per chunk to avoid duplicates on re-ingestion
            namespace_dns = uuid.NAMESPACE_DNS
            unique_id_str = f"{source_file}_{chunk_index}_{i}"
            point_id = str(uuid.uuid5(namespace_dns, unique_id_str))
            
            # Payload includes both text and full enriched metadata
            payload = {
                "text": chunk["text"],
                **metadata
            }
            
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
            )
            
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        logger.info(f"Successfully inserted {len(points)} chunks into Qdrant.")

    def search(self, query: str, top_k: int = 5, filter_metadata: Any = None) -> List[Dict]:
        """
        Embeds the query and searches Qdrant for the closest points using query_points.
        Supports native metadata filtering.
        """
        try:
            query_vector = self.embeddings.embed_query(query)
            
            # Construct Qdrant query filter if metadata is provided
            qdrant_filter = None
            if filter_metadata:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                conditions = []
                for k, v in filter_metadata.items():
                    conditions.append(
                        FieldCondition(
                            key=k,
                            match=MatchValue(value=v)
                        )
                    )
                qdrant_filter = Filter(must=conditions)
            
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=qdrant_filter,
                limit=top_k
            )
            
            hits = []
            for hit in results.points:
                hits.append({
                    "text": hit.payload.get("text", ""),
                    "score": hit.score,
                    "metadata": {k: v for k, v in hit.payload.items() if k != "text"}
                })
            return hits
        except Exception as e:
            logger.error(f"Search failed in Qdrant store: {e}")
            return []

# --- Example Dummy Implementations for Future Sprints ---

class GeminiAdapter(BaseLLMAdapter):
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured in settings/environment.")
        from langchain_google_genai import ChatGoogleGenerativeAI
        model_name = settings.gemini_model_name
        logger.info(f"Initializing Gemini LLM Adapter using model: {model_name}")
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0.2
        )

    def generate(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return response.content

class OpenAIAdapter(BaseLLMAdapter):
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not configured in settings/environment.")
        from langchain_openai import ChatOpenAI
        model_name = settings.openai_model_name
        logger.info(f"Initializing OpenAI LLM Adapter using model: {model_name}")
        self.llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            temperature=0.2
        )

    def generate(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return response.content

class AdapterFactory:
    """
    Factory class to return the correct adapter based on configs/settings.py
    This keeps the main application completely agnostic to the specific model/DB used.
    """
    _vector_store_instance = None

    @staticmethod
    def get_llm() -> BaseLLMAdapter:
        provider = settings.llm_provider.lower()
        if provider == "gemini":
            return GeminiAdapter(api_key=settings.gemini_api_key)
        elif provider == "openai":
            return OpenAIAdapter(api_key=settings.openai_api_key)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    @staticmethod
    def get_vector_store() -> BaseVectorStoreAdapter:
        if AdapterFactory._vector_store_instance is None:
            AdapterFactory._vector_store_instance = QdrantAdapter()
        return AdapterFactory._vector_store_instance

