from pydantic import BaseModel
from typing import Optional
from datetime import datetime
class ProjectCreate(BaseModel):
    name: str
    natureOfData: str
    description: Optional[str] = ""
    class Config:
        json_schema_extra = {
            "example": {
                "name": "123456789",
                "natureOfData": "Sales",
                "description": "Sales data analysis project"
            }
        }

class ProjectStats(BaseModel):
    """Schema for project stats"""
    title: str
    description: str
    value: float
    type: str

class ProjectResponse(BaseModel):
    """Schema for project response"""
    id: str
    name: str
    description: str
    natureOfData: str
    status: str
    createdAt: datetime
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
