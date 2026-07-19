from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime

class ConfigBase(BaseModel):
    key: str
    value: str

class ConfigUpdate(BaseModel):
    value: str

class ConfigResponse(ConfigBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
