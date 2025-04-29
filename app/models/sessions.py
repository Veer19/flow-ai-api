from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import datetime

class UploadSession(BaseModel):
    id: str = Field(alias="_id")
    files: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    created_at: datetime
    blob_urls: Dict[str, str] 