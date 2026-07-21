from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class EvaluationItem(BaseModel):
    query: str = Field(..., description="Evaluation query string")
    ground_truth: Dict[str, Any] = Field(..., description="Expected metadata matches, e.g., {'source_file': 'x.pdf'}")

class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the sender, e.g. 'user' or 'assistant'")
    content: str = Field(..., description="Content of the message")

class ChatRequest(BaseModel):
    query: str = Field(..., description="The user's query/message")
    top_k: int = Field(5, description="Number of final matches to retrieve")
    rerank: bool = Field(True, description="Whether to apply Cross-Encoder rerank")
    document_type: Optional[str] = Field(None, description="Filter by document type")
    section: Optional[str] = Field(None, description="Filter by section name")
    confidence_threshold: Optional[float] = Field(None, description="Optional custom confidence threshold")
    history: List[ChatMessage] = Field(default=[], description="Chat history context")

class ChatResponse(BaseModel):
    query: str
    answer: str
    context: str
    results: List[Dict[str, Any]]
