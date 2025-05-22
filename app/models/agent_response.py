

from pydantic import BaseModel
from enum import Enum
from typing import List, Any, Optional


class Intent(str, Enum):
    DATA_QUESTION = "data_question"
    CREATE_VISUAL = "create_visual"
    CASUAL_GREETING = "casual_greeting"
    GRATITUDE = "gratitude"
    UNKNOWN = "unknown"


class AttachmentType(str, Enum):
    INLINE_TABLE = "inline_table"
    ATTACHED_CSV = "attached_csv"
    VISUAL = "visual"


class ResponseType(str, Enum):
    ERROR = "error"
    ANALYSIS = "analysis"
    RESPONSE = "response"


class ClassifyQueryLLMResponse(BaseModel):
    intent: Intent
    reason: str


class AnalyzeQuestionLLMResponse(BaseModel):
    required_dataset_ids: List[str]
    analysis_description: str
    suggested_operations: List[str]


class FormatResponseLLMResponse(BaseModel):
    type: ResponseType
    message: str
    data: Optional[Any] = None
    attach: Optional[AttachmentType] = None
