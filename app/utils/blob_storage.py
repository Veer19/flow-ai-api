import logging
from azure.storage.blob import BlobServiceClient
from app.config import get_settings
import pandas as pd
import io
from app.models.data_sources import DataSource

# Set up logging
logger = logging.getLogger(__name__)
settings = get_settings()

async def upload_to_blob_storage(content: bytes, blob_path: str) -> str:
    """
    Upload content to Azure Blob Storage.
    
    Args:
        content: The raw bytes to upload
        blob_path: The path/name for the blob
        
    Returns:
        URL of the uploaded blob
        
    Raises:
        Exception: If upload fails
    """
    logger.info(f"Uploading to blob storage: {blob_path}")
    
    try:
        # Initialize Azure Blob Storage client
        blob_service_client = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
        container_client = blob_service_client.get_container_client(
            settings.AZURE_STORAGE_CONTAINER
        )
        
        # Upload to Azure Blob Storage
        blob_client = container_client.get_blob_client(blob_path)
        blob_client.upload_blob(content)
        
        logger.info(f"Successfully uploaded blob: {blob_path}")
        return blob_client.url
    
    except Exception as e:
        logger.error(f"Failed to upload to blob storage: {str(e)}")
        raise

async def cleanup_uploaded_blobs(blobs: list[dict[str, str]]):
    """
    Clean up blobs that were uploaded before an error occurred.
    
    Args:
        blobs: List of dictionaries with 'path' and 'url' keys
    """
    if not blobs:
        return
        
    logger.info(f"Cleaning up {len(blobs)} uploaded blobs")
    
    try:
        blob_service_client = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
        container_client = blob_service_client.get_container_client(
            settings.AZURE_STORAGE_CONTAINER
        )
        
        for blob in blobs:
            try:
                blob_path = blob.get("path")
                if blob_path:
                    blob_client = container_client.get_blob_client(blob_path)
                    blob_client.delete_blob()
                    logger.info(f"Deleted blob: {blob_path}")
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up blob {blob.get('path')}: {str(cleanup_error)}")
    except Exception as e:
        logger.error(f"Error initializing blob client for cleanup: {str(e)}")

async def download_from_blob_storage(blob_path: str) -> bytes:
    """
    Download a file from Azure Blob Storage
    
    Args:
        blob_path: The path to the blob in storage
        
    Returns:
        The blob content as bytes, or None if download fails
    """
    try:
        # Get settings
        settings = get_settings()
        
        # Create the BlobServiceClient
        blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
        
        # Get the container client
        container_client = blob_service_client.get_container_client(settings.AZURE_STORAGE_CONTAINER)
        
        # Get the blob client
        blob_client = container_client.get_blob_client(blob_path)
        
        # Download the blob - use synchronous methods
        download_stream = blob_client.download_blob()
        blob_content = download_stream.readall()
        
        logger.info(f"Successfully downloaded blob: {blob_path}")
        return blob_content
        
    except Exception as e:
        logger.error(f"Error downloading blob {blob_path}: {str(e)}")
        return None 
    
async def generate_blob_df(blob_path: str) -> pd.DataFrame:
    """
    Generate a CSV from a blob
    """
    # Now load the actual data from blob storage
    
    try:
        # Get blob path and download content       
        blob_content = await download_from_blob_storage(blob_path)
       
        # Try different encodings to read the CSV
        try:
            df = pd.read_csv(io.BytesIO(blob_content))
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(io.BytesIO(blob_content), encoding='latin1')
            except Exception:
                df = pd.read_csv(io.BytesIO(blob_content), encoding='utf-8', errors='replace')
        
        return df
        
    except Exception as e:
        logger.error(f"Error loading {blob_path}: {str(e)}")
        return None


async def get_dataframes_dict(data_sources: list[DataSource], data_source_ids: list[str] = None) -> dict[str, pd.DataFrame]:
    """
    Get a dictionary of dataframes for the given data source ids
    """
    if data_source_ids:
        used_data_sources = [ds for ds in data_sources if str(ds.id) in data_source_ids]
    else:
        used_data_sources = data_sources
    dataframes = {}
    for data_source in used_data_sources:
        df = await generate_blob_df(data_source.blobPath)
        dataframes[str(data_source.id)] = df
    return dataframes