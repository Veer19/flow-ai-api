from fastapi import APIRouter, HTTPException, Body, File, UploadFile
from datetime import datetime
from typing import List, Dict, Any
from bson.objectid import ObjectId
import uuid
import logging
import traceback
import json
from app.services.azure_ai import query_azure_openai

from app.services.mongodb import get_collection
from app.config import get_settings
from app.utils.json_encoders import ensure_json_serializable, convert_numpy_types
from app.utils.blob_storage import upload_to_blob_storage, cleanup_uploaded_blobs, download_from_blob_storage
from app.utils.csv_parser import read_and_parse_csv
from app.models.projects import ProjectCreate, ProjectResponse
from app.services.project_service import create_project, get_projects, get_project, get_project_data_sources
from app.api.auth import verify_jwt_token
from fastapi import Depends

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
router = APIRouter()


@router.post("", response_model=ProjectResponse)
async def create_project_endpoint(project: ProjectCreate = Body(...), user: dict = Depends(verify_jwt_token)):
    """
    Create a new project document in MongoDB
    """
    return await create_project(user.get("sub"), project)



@router.get("", response_model=list[ProjectResponse])
async def get_projects_endpoint(user: dict = Depends(verify_jwt_token)):
    """
    Get all projects from MongoDB with complete structure
    """
    return await get_projects(user.get("sub"))

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project_endpoint(project_id: str, user: dict = Depends(verify_jwt_token)):
    """
    Get a specific project by ID with complete structure
    """
    return await get_project(project_id, user.get("sub"))

@router.post("/{project_id}/upload-file")
async def upload_single_file_endpoint(
    project_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(verify_jwt_token)
):
    """Upload a single CSV file to Azure Blob Storage and associate with a project."""
    logger.info(f"Starting single file upload for project {project_id}")
    
    try:
        # Verify project exists
        projects_collection = get_collection("projects")
        datasources_collection = get_collection("dataSources")
        
        project = await projects_collection.find_one({"_id": ObjectId(project_id), "userId": user.get("sub")})
        if not project:
            raise HTTPException(status_code=404, detail=f"Project not found")
        
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are supported")
            
        # Read and validate file
        content = await file.read()
        file_size = len(content)
        
        # Parse CSV
        df, sample_data, column_names, column_types = await read_and_parse_csv(content, file_size, file.filename)
        
        # Upload to blob storage
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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
            "createdAt": datetime.now(),
            "lastUpdatedAt": datetime.now(),
            "status": "READY",
        }
        
        # Insert into MongoDB
        await datasources_collection.insert_one(file_metadata)
        
        # Update project status
        # await projects_collection.update_one(
        #     {"_id": ObjectId(project_id)},
        #     {"$set": {
        #         # "status": "DATA_UPLOADED",
        #         "lastUpdatedAt": datetime.now()
        #     }}
        # )
        # Retyrn the object
        return ensure_json_serializable(file_metadata)
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/{project_id}/upload-data")
async def upload_project_data_endpoint(
    project_id: str,
    files: List[UploadFile] = File(...),
    user: dict = Depends(verify_jwt_token)
):
    """
    Upload CSV files to Azure Blob Storage and associate directly with a project.
    """
    print("THIS IS GETTING CALLED")
    logger.info(f"Starting upload_project_data for project {project_id} with {len(files)} files")
    
    # Track files to be processed
    file_metadata = []
    uploaded_blobs = []
    
    try:
        # Verify project exists
        projects_collection = get_collection("projects")
        datasources_collection = get_collection("dataSources")
        project_activities_collection = get_collection("projectActivities")
        
        project = await projects_collection.find_one({"_id": ObjectId(project_id), "userId": user.get("sub")})
        if not project:
            logger.error(f"Project with ID {project_id} not found")
            raise HTTPException(
                status_code=404,
                detail=f"Project with ID {project_id} not found"
            )
        
        # First, validate all files can be read and analyzed before uploading any
        logger.info("Validating all files before uploading")
        valid_files = []
        
        for file in files:
            if not file.filename.endswith('.csv'):
                logger.warning(f"Skipping non-CSV file: {file.filename}")
                continue
            
            logger.info(f"Validating file: {file.filename}")
            
            # Read file content
            content = await file.read()
            file_size = len(content)
            
            try:
                # Try to parse the CSV - this will raise an error if the file is invalid
                df, sample_data, column_names, column_types = await read_and_parse_csv(content, file_size, file.filename)
                
                # Reset file position for later reading
                await file.seek(0)
                
                # Add to valid files
                valid_files.append({
                    "file": file,
                    "content": content,
                    "size": file_size,
                    "df": df,
                    "sample_data": sample_data,
                    "column_names": column_names,
                    "column_types": column_types
                })
                
                logger.info(f"File validated successfully: {file.filename}")
                
            except Exception as e:
                # If any file fails validation, abort the entire upload
                logger.error(f"File validation failed for {file.filename}: {str(e)}")
                raise HTTPException(
                    status_code=400,
                    detail=f"File '{file.filename}' could not be processed: {str(e)}"
                )
        
        # If we get here, all files are valid - proceed with upload and analysis
        logger.info(f"All files validated successfully. Proceeding with upload for {len(valid_files)} files")
        
        # Process each valid file
        for valid_file in valid_files:
            file = valid_file["file"]
            content = valid_file["content"]
            file_size = valid_file["size"]
            df = valid_file["df"]
            sample_data = valid_file["sample_data"]
            column_names = valid_file["column_names"]
            column_types = valid_file["column_types"]
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Include project_id in the blob path
            safe_filename = f"{project_id}/{timestamp}_{file.filename}"
            
            try:
                # Analyze the data quality
                logger.info(f"Analyzing data quality for {file.filename}")
                # stats = await analyze_csv_data(df, column_names)
                
                # Upload to Azure Blob Storage
                logger.info(f"Uploading {file.filename} to blob storage")
                blob_url = await upload_to_blob_storage(content, safe_filename)
                uploaded_blobs.append({"path": safe_filename, "url": blob_url})
                
                logger.info(f"Successfully uploaded {file.filename} to blob storage")
                # Add file metadata
                file_metadata_entry = {
                    "projectId": str(project_id),
                    "filename": file.filename,
                    "blobPath": safe_filename,
                    "blobUrl": blob_url,
                    "size": int(file_size),  # Ensure it's a Python int
                    "type": 'csv',
                    "rows": int(len(df)),  # Ensure it's a Python int
                    "columns": int(len(df.columns)),  # Ensure it's a Python int
                    "sampleData": sample_data,
                    "columnMetadata": [
                        {"name": name, "type": column_types[name]} for name in column_names
                    ],
                    "createdAt": datetime.now(),
                    "lastUpdatedAt": datetime.now()
                }

                # Convert any remaining NumPy types to Python native types
                file_metadata_entry = convert_numpy_types(file_metadata_entry)

                file_metadata.append(file_metadata_entry)
                
                logger.info(f"Successfully processed and uploaded file: {file.filename}")
                
            except Exception as e:
                # If any part of the process fails, clean up and abort
                logger.error(f"Error processing file {file.filename}: {str(e)}")
                
                # Clean up any blobs that were already uploaded
                await cleanup_uploaded_blobs(uploaded_blobs)
                
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing file '{file.filename}': {str(e)}"
                )
        
        # If we get here, all files were processed successfully
        # Insert files into MongoDB
        if file_metadata:
            logger.info(f"Inserting {len(file_metadata)} file metadata records into MongoDB")
            await datasources_collection.insert_many(file_metadata)
            logger.info(f"Successfully inserted {len(file_metadata)} file metadata records into MongoDB")
            # Update project status to IN_PROGRESS
            # Add a projectActivity record
            project_activity = {
                "projectId": project_id,
                "activity": "DATA_UPLOADED",
                "status": "SUCCESS",
                "details": {
                    "dataSourcesCount": len(file_metadata),
                },
                "createdAt": datetime.now()
            }
            await project_activities_collection.insert_one(project_activity)
            await projects_collection.update_one(
                {"_id": ObjectId(project_id)},
                {"$set": {
                    "status": "DATA_UPLOADED", 
                    "lastUpdatedAt": datetime.now()
                }}
            )
            return ensure_json_serializable(file_metadata)
        else:
            logger.warning("No valid files to insert into MongoDB")
            return None
        
        
    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error in upload_project_data: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Clean up any blobs that were already uploaded
        await cleanup_uploaded_blobs(uploaded_blobs)
        
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )

@router.get("/{project_id}/data-sources")
async def get_project_data_sources_endpoint(project_id: str):
    """
    Get all files associated with a specific project
    """
    return await get_project_data_sources(project_id)

@router.post("/{project_id}/establish-relationships")
async def establish_relationships_endpoint(project_id: str):
    """
    Delete all existing relationships for a project and generate new ones
    based on the current data sources.
    """
    try:
        # Get the project from MongoDB
        projects_collection = get_collection("projects")
        relationships_collection = get_collection("relationships")
        
        # Verify project exists
        project = await projects_collection.find_one({"_id": ObjectId(project_id)})
        if not project:
            raise HTTPException(
                status_code=404,
                detail=f"Project with ID {project_id} not found"
            )
        
        # Get dataSources collection
        dataSources_collection = get_collection("dataSources")

        # Get all files from the dataSources collection
        data_sources = await dataSources_collection.find({"projectId": project_id}).to_list(None)
        
        # Ensure we have at least 2 data sources to find relationships
        if len(data_sources) < 2:
            return {
                "success": True,
                "message": "Need at least 2 data sources to analyze relationships",
                "relationships": []
            }
        
       
        
        # Prepare data for LLM analysis
        data_source_info = []
        for ds in data_sources:
            # Extract essential information for each data source
            source_info = {
                "id": ds.get("id"),
                "filename": ds.get("filename"),
                "rows": ds.get("rows"),
                "columns": [col.get("name") for col in ds.get("columnMetadata", [])],
                "column_types": {col.get("name"): col.get("type") for col in ds.get("columnMetadata", [])},
                "sample_data": ds.get("sampleData", [])[:2]  # Just a couple of rows for context
            }
            data_source_info.append(source_info)
        
        # Construct prompt for the LLM
        prompt = f"""
        I have {len(data_sources)} datasets in my project. I need to understand how they might be related.
        
        Here are the datasets with their column information:
        
        {json.dumps(data_source_info, indent=2)}
        
        Please analyze these datasets and identify potential join keys between datasets (columns that could be used to join datasets together).
        For each relationship, provide:
        - The two datasets involved
        - The type of relationship
        - The columns that establish the relationship
        - Confidence level (high, medium, low)
        - A brief explanation of why you think this relationship exists
        
        Note - 
        Identify the relationships along the lines of main data source and master tables. Always create the relationship from the main data source to the master tables.
        
        Format your response as a JSON object with a "relationships" array with following fields:
        tableA: string;
        tableB: string;
        keyA: string;
        keyB: string;
        description: string;
        confidence: number;
        """
        
        # Call the LLM to analyze relationships
        llm_response = await query_azure_openai(prompt)
        
        # Parse the LLM response to extract the JSON
        try:
            # Check if the response is already a dictionary (might be pre-parsed)
            if isinstance(llm_response, dict):
                relationships_data = llm_response
            else:
                # Find JSON in the response string
                json_start = llm_response.find('{')
                json_end = llm_response.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = llm_response[json_start:json_end]
                    relationships_data = json.loads(json_str)
                else:
                    # If no JSON found, try to parse the whole response
                    relationships_data = json.loads(llm_response)
        except json.JSONDecodeError:
            # If JSON parsing fails, extract structured data manually
            relationships_data = {
                "relationships": [],
                "raw_llm_response": str(llm_response)  # Convert to string to ensure it's serializable
            }
        
        # Store the relationship analysis in a new document
        relationship_doc = {
            "projectId": project_id,
            "relationships": relationships_data.get("relationships", []),
            "raw_llm_response": str(llm_response) if isinstance(llm_response, str) else json.dumps(llm_response),
            "dataSourceCount": len(data_sources),
            "createdAt": datetime.now()
        }
        
         # Delete all existing relationships for this project
        delete_result = await relationships_collection.delete_many({"projectId": project_id})
        deleted_count = delete_result.deleted_count
        # Insert the new relationship document
        await relationships_collection.insert_one(relationship_doc)
        
        # Update the project with the latest relationship analysis
        await projects_collection.update_one(
            {"_id": ObjectId(project_id)},
            {
                "$set": {
                    "relationshipCount": len(relationships_data.get("relationships", [])),
                    "relationshipsAnalyzed": True,
                    "lastUpdatedAt": datetime.now()
                }
            }
        )
        
        # Ensure the response is JSON serializable
        safe_response = ensure_json_serializable({
            "success": True,
            "project_id": str(project_id),
            "data_sources_count": len(data_sources),
            "analysis_time": datetime.now(),
            "old_relationships_deleted": deleted_count,
            "new_relationships_created": len(relationships_data.get("relationships", [])),
            "relationships": relationships_data.get("relationships", []),
            "message": "Relationship analysis completed successfully"
        })
        
        return safe_response
        
    except Exception as e:
        logger.error(f"Relationship regeneration failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Relationship regeneration failed: {str(e)}"
        )

@router.get("/{project_id}/relationships")
async def get_project_relationships_endpoint(project_id: str):
    """
    Get all relationships for a project including datasets, models, and data sources.
    
    Args:
        project_id: The ID of the project
        
    Returns:
        Dictionary containing datasets, models, and data sources related to the project
    """
    try:
        # Get the projects collection
        projects_collection = get_collection("projects")

        # Get the datasets collection
        datasets_collection = get_collection("dataSources")

        # Get the relationships collection
        relationships_collection = get_collection("relationships")
        
        # Verify project exists
        project = await projects_collection.find_one({"_id": ObjectId(project_id)})
        if not project:
            raise HTTPException(
                status_code=404,
                detail=f"Project with ID {project_id} not found"
            )
        
        # Get all data sources for this project
        data_sources = await datasets_collection.find({"projectId": project_id}).to_list(None)

        # Get the most recent relationship document for this project
        relationship = await relationships_collection.find_one(
            {"projectId": project_id},
            sort=[("createdAt", -1)]  # Sort by createdAt in descending order to get the most recent
        )
        
        if not relationship:
            return {
                "project_id": str(project_id),
                "message": "No relationships found for this project",
                "relationships": []
            }
        
        # Ensure the response is JSON serializable
        safe_response = ensure_json_serializable({
            "project_id": str(project_id),
            "analysis_time": relationship.get("createdAt"),
            "data_sources_count": relationship.get("dataSourceCount", 0),
            "relationships": relationship.get("relationships", []),
            "dataSources": data_sources
        })
        
        return safe_response
        
    except Exception as e:
        logger.error(f"Failed to fetch project relationships: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch project relationships: {str(e)}"
        )

@router.post("/{project_id}/generate-stats")
async def generate_project_stats_endpoint(project_id: str):
    """Generate top 4 statistical insights about the project data."""
    try:
        # Get collections and data
        projects_collection = get_collection("projects")
        dataSources_collection = get_collection("dataSources")
        relationships_collection = get_collection("relationships")
        project_stats_collection = get_collection("projectStats")  # New collection
        
        # Verify project exists
        project = await projects_collection.find_one({"_id": ObjectId(project_id)})
        if not project:
            raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found")
        
        # Get data sources
        data_sources = await dataSources_collection.find({"projectId": project_id}).to_list(None)
        if not data_sources:
            raise HTTPException(status_code=404, detail="No data sources found for this project")
            
        # Get relationships
        relationship = await relationships_collection.find_one(
            {"projectId": project_id},
            sort=[("createdAt", -1)]
        )
        relationships = relationship.get("relationships", []) if relationship else []
        
        # First, get code to generate stats
        data_source_info = []
        for ds in data_sources:
            source_info = {
                "filename": ds.get("filename"),
                "columns": [col.get("name") for col in ds.get("columnMetadata", [])],
                "column_types": {col.get("name"): col.get("type") for col in ds.get("columnMetadata", [])},
                "sample_data": ds.get("sampleData", [])[:2],
                "stats": ds.get("stats", {})
            }
            data_source_info.append(source_info)
        
        # Generate code prompt
        code_prompt = f"""
        I need Python code to calculate 4 key statistical insights about this data project.
        
        Project Details:
        Name: {project.get("name")}
        Nature of Data: {project.get("natureOfData")}
        Description: {project.get("description")}
        
        Available Data Sources:
        {json.dumps(data_source_info, indent=2)}
        
        Relationships between data sources:
        {json.dumps(relationships, indent=2)}
        
        Write a Python function that:
        1. Takes a dictionary of pandas DataFrames as input (key: filename, value: DataFrame)
        2. Calculates 4 key statistical insights
        3. Returns a list of 4 insight objects with these keys:
           - title: A short title for the insight
           - description: A detailed explanation
           - value: The key numerical value. Make sure it is a number.
           - type: The type of stat (count, percentage, average, etc.)
        
        The function should handle:
        - Data cleaning
        - Proper type conversion
        - Null value handling
        - Basic error handling

        
        
        Return ONLY the Python function with the name "calculate_insights" without any explanation.
        """
        
        # Get the code from LLM
        code_response = await query_azure_openai(code_prompt, response_type='text')
        
        # Now load the actual data from blob storage
        import pandas as pd
        import io
        from app.utils.blob_storage import download_from_blob_storage
        
        dataframes = {}
        for ds in data_sources:
            try:
                # Get blob path and download content
                blob_path = ds.get("blobPath")
                if not blob_path:
                    continue
                    
                blob_content = await download_from_blob_storage(blob_path)
                if not blob_content:
                    continue
                
                # Try different encodings to read the CSV
                try:
                    df = pd.read_csv(io.BytesIO(blob_content))
                except UnicodeDecodeError:
                    try:
                        df = pd.read_csv(io.BytesIO(blob_content), encoding='latin1')
                    except Exception:
                        df = pd.read_csv(io.BytesIO(blob_content), encoding='utf-8', errors='replace')
                
                dataframes[ds.get("filename")] = df
                logger.info(f"Loaded {len(df)} rows from {ds.get('filename')}")
                
            except Exception as e:
                logger.error(f"Error loading {ds.get('filename')}: {str(e)}")
                continue
        
        if not dataframes:
            raise HTTPException(status_code=500, detail="Could not load any data from storage")
        
        # Execute the generated code
        try:
            # Create namespace for execution
            namespace = {}
            exec(code_response.split("```python")[1].split("```")[0], namespace)
            calculate_insights = namespace.get('calculate_insights')
            
            if not calculate_insights:
                raise ValueError("Code did not define calculate_insights function")
            
            # Run the analysis
            insights = calculate_insights(dataframes)
            
            if not isinstance(insights, list):
                raise ValueError("Function did not return a list of insights")
            
            # After insights are generated and before returning response, save to MongoDB
            try:
                stats_document = {
                    "projectId": project_id,
                    "stats": insights[:4],
                    "generatedAt": datetime.now(),
                    "dataSourcesCount": len(dataframes),
                    "dataSourcesUsed": list(dataframes.keys()),
                    "status": "success"
                }
                
                # Insert the new stats document
                result = await project_stats_collection.insert_one(stats_document)
                
                # Update the project with reference to latest stats
                await projects_collection.update_one(
                    {"_id": ObjectId(project_id)},
                    {
                        "$set": {
                            "statsGenerated": True,
                            "lastUpdatedAt": datetime.now()
                        }
                    }
                )
                
                # Add stats document ID to response
                response = {
                    "success": True,
                    "project_id": project_id,
                    "stats_id": str(result.inserted_id),
                    "generated_at": stats_document["generatedAt"],
                    "stats": insights[:4]
                }
                
                return ensure_json_serializable(response)
                
            except Exception as e:
                logger.error(f"Error saving stats to database: {str(e)}")
                # Still return the insights even if saving fails
                return ensure_json_serializable({
                    "success": True,
                    "project_id": project_id,
                    "generated_at": datetime.now(),
                    "stats": insights[:4],
                    "warning": "Stats generated but not saved to database"
                })
            
        except Exception as e:
            logger.error(f"Error executing analysis code: {str(e)}")
            logger.error(f"Generated code: {code_response}")
            raise HTTPException(
                status_code=500,
                detail=f"Error calculating insights: {str(e)}"
            )
        
    except Exception as e:
        logger.error(f"Failed to generate project stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate project stats: {str(e)}"
        )

@router.get("/{project_id}/stats")
async def get_project_stats_endpoint(project_id: str):
    """Get the most recent statistical insights for a project."""
    try:
        # Get the stats collection
        project_stats_collection = get_collection("projectStats")
        
        # Get the most recent stats for this project
        stats = await project_stats_collection.find_one(
            {"projectId": project_id},
            sort=[("generatedAt", -1)]  # Get most recent
        )
        
        if not stats:
            return {
                "success": False,
                "message": "No stats found for this project",
                "project_id": project_id
            }
        
        return ensure_json_serializable({
            "success": True,
            "project_id": project_id,
            "stats_id": str(stats["_id"]),
            "generated_at": stats["generatedAt"],
            "stats": stats["stats"],
            "dataSourcesCount": stats["dataSourcesCount"],
            "dataSourcesUsed": stats["dataSourcesUsed"]
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch project stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch project stats: {str(e)}"
        )

@router.put("/{project_id}")
async def update_project_endpoint(project_id: str, project_update: Dict[str, Any] = Body(...)):
    """
    Update a project's details with any provided fields
    
    Args:
        project_id: The ID of the project to update
        project_update: Dictionary containing fields to update
        
    Returns:
        Updated project information
    """
    try:
        logger.info(f"Starting update for project ID: {project_id}")
        logger.debug(f"Update data received: {project_update}")
        
        # Get the projects collection
        projects_collection = get_collection("projects")
        logger.debug("Retrieved projects collection")
        
        # Verify project exists
        logger.info(f"Verifying project exists with ID: {project_id}")
        project = await projects_collection.find_one({"_id": ObjectId(project_id)})
        if not project:
            logger.warning(f"Project with ID {project_id} not found")
            raise HTTPException(
                status_code=404,
                detail=f"Project with ID {project_id} not found"
            )
        
        # Validate status if it's being updated
        if "status" in project_update:
            logger.info(f"Validating status update: {project_update['status']}")
            valid_statuses = ["CREATED", "IN_PROGRESS", "COMPLETED", "ARCHIVED", "READY"]
            if project_update["status"] not in valid_statuses:
                logger.warning(f"Invalid status provided: {project_update['status']}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                )
        
        # Don't allow updating certain fields
        logger.debug("Filtering out protected fields from update data")
        protected_fields = ["_id", "createdAt"]
        update_data = {
            k: v for k, v in project_update.items() 
            if k not in protected_fields
        }
        
        # Add last updated timestamp
        update_data["lastUpdatedAt"] = datetime.now()
        logger.debug(f"Final update data: {update_data}")
        
        if not update_data:
            logger.info("No changes requested for the project")
            return {
                "success": True,
                "message": "No changes requested",
                "project": ensure_json_serializable(project)
            }
        
        # Update the project
        logger.info(f"Updating project with ID: {project_id}")
        result = await projects_collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            logger.info(f"No modifications made to project {project_id}")
            return {
                "success": False,
                "message": "Project was not modified",
                "project": ensure_json_serializable(project)
            }
        
        # Get the updated project
        logger.info(f"Retrieving updated project with ID: {project_id}")
        updated_project = await projects_collection.find_one({"_id": ObjectId(project_id)})
        
        logger.info(f"Successfully updated project {project_id}")
        return {
            "success": True,
            "message": "Project updated successfully",
            "project": ensure_json_serializable(updated_project)
        }
        
    except Exception as e:
        logger.error(f"Failed to update project: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update project: {str(e)}"
        )
