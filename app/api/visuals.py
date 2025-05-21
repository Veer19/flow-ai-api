from fastapi import APIRouter, Depends
from app.config import get_settings
from app.api.auth import verify_jwt_token
from app.services.visuals import get_visuals, generate_visuals

settings = get_settings()
router = APIRouter()

@router.get("")
async def get_visuals_endpoint(project_id: str, user: dict = Depends(verify_jwt_token)):
    """Get all charts for a project"""
    return await get_visuals(project_id, user.get("sub"))

@router.post("")
async def generate_visuals_endpoint(project_id: str, user: dict = Depends(verify_jwt_token)):
    """Generate visual concepts for a project"""
    return await generate_visuals(project_id, user.get("sub"))
