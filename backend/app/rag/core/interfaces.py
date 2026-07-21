from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseVectorStoreAdapter(ABC):
    """
    Blueprint for Vector Database adapters.
    Whether we use Qdrant, Pinecone, or Chroma, they must implement these methods.
    """
    @abstractmethod
    async def insert_chunks(self, chunks: List[Dict]):
        pass

    @abstractmethod
    async def search(self, query: str, top_k: int = 5, filter_metadata: Any = None) -> List[Dict]:
        pass

class BaseLLMAdapter(ABC):
    """
    Blueprint for LLM adapters.
    Whether we use Gemini, OpenAI, or local LLaMA, they must implement this.
    """
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        pass
