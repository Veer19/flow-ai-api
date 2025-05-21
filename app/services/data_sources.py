from fastapi import HTTPException, UploadFile
from app.services.mongodb import get_collection
from app.models.data_sources import DataSource
from datetime import datetime
import logging
from app.utils.blob_storage import upload_to_blob_storage
from app.utils.csv_parser import read_and_parse_csv
from bson.objectid import ObjectId
from app.services.projects import get_project
from typing import List

logger = logging.getLogger(__name__)

async def get_data_sources(project_id: str, user_id: str) -> List[DataSource]:
    """
    Get all files associated with a specific project
    """
    try:
        dataSources_collection = get_collection("dataSources")
        
        await get_project(project_id, user_id)
        
        # Get all files from the dataSources collection
        data_sources = []
        async for data_source in dataSources_collection.find({"projectId": project_id}):
            data_sources.append(DataSource(id=str(data_source["_id"]), **data_source))
        
        return data_sources
        
    except Exception as e:
        logger.error(f"Failed to fetch project files: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch project files: {str(e)}"
        )
    
async def upload_data_source(project_id: str, file: UploadFile, user_id: str):
    """
    Upload a single CSV file to Azure Blob Storage and associate with a project.
    """
    try:
        logger.info(f"Starting single file upload for project {project_id}")

        # Get the dataSources collection
        datasources_collection = get_collection("dataSources")

        # Get the projects collection
        projects_collection = get_collection("projects")
        
        # Verify project exists
        await get_project(project_id, user_id)

        # Upload file to Azure Blob Storage
        # Read and validate file
        content = await file.read()
        file_size = len(content)
        
        # Parse CSV
        df, sample_data, column_names, column_types = await read_and_parse_csv(content, file_size, file.filename)
        
        # Upload to blob storage
        # Get the current timestamp
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{project_id}/{timestamp}_{file.filename}"
        blob_url = await upload_to_blob_storage(content, safe_filename)
        
        # Create file metadata
        file_metadata = {
            "projectId": str(project_id),
            "filename": file.filename,
            "blobPath": safe_filename,
            "blobUrl": blob_url,
            "size": file_size,
            "type": 'csv',
            "rows": len(df),
            "columns": len(df.columns),
            "sampleData": sample_data,
            "columnMetadata": [
                {"name": name, "type": column_types[name]} 
                for name in column_names
            ],
            "createdAt": now,
            "lastUpdatedAt": now,
            "status": "READY",
        }
        
        # Insert into MongoDB
        result = await datasources_collection.insert_one(file_metadata)

        await projects_collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {
                "status": "DATA_UPLOADED",
                "lastUpdatedAt": now
            }}
        )
        
        created_data_source = await datasources_collection.find_one({"_id": result.inserted_id})
        
        return DataSource(id=str(created_data_source["_id"]), **created_data_source)
    
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

async def delete_data_source(project_id: str, data_source_id: str, user_id: str):
    """
    Delete a data source from Azure Blob Storage and MongoDB.
    """
    try:
        # Get the dataSources collection
        datasources_collection = get_collection("dataSources")
        
        # Verify project exists
        await get_project(project_id, user_id)

        # Delete the data source from Azure Blob Storage
        # await cleanup_uploaded_blobs(data_source_id)

        # Delete the data source from MongoDB
        await datasources_collection.delete_one({"_id": ObjectId(data_source_id)})

        return True
    
    except Exception as e:
        logger.error(f"Failed to delete data source: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete data source: {str(e)}")