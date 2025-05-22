from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any
from datetime import timezone
from pydantic import field_validator


class ChatFeedback(BaseModel):
    type: str
    remarks: str


class ChatMetrics(BaseModel):
    tokens_used: int
    time_taken: float


class Attachment(BaseModel):
    type: str
    attachment: list[Any] | dict[str, Any]


class Message(BaseModel):
    id: str
    thread_id: str
    project_id: str
    user_id: str
    role: str
    content: str
    attachments: list[Attachment]
    timestamp: datetime
    feedback: Optional[ChatFeedback] = None
    metrics: Optional[ChatMetrics] = None

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def to_llm_dict(self):
        return {
            "role": self.role,
            "content": self.content
        }


class Thread(BaseModel):
    """Schema for thread response"""
    id: str
    project_id: str
    user_id: str
    status: str
    created_at: datetime
    last_updated_at: datetime

    @field_validator("created_at", "last_updated_at", mode="before")
    @classmethod
    def ensure_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "123456789",
                "user_id": "123456789",
                "status": "OPEN",
                "created_at": "2024-04-29T18:24:22.783948",
                "last_updated_at": "2024-04-29T18:24:22.783948"
            }
        }
