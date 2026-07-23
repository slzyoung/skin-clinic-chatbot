from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os

class Settings(BaseSettings):
    # LLM Settings
    llm_provider: str = "openai"
    openai_api_key: Optional[str] = None
    openai_model_name: str = "gpt-4o-mini"

    # Vector DB (PGVector) Settings
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_db: str = "arya_noble"
    pg_user: str = "postgres"
    pg_password: str = "postgres"
    pg_collection_name: str = "arya_noble_kb"
    
    @property
    def pg_conn_str(self) -> str:
        return f"postgresql+psycopg://{self.pg_user}:{self.pg_password}@{self.pg_host}:{self.pg_port}/{self.pg_db}"
    
    # Chunking Settings
    chunk_size: int = 500
    chunk_overlap: int = 50
    
    # Embedding Settings
    embedding_model_name: str = "BAAI/bge-m3"
    
    # Reranker Settings
    reranker_model_name: str = "BAAI/bge-reranker-base"
    rerank_confidence_threshold: float = 0.1
    
    # BM25 Settings
    bm25_index_path: str = "./data/output/bm25_index.pkl"

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../.env", "../../.env"),
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()
