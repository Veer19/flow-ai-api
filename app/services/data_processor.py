import pandas as pd
import os
from typing import List, Dict, Any
import json
from fastapi import HTTPException
from azure.storage.blob import BlobServiceClient
from app.config import get_settings
from io import StringIO

settings = get_settings()

def execute_chart_code(code_lines: List[str], dataset_id: str, blob_urls: Dict[str, str]) -> Dict[str, Any]:
    """Execute the generated code lines and return the chart data."""
    try:
        # Create a directory for this dataset if it doesn't exist
        dataset_dir = f"data/{dataset_id}"
        os.makedirs(dataset_dir, exist_ok=True)
        
        # Initialize Azure Blob Storage client
        blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
        container_client = blob_service_client.get_container_client(settings.AZURE_STORAGE_CONTAINER)
        
        # Download and save CSV files locally
        for filename, url in blob_urls.items():
            file_path = os.path.join(dataset_dir, filename)
            if not os.path.exists(file_path):
                # Get blob path from URL
                blob_path = url.split(settings.AZURE_STORAGE_CONTAINER + '/')[1]
                # Download using blob client
                blob_client = container_client.get_blob_client(blob_path)
                blob_data = blob_client.download_blob()
                content = blob_data.content_as_text()
                df = pd.read_csv(StringIO(content))
                df.to_csv(file_path, index=False)
        
        # Create a local namespace for code execution
        local_ns = {}
        
        # Execute each line of code
        for line in code_lines:
            if line.strip():  # Skip empty lines
                # Update file paths in code
                if "pd.read_csv" in line:
                    for filename in blob_urls.keys():
                        if filename in line:
                            line = line.replace(
                                f"'{filename}'", 
                                f"'data/{dataset_id}/{filename}'"
                            )
                
                # Execute the line
                exec(line, {"pd": pd}, local_ns)
        
        # Get the chart_data from the local namespace
        if "chart_data" not in local_ns:
            raise ValueError("Code did not generate 'chart_data'")
            
        return local_ns["chart_data"]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error executing chart code: {str(e)}"
        ) 