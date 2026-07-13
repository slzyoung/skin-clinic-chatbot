import uuid
from typing import Dict, Any

class RagServiceStub:
    """
    Stubs for the Langchain integration. 
    Your AI partner should implement the actual RAG pipeline logic here.
    """
    
    async def process_document(self, knowledge_id: uuid.UUID) -> None:
        """
        Takes a document from the DB (e.g., PDF), extracts text, chunks it, 
        generates embeddings via OpenAI, and saves it to 'knowledge_chunk'.
        """
        pass
        
    async def generate_chat_response(self, session_id: uuid.UUID, user_message: str) -> Dict[str, Any]:
        """
        Retrieves context using pgvector and generates a grounded response.
        Should return a dict containing the text and metadata.
        """
        return {
            "text": "This is a stub response.",
            "metadata": {}
        }
