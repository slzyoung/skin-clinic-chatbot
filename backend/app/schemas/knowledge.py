from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from app.models.knowledge import KnowledgeType, KnowledgeStatus

class KnowledgeBase(BaseModel):
    title: str
    content: Optional[str] = None
    file_name: str
    original_path: str
    mime_type: Optional[str] = None
    file_size: Optional[int] = None

class KnowledgeCreate(KnowledgeBase):
    type: KnowledgeType

class KnowledgeUpdateStatus(BaseModel):
    status: KnowledgeStatus

class KnowledgeProjectUpdate(BaseModel):
    project_id: Optional[UUID] = None

class KnowledgeResponse(KnowledgeBase):
    id: UUID
    type: KnowledgeType
    status: KnowledgeStatus
    ai_summary: Optional[str] = None
    ai_confidence: Optional[float] = None
    uploaded_by: UUID
    approved_by: Optional[UUID] = None
    project_id: Optional[UUID] = None
    metadata_: Optional[Dict[str, Any]] = Field(default=None, serialization_alias="metadata")
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
