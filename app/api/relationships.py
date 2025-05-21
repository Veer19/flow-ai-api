from fastapi import APIRouter, Depends
import logging
from app.config import get_settings
from app.api.auth import verify_jwt_token
from app.services.relationships import establish_relationships, get_relationships
from app.models.relationships import Relationship
from typing import List

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
router = APIRouter()

@router.post("")
async def establish_relationships_endpoint(project_id: str, user: dict = Depends(verify_jwt_token)) -> List[Relationship]:
    """
    Delete all existing relationships for a project and generate new ones
    based on the current data sources.
    """
    return await establish_relationships(project_id, user.get("sub"))

@router.get("")
async def get_project_relationships_endpoint(project_id: str, user: dict = Depends(verify_jwt_token)) -> List[Relationship]:
    """
    Get all relationships for a project including datasets, models, and data sources.
    """
    return await get_relationships(project_id, user.get("sub"))
