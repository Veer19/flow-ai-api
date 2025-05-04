import json
import re
import io
import pandas as pd
from typing import List, Dict, Any
from app.services.project_service import get_project_data_sources
from app.utils.blob_storage import download_from_blob_storage
from .config import AgentState
import asyncio
import time


async def get_datasets(project_id: str) -> List[Dict[str, Any]]:
    """Get all datasets for a project"""
    return await get_project_data_sources(project_id)

async def load_dataset(blob_path: str) -> pd.DataFrame:
    """Load a dataset from blob storage"""
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

async def execute_pandas_code(required_datasets: List[Dict[str, Any]], generated_code: str) -> Any:
    """Execute generated pandas code safely"""
    # Print start time
    start_time = time.time()
    print(f"Start time: {start_time}")
    print("EXECUTING PANDAS CODE")
    print(generated_code)
    namespace = {}
    exec(generated_code, namespace)
    analyze_data = namespace.get('analyze_data')
    
    if not analyze_data:
        raise ValueError("Code did not define analyze_data function")
    print("ANALYZE DATA")
    print(analyze_data)
    # Run the analysis
    dataframes = await save_datesets_to_dfs(required_datasets)
    print("DATAFRAMES")
    print(dataframes)
    result = analyze_data(dataframes)
    # Print end time
    end_time = time.time()
    print(f"End time: {end_time}")
    print(f"Time taken: {end_time - start_time} seconds")
    print("RESULT")
    print(result)
    return result

async def save_datesets_to_dfs(datasets: List[Dict[str, Any]]) -> Dict[str, pd.DataFrame]:
    """Save datasets to dataframes"""
    tasks = [
        load_dataset(dataset['blobPath']) for dataset in datasets
    ]
    filenames = [d['filename'] for d in datasets]
    # Kick off all loads concurrently
    loaded_data = await asyncio.gather(*tasks)
    # Map filenames to their corresponding DataFrames
    dataframes = dict(zip(filenames, loaded_data))
    return dataframes

def prepare_datasets_for_prompt(datasets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def clean_dataset(ds):
        return {
            "id": ds["_id"],
            "filename": ds["filename"],
            "rows": ds.get("rows", 0),
            "columns": ds.get("columns", 0),
            "columnMetadata": ds.get("columnMetadata", []),
            "sampleData": ds.get("sampleData", [])[:1],
        }
    return [clean_dataset(d) for d in datasets]

def extract_json_from_llm_response(content: str) -> Dict[str, Any]:
    try:
        json_match = re.search(r"{.*}", content, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON object found in response.")
        return json.loads(json_match.group(0))
    except Exception as e:
        raise ValueError(f"Failed to parse JSON from LLM response: {str(e)}") from e

def extract_code_block(content: str) -> str:
    """Extracts the first Python code block from markdown-style content"""
    match = re.search(r"```python\s+(.*?)```", content, re.DOTALL)
    if not match:
        raise ValueError("No Python code block found in LLM response.")
    return match.group(1).strip()