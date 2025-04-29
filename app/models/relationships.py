from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId

class RelationshipBase(BaseModel):
    tableA: str
    tableB: str
    keyA: str
    keyB: str
    description: Optional[str] = None

class RelationshipConfirmation(RelationshipBase):
    pass

class RelationshipResponse(RelationshipBase):
    confidence: float

class RelationshipInDB(RelationshipBase):
    id: str = Field(alias="_id")
    confirmed_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        
    @classmethod
    def from_mongo(cls, data: dict):
        if not data:
            return None
        data["id"] = str(data.pop("_id"))
        return cls(**data) 