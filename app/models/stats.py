from pydantic import BaseModel
from typing import List
from enum import Enum
from datetime import datetime
from typing import Any, Dict

class StatType(str, Enum):
    count = "count"
    percentage = "percentage"


class ProjectStats(BaseModel):
    """Schema for project stats"""
    id: str
    title: str
    description: str
    value: float
    type: StatType
    projectId: str
    userId: str
    data_sources_used: List[str]
    python_code: str
    createdAt: datetime
    def to_llm_dict(self) -> Dict[str, Any]:
        """Convert the Stat to a plain dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "type": self.type.value,
            "data_sources_used": self.data_sources_used,
        }
    

class NewStat(BaseModel):
    title: str
    description: str
    type: StatType
    python_code: str
    data_sources_used: List[str]

class StatsLLMResponse(BaseModel):
    stats: List[NewStat]