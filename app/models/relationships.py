from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from enum import Enum
from typing import Any, Dict

class RelationshipType(str, Enum):
    ONE_TO_ONE = "ONE_TO_ONE"
    ONE_TO_MANY = "ONE_TO_MANY"
    MANY_TO_MANY = "MANY_TO_MANY"
    MANY_TO_ONE = "MANY_TO_ONE"

class RelationshipConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class NewRelationship(BaseModel):
    tableA: str
    tableB: str
    keyA: str
    keyB: str
    type: RelationshipType
    description: Optional[str] = None
    confidence: RelationshipConfidence

class RelationshipLLMResponse(BaseModel):
    relationships: List[NewRelationship]

class Relationship(BaseModel):
    id: str
    projectId: str
    userId: str
    tableA: str
    tableB: str
    keyA: str
    keyB: str
    type: RelationshipType
    description: Optional[str] = None
    confidence: RelationshipConfidence
    createdAt: datetime
    def to_llm_dict(self) -> Dict[str, Any]:
        """Convert the Relationship to a plain dictionary."""
        return {
            "id": self.id,
            "tableA": self.tableA,
            "tableB": self.tableB,
            "keyA": self.keyA,
            "keyB": self.keyB,
            "type": self.type.value,
            "description": self.description,
        }
