from fastapi import APIRouter, HTTPException
from app.models.datasets import UploadDataset
from app.services.mongodb import get_database
from typing import List
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class DatasetListItem(BaseModel):
    id: str
    filename: str
    created_at: datetime

@router.get("/", response_model=List[DatasetListItem])
async def list_datasets():
    """List all datasets with basic information."""
    try:
        db = get_database()
        cursor = db.datasets.find(
            {},
            {
                "_id": 1,
                "files.filename": {"$reduce": {
                    "input": "$files.filename",
                    "initialValue": "",
                    "in": {"$concat": ["$$value", {"$cond": [{"$eq": ["$$value", ""]}, "", ", "]}, "$$this"]}
                }},
                "created_at": 1
            }
        ).sort("created_at", -1)
        
        datasets = await cursor.to_list(length=None)
        
        if not datasets:
            return []
            
        return [
            DatasetListItem(
                id=str(d["_id"]),
                filename=d["files"][0]["filename"] if d.get("files") else "Untitled",
                created_at=d["created_at"]
            ) 
            for d in datasets
        ]
        
    except Exception as e:
        print(f"Failed to fetch datasets: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch datasets: {str(e)}"
        )

@router.get("/{dataset_id}", response_model=UploadDataset)
async def get_dataset(dataset_id: str):
    """Retrieve dataset details including files, relationships and blob URLs."""
    try:
        db = get_database()
        dataset = await db.datasets.find_one({"_id": dataset_id})
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
            
        return UploadDataset(**dataset)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve dataset: {str(e)}"
        ) 