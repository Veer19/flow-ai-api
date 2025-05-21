from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.stats import ProjectStats

class ProjectRequestBody(BaseModel):
    name: str
    description: Optional[str] = ""
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Supermarket Sales Data",
                "description": "Sales data analysis project"
            }
        }


class Project(BaseModel):
    """Schema for project response"""
    id: str
    name: str
    description: str
    status: str
    createdAt: datetime
    userId: str
    stats: Optional[list[ProjectStats]] = []
    lastUpdatedAt: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123456789",
                "name": "Test Project",
                "description": "Sales data analysis project",
                "natureOfData": "Sales",
                "status": "CREATED",
                "createdAt": "2024-04-29T18:24:22.783948",
                "lastUpdatedAt": "2024-04-29T18:24:22.783948"
            }
        }
