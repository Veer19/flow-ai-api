from app.models.stats import ProjectStats
from fastapi import HTTPException
from typing import List
from app.services.mongodb import get_collection
import logging
from app.services.projects import get_project
from app.utils.llm_provider import ainvoke_llm
from app.utils.prompt_engine import render_prompt
from app.models.stats import StatsLLMResponse
from datetime import datetime
from bson.objectid import ObjectId
import json
from app.utils.json_encoders import ensure_json_serializable
from app.utils.blob_storage import get_dataframes_dict
from app.utils.code_executer import execute_pandas_code
from app.services.data_sources import get_data_sources
from app.services.relationships import get_relationships
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def generate_stats(project_id: str, user_id: str = "google-oauth2|105273317112514853668") -> List[ProjectStats]:
    """
    Generate statistical insights for a project
    """
    try:
        # Get the project from MongoDB
        projects_collection = get_collection("projects")
        stats_collection = get_collection("projectStats")
        relationships_collection = get_collection("relationships")
        dataSources_collection = get_collection("dataSources")
        
        # Verify project exists
        project = await get_project(project_id, user_id)
        
        # Get dataSources collection

        # Get all files from the dataSources collection
        data_sources = await get_data_sources(project_id, user_id)
            
        
        relationships = await get_relationships(project_id, user_id)
       
        
        # Prepare data for LLM analysis
        data_source_info = [ds.to_llm_dict() for ds in data_sources]
        relationships_info = [r.to_llm_dict() for r in relationships]
        
        # Call the LLM to analyze relationships
        system_prompt = render_prompt("generate_kpis/system.jinja")
        user_prompt = render_prompt("generate_kpis/user.jinja", {
            "project_details": ensure_json_serializable(project),
            "data_sources": ensure_json_serializable(data_source_info),
            "relationships": ensure_json_serializable(relationships_info),
            "number_of_kpis": 4
        })
        llm_response: StatsLLMResponse = await ainvoke_llm(
            user_prompt=user_prompt, 
            system_prompt=system_prompt,
            profile="analyze",
            response_model=StatsLLMResponse
        )
        stats = llm_response.stats
        all_used_data_source_ids = []
        for stat in stats:
            all_used_data_source_ids.extend(stat.data_sources_used)
        all_used_data_source_ids = list(set(all_used_data_source_ids))
        
        dataframes = await get_dataframes_dict(data_sources, all_used_data_source_ids)
        
        now = datetime.now()
        stats_with_value = []
        for stat in stats:
            result = execute_pandas_code(stat.python_code, dataframes, 'get_kpi_value')
            print(result)
            stats_with_value.append({
                "title": stat.title,
                "description": stat.description,
                "type": stat.type,
                "projectId": project_id,
                "userId": user_id,
                "value": result,
                "createdAt": now,
                "data_sources_used": stat.data_sources_used,
                "python_code": stat.python_code
            })
         # Delete all existing relationships for this project 
        await stats_collection.delete_many({"projectId": project_id, "userId": user_id})
        # Insert the new relationship document
        await stats_collection.insert_many(stats_with_value)
        

        created_stats = []
        async for stat in stats_collection.find({"projectId": project_id, "userId": user_id}):
            created_stats.append(ProjectStats(id=str(stat["_id"]), **stat))
        
        # Update the project with the latest stats
        await projects_collection.update_one(
            {"_id": ObjectId(project_id)},
            {
                "$set": {
                    "stats": [stat.model_dump() for stat in created_stats],
                    "lastUpdatedAt": now
                }
            }
        )
        
        return created_stats
    
    except Exception as e:
        logger.error(f"Stats generation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Stats generation failed: {str(e)}"
        )

async def get_project_stats(project_id: str, user_id: str) -> List[ProjectStats]:
    """Get the most recent statistical insights for a project."""
    try:
        # Get the stats collection
        stats_collection = get_collection("projectStats")

        await get_project(project_id, user_id)
        
        # Get the most recent stats for this project
        
        stats = []
        async for stat in stats_collection.find(
            {"projectId": project_id, "userId": user_id}
        ):
            stats.append(ProjectStats(id=str(stat["_id"]), **stat))
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to fetch project stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch project stats: {str(e)}"
        )
