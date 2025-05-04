from app.services.mongodb import get_collection
from app.models.projects import ProjectCreate, ProjectResponse
from fastapi import HTTPException
from datetime import datetime
import logging
from app.utils.json_encoders import ensure_json_serializable
from bson.objectid import ObjectId
logger = logging.getLogger(__name__)

async def create_project(project: ProjectCreate):
    """
    Create a new project document in MongoDB
    """
    try:
        # Get the projects collection
        projects_collection = get_collection("projects")
        
        # Create the project document
        project_data = {
            "name": project.name,
            "natureOfData": project.natureOfData,
            "description": project.description,
            "status": "CREATED",
            "createdAt": datetime.now(),
            "lastUpdatedAt": datetime.now(),
        }
        
        # Insert the document
        result = await projects_collection.insert_one(project_data)
        
        # Return the created project with ID
        return ProjectResponse(
            id=str(result.inserted_id),
            **project_data
        )
    except Exception as e:
        # Log the error for debugging
        logger.error(f"Failed to create project: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


async def get_projects():
    """
    Get all projects from MongoDB with complete structure
    """
    try:
        # Get the projects collection
        projects_collection = get_collection("projects")
        
        # Fetch all projects - using async iteration
        projects = []
        async for project in projects_collection.find():
            # Build complete project structure with defaults
            formatted_project = ProjectResponse(
                id=str(project["_id"]),
                name=project.get("name"),
                natureOfData=project.get("natureOfData"),
                description=project.get("description"),
                status=project.get("status"),
                createdAt=project.get("createdAt"),
                lastUpdatedAt=project.get("lastUpdatedAt", project.get("createdAt"))
            )
            projects.append(formatted_project)
        
        return ensure_json_serializable(projects)
        
    except Exception as e:
        logger.error(f"Failed to fetch projects: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch projects: {str(e)}")

async def get_project(project_id: str):
    """
    Get a specific project by ID with complete structure
    """
    try:
        # Get the projects collection
        projects_collection = get_collection("projects")
        
        # Find the project by ID
        try:
            project = await projects_collection.find_one({"_id": ObjectId(project_id)})
        except Exception as e:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Return complete project structure with defaults
        formatted_project = ProjectResponse(
            id=str(project["_id"]),
            name=project.get("name"),
            natureOfData=project.get("natureOfData"),
            description=project.get("description"),
            status=project.get("status", "CREATED"),
            createdAt=project.get("createdAt"),
            lastUpdatedAt=project.get("lastUpdatedAt", project.get("createdAt"))
        )
        
        return ensure_json_serializable(formatted_project)
        
    except Exception as e:
        logger.error(f"Failed to fetch project: {str(e)}")
        raise HTTPException(status_code=e.status_code, detail=f"Failed to fetch project: {str(e.detail)}")
    
async def get_project_data_sources(project_id: str):
    """
    Get all files associated with a specific project
    """
    try:
        # Get the projects collection
        projects_collection = get_collection("projects")
        # Get the dataSources collection
        dataSources_collection = get_collection("dataSources")
        
        # Verify project exists
        project = await projects_collection.find_one({"_id": ObjectId(project_id)})
        if not project:
            raise HTTPException(
                status_code=404,
                detail=f"Project with ID {project_id} not found"
            )
        
        # Get all files from the dataSources collection
        cursor = dataSources_collection.find({"projectId": project_id})
        files = await cursor.to_list(None)
        
        # Ensure the files are JSON serializable
        safe_files = ensure_json_serializable(files)
        
        return safe_files
        
    except Exception as e:
        logger.error(f"Failed to fetch project files: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch project files: {str(e)}"
        )