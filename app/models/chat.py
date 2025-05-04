from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any

class ChatFeedback(BaseModel):
    type: str
    remarks: str

class ChatMetrics(BaseModel):
    tokens_used: int
    time_taken: float

class Attachment(BaseModel):
    type: str
    attachment: list[Any]

class Message(BaseModel):
    role: str
    content: str
    attachments: list[Attachment]
    timestamp: datetime
    feedback: Optional[ChatFeedback] = None
    metrics: Optional[ChatMetrics] = None


class ThreadListItem(BaseModel):
    thread_id: str
    project_id: str
    status: str
    createdAt: datetime
    lastUpdatedAt: datetime
    class Config:
        json_schema_extra = {
            "example": {
                "thread_id": "123456789",
                "project_id": "123456789",
                "status": "OPEN",
                "createdAt": "2024-04-29T18:24:22.783948",
                "lastUpdatedAt": "2024-04-29T18:24:22.783948"
            }
        }

class Thread(BaseModel):
    """Schema for thread response"""
    _id: str
    thread_id: str
    project_id: str
    status: str
    messages: list[Message]
    createdAt: datetime
    lastUpdatedAt: datetime
    class Config:
        json_schema_extra = {
            "example": {
                "_id": "123456789",
                "thread_id": "123456789",
                "project_id": "123456789",
                "status": "OPEN",
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello, how are you?",
                        "timestamp": "2024-04-29T18:24:22.783948",
                        "attachments": [],
                        "feedback": {
                            "type": "positive",
                            "remarks": "Good"
                        }
                    }
                ],
                "createdAt": "2024-04-29T18:24:22.783948",
                "lastUpdatedAt": "2024-04-29T18:24:22.783948"
            }
        }
