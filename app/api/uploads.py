from fastapi import APIRouter, File, UploadFile, HTTPException, Form, Path, Body
from typing import List, Optional, Dict
import uuid
from datetime import datetime
import pandas as pd
from azure.storage.blob import BlobServiceClient
from app.config import get_settings
from app.services.azure_ai import query_azure_openai
from app.services.mongodb import get_database
from bson.objectid import ObjectId
import json

settings = get_settings()
router = APIRouter()

@router.post("/csv")
async def upload_csv_files(
    files: List[UploadFile] = File(...),
    project_id: Optional[str] = Form(None)
):
    """
    Upload CSV files to Azure Blob Storage and associate with a project if project_id is provided.
    Returns a dataset_id that can be used to analyze the files later.
    """
    blob_urls = {}
    dataset_id = str(uuid.uuid4())
    file_metadata = []
    
    # Initialize Azure Blob Storage client
    blob_service_client = BlobServiceClient.from_connection_string(
        settings.AZURE_STORAGE_CONNECTION_STRING
    )
    container_client = blob_service_client.get_container_client(
        settings.AZURE_STORAGE_CONTAINER
    )
    
    try:
        # Verify project exists if project_id is provided
        if project_id:
            db = get_database()
            project = await db.projects.find_one({"_id": ObjectId(project_id)})
            if not project:
                raise HTTPException(
                    status_code=404,
                    detail=f"Project with ID {project_id} not found"
                )
        
        for file in files:
            if not file.filename.endswith('.csv'):
                continue
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Include project_id in the blob path if provided
            folder_prefix = f"{project_id}/" if project_id else ""
            safe_filename = f"{folder_prefix}{dataset_id}/{timestamp}_{file.filename}"
            
            # Process the CSV file
            content = await file.read()
            
            # Upload to Azure Blob Storage
            blob_client = container_client.get_blob_client(safe_filename)
            blob_client.upload_blob(content)
            blob_urls[file.filename] = blob_client.url
            
            # Store basic file metadata
            file_metadata.append({
                "filename": file.filename,
                "blob_path": safe_filename,
                "upload_time": datetime.utcnow().isoformat(),
                "analyzed": False
            })
        
        # Store dataset information in MongoDB
        db = get_database()
        dataset_doc = {
            "_id": dataset_id,
            "files": file_metadata,
            "created_at": datetime.utcnow(),
            "blob_urls": blob_urls,
            "analyzed": False
        }
        
        # Add project_id to the dataset document if provided
        if project_id:
            dataset_doc["project_id"] = project_id
            
            # Also update the project document to include this dataset
            await db.projects.update_one(
                {"_id": ObjectId(project_id)},
                {"$push": {"datasets": dataset_id}}
            )
        
        await db.datasets.insert_one(dataset_doc)
        
        return {
            "dataset_id": dataset_id,
            "project_id": project_id if project_id else None,
            "files": file_metadata,
            "message": "Files uploaded successfully. Call /analyze/{dataset_id} to analyze the files."
        }
        
    except Exception as e:
        # Cleanup blobs if error occurs
        for filename, url in blob_urls.items():
            try:
                blob_path = next((f["blob_path"] for f in file_metadata if f["filename"] == filename), None)
                if blob_path:
                    blob_client = container_client.get_blob_client(blob_path)
                    blob_client.delete_blob()
            except:
                pass
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )

@router.post("/analyze/{dataset_id}")
async def analyze_dataset(
    dataset_id: str = Path(..., description="The ID of the dataset to analyze")
):
    """
    Analyze previously uploaded CSV files in a dataset.
    Performs data analysis, extracts metadata, and identifies relationships between files.
    """
    try:
        # Get the dataset from MongoDB
        db = get_database()
        dataset = await db.datasets.find_one({"_id": dataset_id})
        
        if not dataset:
            raise HTTPException(
                status_code=404,
                detail=f"Dataset with ID {dataset_id} not found"
            )
            
        if dataset.get("analyzed", False):
            return {
                "dataset_id": dataset_id,
                "message": "Dataset has already been analyzed",
                "files": dataset.get("files", []),
                "relationships": dataset.get("relationships", [])
            }
        
        # Initialize Azure Blob Storage client
        blob_service_client = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
        container_client = blob_service_client.get_container_client(
            settings.AZURE_STORAGE_CONTAINER
        )
        
        # Process each file
        dataframes = {}
        updated_files = []
        
        for file_info in dataset.get("files", []):
            blob_path = file_info.get("blob_path")
            filename = file_info.get("filename")
            
            if not blob_path or not filename:
                continue
                
            try:
                # Download blob content
                blob_client = container_client.get_blob_client(blob_path)
                blob_content = blob_client.download_blob().readall()
                
                # Process with pandas
                import io
                df = pd.read_csv(io.BytesIO(blob_content))
                df = df.replace({
                    pd.NA: None,
                    pd.NaT: None,
                    float('inf'): None,
                    float('-inf'): None
                })
                df = df.where(pd.notnull(df), None)
                
                column_types = {
                    col: str(dtype) 
                    for col, dtype in df.dtypes.items()
                }
                sample_data = df.head(3).to_dict('records')
                
                # Get unique values for non-numerical columns
                unique_values = []
                for col in df.columns:
                    if (df[col].dtype not in ['int64', 'float64'] and 
                        len(df[col].dropna().unique()) < 20):
                        unique_values.append(
                            df[col].dropna().unique().tolist()
                        )
                    else:
                        unique_values.append(None)

                # Update file metadata with analysis results
                updated_file_info = {
                    **file_info,
                    "rows": len(df),
                    "columns": len(df.columns),
                    "column_names": df.columns.tolist(),
                    "column_types": column_types,
                    "sample_data": sample_data,
                    "unique_values": unique_values,
                    "analyzed": True,
                    "success": True
                }
                
                dataframes[filename] = updated_file_info
                updated_files.append(updated_file_info)
                
            except Exception as e:
                # Update file metadata with error information
                updated_file_info = {
                    **file_info,
                    "error": str(e),
                    "analyzed": True,
                    "success": False
                }
                updated_files.append(updated_file_info)
        
        # Infer relationships if we have multiple files
        relationships = []
        if len(dataframes) > 1:
            try:
                prompt = """
                Analyze these tables and suggest relationships between them.
                Consider column names, data types, and sample data.
                Tables to analyze:
                """
                for filename, metadata in dataframes.items():
                    prompt += f"\nTable: {filename}\n"
                    prompt += "Columns:\n"
                    for col, dtype in metadata["column_types"].items():
                        prompt += f"- {col} ({dtype})\n"
                    prompt += "Sample Data:\n"
                    for row in metadata["sample_data"]:
                        prompt += f"- {row}\n"

                ai_response = await query_azure_openai(prompt)
                relationships = ai_response['relationships']
            except Exception as e:
                print(f"AI inference error: {str(e)}")
        
        # Update the dataset document with analysis results
        await db.datasets.update_one(
            {"_id": dataset_id},
            {
                "$set": {
                    "files": updated_files,
                    "relationships": relationships,
                    "analyzed": True,
                    "analysis_time": datetime.utcnow()
                }
            }
        )
        
        return {
            "dataset_id": dataset_id,
            "project_id": dataset.get("project_id"),
            "files": updated_files,
            "relationships": relationships,
            "message": "Dataset analysis completed successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        ) 