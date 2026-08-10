from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the sender ('user' or 'assistant')")
    content: str = Field(..., description="Content of the conversation message")

class UserContext(BaseModel):
    user_id: str = Field(..., description="The ID of the user requesting the chat")
    dr_type: str = Field(..., description="The doctor type of the user")
    branch_ids: List[str] = Field(default_factory=list, description="The branch IDs the user belongs to")
    excluded_categories: List[str] = Field(default_factory=list, description="The names of categories excluded for this user")

class ChatRequest(BaseModel):
    query: str = Field(..., description="User question or medical query string")
    categories: Optional[List[str]] = Field(default=[], description="Optional list of category filters (e.g. ['Acne Care', 'Brightening'])")
    document_type: Optional[str] = Field(None, description="Optional document category type filter ('Product', 'Treatment', or 'Promotional')")
    top_k: int = Field(8, description="Number of context passages to retrieve")
    history: List[ChatMessage] = Field(default=[], description="Multi-turn conversation chat history context")
    user_context: Optional[UserContext] = Field(None, description="Context properties of the querying user used for visibility and exclusion filtering")

class ChatResponse(BaseModel):
    query: str = Field(..., description="User query string")
    answer: str = Field(..., description="Doctor-aligned AI generated response")
    context: str = Field(..., description="Retrieved context passages formatted for reference")
    results: List[Dict[str, Any]] = Field(..., description="Retrieved passage citations and metadata")
    agent_used: bool = Field(False, description="Whether AI Agent (multi-step reasoning) was used for this response")

class EvaluationItem(BaseModel):
    query: str = Field(..., description="Test query string (e.g. 'Apa indikasi ERHA Acne Clear Gel?')")
    expected_file: str = Field(..., description="Expected source document filename (e.g. 'ERHA Acne Clear Gel.docx')")

class DocumentListItem(BaseModel):
    knowledge_id: str = Field(..., description="Unique document ID (UUID)")
    file_name: str = Field(..., description="Filename of the ingested document")
    product_name: Optional[str] = Field(None, description="Extracted product name")
    type: Optional[str] = Field("Product", description="Document Category Type (Product, Treatment, Promotional)")
    status: str = Field(..., description="'Approved' or 'On review'")
    processed_at: Optional[str] = Field(None, description="ISO timestamp of when document was processed")
    chunks_count: int = Field(..., description="Number of text chunks in document")

class ApproveRequest(BaseModel):
    file_name: Optional[str] = Field(None, description="Filename of the pending document to approve")
    category_ids: Optional[List[str]] = Field(default=[], description="Category IDs if applicable")
    knowledge_ids: Optional[List[str]] = Field(default=[], description="Optional list of knowledge IDs for batch approval in 1 click")

class RejectRequest(BaseModel):
    file_name: Optional[str] = Field(None, description="Filename of the pending document to reject")

class VisibilitySettings(BaseModel):
    clinics: List[str] = Field(default=["all"], description="Allowed clinic IDs or ['all']")
    doctor_types: List[str] = Field(default=["all"], description="Allowed doctor type IDs or ['all']")
    doctors: List[str] = Field(default=["all"], description="Allowed doctor user IDs or ['all']")

class PendingDocumentResponse(BaseModel):
    knowledge_id: str = Field(..., description="Unique document ID (UUID)")
    file_name: str = Field(..., description="Filename of the staged document")
    title: Optional[str] = Field(None, description="AI Recommended Title for Knowledge Header (e.g. 'Knowledge Ingestment Brightener Product')")
    type: Optional[str] = Field("Product", description="Document Category Type (Product, Treatment, Promotional, General)")
    status: str = Field(..., description="'Approved' or 'On review'")
    summary: Optional[str] = Field("", description="Document content in markdown format")
    text_accuracy: str = Field(..., description="AI confidence score / text accuracy percentage")
    feedback: str = Field(..., description="AI data validation feedback")
    suggested_categories: Optional[List[Any]] = Field(default=[], description="Suggested category tags (objects with id and name)")
    visibility_settings: Optional[VisibilitySettings] = Field(default_factory=VisibilitySettings, description="Access control visibility settings (Clinic, Doctor Type, Doctor)")
    initial_prompt: Optional[str] = Field(None, description="Initial prompt passed during ingestion if any")
    history: Optional[List[ChatMessage]] = Field(default=[], description="Conversation history list")
    chunks: List[Dict[str, Any]] = Field(..., description="Parsed chunks list")

class RefineRequest(BaseModel):
    prompt: str = Field(..., description="Instructions to refine the document summary or text content")
    history: Optional[List[ChatMessage]] = Field(default=[], description="Multi-turn conversation history for refine editing")
    visibility_settings: Optional[VisibilitySettings] = Field(None, description="Optional visibility settings update")

class EditApprovedDocumentRequest(BaseModel):
    summary: Optional[str] = Field(None, description="Updated document summary markdown (for manual save)")
    categories: Optional[List[Any]] = Field(default=[], description="Updated list of document categories (for manual save)")
    visibility_settings: Optional[VisibilitySettings] = Field(None, description="Updated visibility settings")
    title: Optional[str] = Field(None, description="Updated document title")

class ApprovedDocumentResponse(BaseModel):
    knowledge_id: str = Field(..., description="Knowledge ID / document identifier")
    file_name: str = Field(..., description="Filename of the approved document")
    title: Optional[str] = Field(None, description="Document title")
    status: str = Field("Approved", description="Document status")
    summary: str = Field("", description="Document summary")
    categories: List[str] = Field(default=[], description="Document categories")
    visibility_settings: Optional[VisibilitySettings] = Field(default_factory=VisibilitySettings, description="Access control visibility settings (Clinic, Doctor Type, Doctor)")
    chunks: List[Dict[str, Any]] = Field(..., description="Document text chunks")


# --- RAGAS-style Evaluation Schemas ---

class RAGEvaluationItem(BaseModel):
    query: str = Field(..., description="Test query string")
    expected_file: str = Field(..., description="Expected source document filename for retrieval metrics")
    expected_answer: Optional[str] = Field(None, description="Expected reference answer for generation metrics (Faithfulness, Answer Relevance)")

class RAGEvaluationResponse(BaseModel):
    hit_rate: float = Field(..., description="Hit Rate@K — proportion of queries where relevant doc is in top-K")
    mrr: float = Field(..., description="Mean Reciprocal Rank@K")
    faithfulness: Optional[float] = Field(None, description="Faithfulness score (0-1) — are claims grounded in context?")
    answer_relevance: Optional[float] = Field(None, description="Answer Relevance score (0-1) — does answer address the question?")
    total_queries: int = Field(..., description="Number of queries evaluated")
