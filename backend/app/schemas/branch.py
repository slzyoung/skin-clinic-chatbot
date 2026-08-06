from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class BranchBase(BaseModel):
    name: str
    token_limit: int = 0

class BranchCreate(BranchBase):
    pass

class BranchUpdate(BaseModel):
    name: Optional[str] = None
    token_limit: Optional[int] = None

class BranchDoctorResponse(BaseModel):
    id: UUID
    name: str
    speciality: str = ""
    tokensLeft: int = 0
    status: str = "Active"
    maxTokens: int = 0
    
    model_config = ConfigDict(from_attributes=True)

class BranchResponse(BranchBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    used: int = 0
    remaining: int = 0
    
    doctors: Optional[List[BranchDoctorResponse]] = []
    
    model_config = ConfigDict(from_attributes=True)
