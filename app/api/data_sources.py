from fastapi import APIRouter, File, UploadFile
import logging
from app.config import get_settings
from app.services.data_sources import get_data_sources, upload_data_source, delete_data_source
from app.api.auth import verify_jwt_token
from fastapi import Depends
from app.models.data_sources import DataSource
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
router = APIRouter()

@router.get("")
async def get_data_sources_endpoint(project_id: str, user: dict = Depends(verify_jwt_token)) -> list[DataSource]:
    """
    Get all files associated with a specific project
    """
    return await get_data_sources(project_id, user.get("sub"))

@router.post("")
async def upload_data_source_endpoint(
    project_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(verify_jwt_token)
) -> DataSource:
    """Upload a single CSV file to Azure Blob Storage and associate with a project."""
    
    return await upload_data_source(project_id, file, user.get("sub"))

@router.delete("/{data_source_id}")
async def delete_data_source_endpoint(
    project_id: str,
    data_source_id: str,
    user: dict = Depends(verify_jwt_token)
) -> bool:
    """Delete a data source from Azure Blob Storage and MongoDB."""
    
    return await delete_data_source(project_id, data_source_id, user.get("sub"))
   
