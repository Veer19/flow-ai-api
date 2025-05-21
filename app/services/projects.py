from fastapi import HTTPException
from app.services.mongodb import get_collection
from app.models.projects import ProjectRequestBody, Project
from datetime import datetime
import logging
from bson.objectid import ObjectId

logger = logging.getLogger(__name__)

async def create_project(user_id: str, project: ProjectRequestBody):
    """
    Create a new project document in MongoDB
    """
    try:
        # Get the projects collection
        projects_collection = get_collection("projects")
        
        # Create the project document as a dictionary
        project_data = {
            "name": project.name,
            "description": project.description,
            "status": "CREATED",
            "createdAt": datetime.now(),
            "userId": user_id,
            "lastUpdatedAt": datetime.now(),
        }
        
        # Insert the document
        result = await projects_collection.insert_one(project_data)
        
        # Get the created project
        created_project = await projects_collection.find_one({"_id": result.inserted_id})
        
        # Convert to Pydantic model for response
        return Project(
            id=str(created_project["_id"]),
            **created_project
        )
        
    except Exception as e:
        logger.error(f"Failed to create project: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


async def get_projects(user_id: str):
    """
    Get all projects from MongoDB with complete structure
    """
    try:
        # Get the projects collection
        projects_collection = get_collection("projects")
        
        # Fetch all projects - using async iteration
        projects = []
        async for project in projects_collection.find({"userId": user_id}):
            projects.append(Project(id=str(project["_id"]), **project))
        
        return projects
        
    except Exception as e:
        logger.error(f"Failed to fetch projects: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch projects: {str(e)}")

async def get_project(project_id: str, user_id: str):
    """
    Get a specific project by ID with complete structure
    """
    try:
        logger.info(f"Fetching project {project_id} for user {user_id}")
        # Get the projects collection
        projects_collection = get_collection("projects")
        
        # Find the project by ID
        try:
            project = await projects_collection.find_one({
                "_id": ObjectId(project_id), 
                "userId": user_id
            })
        except Exception as e:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return Project(id=str(project["_id"]), **project)
        
    except Exception as e:
        logger.error(f"Failed to fetch project: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch project: {str(e)}")
    
async def update_project(project_id: str, project_update: dict, user_id: str):
    """
    Update a project's details with any provided fields
    """
    try:
        logger.info(f"Starting update for project ID: {project_id}")
        logger.debug(f"Update data received: {project_update}")
        
        # Get the projects collection
        projects_collection = get_collection("projects")
        logger.debug("Retrieved projects collection")
        
        # Verify project exists
        logger.info(f"Verifying project exists with ID: {project_id}")
        await get_project(project_id, user_id)
        
        # Update the project
        await projects_collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": project_update}
        )

        # Return updated project
        updated_project = await get_project(project_id, user_id)
        return updated_project
        
    except Exception as e:
        logger.error(f"Failed to update project: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update project: {str(e)}"
        )


