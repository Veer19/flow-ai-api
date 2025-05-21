from fastapi import APIRouter, Body
from typing import Dict, Any
import logging
from app.config import get_settings
from app.models.projects import ProjectRequestBody, Project
from app.services.projects import create_project, get_projects, get_project, update_project
from app.api.auth import verify_jwt_token
from fastapi import Depends
from app.api.threads import router as threads_router
from app.api.data_sources import router as data_sources_router
from app.api.relationships import router as relationships_router
from app.api.stats import router as stats_router
from app.api.visuals import router as visuals_router

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
router = APIRouter()


@router.post("", response_model=Project)
async def create_project_endpoint(
    project: ProjectRequestBody = Body(...), 
    user: dict = Depends(verify_jwt_token)
) -> Project:
    """
    Create a new project document in MongoDB
    """
    return await create_project(user.get("sub"), project)


@router.get("", response_model=list[Project])
async def get_projects_endpoint(
    user: dict = Depends(verify_jwt_token)
) -> list[Project]:
    """
    Get all projects from MongoDB with complete structure
    """
    return await get_projects(user.get("sub"))

@router.get("/{project_id}", response_model=Project)
async def get_project_endpoint(
    project_id: str, 
    user: dict = Depends(verify_jwt_token)
) -> Project:
    """
    Get a specific project by ID with complete structure
    """
    return await get_project(project_id, user.get("sub"))


@router.put("/{project_id}")
async def update_project_endpoint(
    project_id: str, 
    project_update: Dict[str, Any] = Body(...), 
    user: dict = Depends(verify_jwt_token)
) -> Project:
    """
    Update a project's details with any provided fields
    """
    return await update_project(project_id, project_update, user.get("sub"))
    

router.include_router(data_sources_router, prefix="/{project_id}/data-sources", tags=["data-sources"])
router.include_router(relationships_router, prefix="/{project_id}/relationships", tags=["relationships"])
router.include_router(stats_router, prefix="/{project_id}/stats", tags=["stats"])
router.include_router(visuals_router, prefix="/{project_id}/visuals", tags=["visuals"])
router.include_router(threads_router, prefix="/{project_id}/threads", tags=["threads"])
