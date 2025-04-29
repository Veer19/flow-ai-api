from fastapi import APIRouter, HTTPException, Query
from app.services.mongodb import get_database
from app.services.azure_ai import generate_python_code, generate_chart_suggestions, generate_chart_options
from azure.storage.blob import BlobServiceClient
from app.config import get_settings
import pandas as pd
from typing import List, Dict, Any
import json
from app.services.data_processor import execute_chart_code
from app.services.mongodb import get_collection
from bson.objectid import ObjectId
from app.utils.generate_charts import generate_chart, generate_chart_concepts
from app.utils.json_encoders import ensure_json_serializable

settings = get_settings()
router = APIRouter()

@router.get("/{project_id}")
async def get_saved_charts(project_id: str):
    """Get all charts for a project"""
    try:
        project_collection = get_collection("projects")
        charts_collection = get_collection("charts")
        project = await project_collection.find_one({"_id": ObjectId(project_id)})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get all charts for the project
        charts = await charts_collection.find({"projectId": project_id}).to_list(None)
        return ensure_json_serializable(charts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting charts: {str(e)}")

@router.post("/{project_id}/concepts")
async def get_charts_concepts(project_id: str):
    """Get all charts for a project"""
    try:
        project_collection = get_collection("projects")
        charts_collection = get_collection("charts")
        project = await project_collection.find_one({"_id": ObjectId(project_id)})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        charts = None
        # If charts are empty call a function to generate charts
        if not charts:
            response = await generate_chart_concepts(project_id)
            if response["success"]:
                charts = response["charts"]
                # Add status as "concept"
                for chart in charts:
                    chart["status"] = "concept"
                await charts_collection.insert_many(charts)
                return ensure_json_serializable(charts)
            else:
                raise HTTPException(status_code=500, detail=response["error"])
        return ensure_json_serializable(charts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting charts: {str(e)}")
    
@router.post("/{chart_id}/generate")
async def generate_chart_data(chart_id: str):
    """Get all charts for a project"""
    try:
        project_collection = get_collection("projects")
        charts_collection = get_collection("charts")
        chart = await charts_collection.find_one({"_id": ObjectId(chart_id)})
        if not chart:
            raise HTTPException(status_code=404, detail="Chart not found")
        project_id = chart["projectId"]
        project = await project_collection.find_one({"_id": ObjectId(project_id)})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        response = await generate_chart(chart)
        if response:
            generated_chart = response
            # Add status as "concept"
            generated_chart["status"] = "generated"
            await charts_collection.update_one({"_id": ObjectId(chart_id)}, {"$set": generated_chart})
            return ensure_json_serializable(generated_chart)
        else:
            raise HTTPException(status_code=500, detail=response["error"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting charts: {str(e)}")

@router.post("/render-chart-data/{dataset_id}")
async def render_chart_data(dataset_id: str, chart_config: Dict[str, Any]):
    """Generate Python code for processing data based on the chart description and dataset."""
    try:
        # Get dataset information
        db = get_database()
        dataset = await db.datasets.find_one({"_id": dataset_id})
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        # Load data structure information
        data_context = "Available data structure:\n"
        for file_info in dataset["files"]:
            if file_info["success"]:
                data_context += f"\nTable: {file_info['filename']}\n"
                for col_name, col_type in file_info["column_types"].items():
                    data_context += f"- {col_name} ({col_type})\n"
                    if file_info["unique_values"][file_info["column_names"].index(col_name)]:
                        unique_vals = file_info["unique_values"][file_info["column_names"].index(col_name)]
                        data_context += f"  Unique values: {unique_vals}\n"
                data_context += "Sample data:\n"
                for row in file_info["sample_data"][:2]:
                    data_context += f"- {row}\n"
        
        # Add relationships if available
        if dataset.get("relationships"):
            data_context += "\nRelationships:\n"
            for rel in dataset["relationships"]:
                data_context += f"- {rel['tableA']}.{rel['keyA']} → {rel['tableB']}.{rel['keyB']}\n"

        prompt = f"""
        {data_context}

        Generate Python code to create a {chart_config['chart_type']} chart:
        Title: {chart_config['title']}
        Description: {chart_config['description']}
        Columns involved: {chart_config['columns_involved']}

        The code should:
        1. Load and process the correct CSV file(s)
        2. Handle data cleaning and aggregation
        3. Return the processed data in a format suitable for a {chart_config['chart_type']} chart
        """
                
        code = await generate_python_code(prompt)
        code_lines = json.loads(code)
        
        # Execute the code and get results
        chart_data = execute_chart_code(
            code_lines=code_lines,
            dataset_id=dataset_id,
            blob_urls=dataset["blob_urls"]
        )
        
        chart_options = await generate_chart_options(data_context, chart_config)

        return {
            "type": chart_config["chart_type"],
            "series": chart_data,
            "options": chart_options,
            "code": code_lines,
            "config": chart_config,
            "dataset_id": dataset_id
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating chart code: {str(e)}"
        )