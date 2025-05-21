from typing import Any, Dict
from pydantic import BaseModel
from datetime import datetime

class DataSourceColumnMetadata(BaseModel):
    name: str
    type: str

class DataSource(BaseModel):
    id: str
    projectId: str
    type: str
    filename: str
    blobPath: str
    blobUrl: str
    size: int
    rows: int
    columns: int
    sampleData: list[dict]
    columnMetadata: list[DataSourceColumnMetadata]
    status: str
    createdAt: datetime
    lastUpdatedAt: datetime
    def to_llm_dict(self) -> Dict[str, Any]:
        """Convert the DataSource to a plain dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "filename": self.filename,
            "rows": self.rows,
            "columns": self.columns,
            "sampleData": self.sampleData,
            "columnMetadata": self.columnMetadata,
            "blobPath": self.blobPath
        }
    
    class Config:
        json_schema_extra = {
            "example": {
                "projectId": "6814a2833d58c2ba83a5c2f0",
                "type": "csv",
                "filename": "sales.csv",
                "blobPath": "6814a2833d58c2ba83a5c2f0/20250502_161703_sales.csv",
                "blobUrl": "https://stveervs1930709483575967.blob.core.windows.net/csvfiles/6814a2…",
                "size": 213045,
                "rows": 2823,
                "columns": 8
            }
        }
