from fastapi import APIRouter
from app.config import get_settings
from app.services.stats import get_project_stats, generate_stats
from app.api.auth import verify_jwt_token
from fastapi import Depends
from app.models.stats import ProjectStats
from typing import List
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
router = APIRouter()


@router.post("")
async def generate_project_stats_endpoint(project_id: str, user: dict = Depends(verify_jwt_token)) -> List[ProjectStats]:
    return await generate_stats(project_id, user.get("sub"))

@router.get("")
async def get_project_stats_endpoint(project_id: str, user: dict = Depends(verify_jwt_token)):
    """Get the latest project stats for a project."""
    return await get_project_stats(project_id, user.get("sub"))
