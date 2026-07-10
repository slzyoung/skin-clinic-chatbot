# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # LLM Settings
    llm_provider: str = "gemini" # 'gemini' or 'openai'
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    gemini_model_name: str = "gemini-2.5-flash"
    openai_model_name: str = "gpt-4o-mini"
    
    # Vector DB (Qdrant) Settings
    qdrant_url: str = "./qdrant_data"
    qdrant_collection_name: str = "arya_noble_kb"
    
    # Chunking Settings
    chunk_size: int = 500
    chunk_overlap: int = 50
    
    # Embedding Settings
    embedding_model_name: str = "BAAI/bge-m3" # Multilingual and highly capable embedding
    
    # Reranker Settings
    reranker_model_name: str = "BAAI/bge-reranker-base"
    rerank_confidence_threshold: float = 0.1
    
    # BM25 Settings
    bm25_index_path: str = "./qdrant_data/bm25_index.pkl"

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()
