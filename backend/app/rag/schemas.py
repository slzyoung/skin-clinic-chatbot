from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the sender, e.g. 'user' or 'assistant'")
    content: str = Field(..., description="Content of the message")

class ChatRequest(BaseModel):
    query: str = Field(..., description="The user's query/message")
    top_k: int = Field(5, description="Number of final matches to retrieve")
    rerank: bool = Field(True, description="Whether to apply Cross-Encoder rerank")
    document_type: Optional[str] = Field(None, description="Filter by document type (e.g. product, treatment, faq, promotion, sop)")
    section: Optional[str] = Field(None, description="Filter by section name (e.g. ACTIVE INGREDIENTS, HOW TO USE)")
    confidence_threshold: Optional[float] = Field(None, description="Optional custom confidence threshold")
    history: List[ChatMessage] = Field(default=[], description="Chat history context")

class ChatResponse(BaseModel):
    query: str
    answer: str
    context: str
    results: List[Dict[str, Any]]

class EvaluationItem(BaseModel):
    query: str = Field(..., description="Evaluation query string")
    ground_truth: Dict[str, Any] = Field(..., description="Expected metadata matches, e.g., {'source_file': 'x.pdf'}")

class DocumentListItem(BaseModel):
    file_name: str = Field(..., description="Filename of the ingested document")
    product_name: Optional[str] = Field(None, description="Extracted product name")
    document_type: Optional[str] = Field(None, description="Document classification type")
    status: str = Field(..., description="'Approved' or 'On review'")
    processed_at: Optional[str] = Field(None, description="ISO timestamp of when document was processed")
    chunks_count: int = Field(..., description="Number of text chunks in document")

class ApproveRequest(BaseModel):
    file_name: str = Field(..., description="Filename of the pending document to approve")

class RejectRequest(BaseModel):
    file_name: str = Field(..., description="Filename of the pending document to reject")

class PendingDocumentResponse(BaseModel):
    file_name: str = Field(..., description="Filename of the staged document")
    status: str = Field(..., description="'Approved' or 'On review'")
    summary: str = Field(..., description="AI-generated summary of the document")
    text_accuracy: str = Field(..., description="AI confidence score / text accuracy percentage")
    feedback: str = Field(..., description="AI data validation feedback")
    chunks: List[Dict[str, Any]] = Field(..., description="Parsed chunks list")

class RefineRequest(BaseModel):
    prompt: str = Field(..., description="Instructions to refine the document summary or text content")


