from fastapi import APIRouter, HTTPException
from datetime import datetime
from bson.objectid import ObjectId
import logging
import json
from app.services.mongodb import get_collection
from app.config import get_settings
from app.services.projects import get_project
from app.models.relationships import Relationship, RelationshipLLMResponse
from app.utils.llm_provider import ainvoke_llm
from app.utils.prompt_engine import render_prompt
from typing import List
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
router = APIRouter()

async def establish_relationships(project_id: str, user_id: str):
    """
    Delete all existing relationships for a project and generate new ones
    based on the current data sources.
    """
    try:
        # Get the project from MongoDB
        projects_collection = get_collection("projects")
        relationships_collection = get_collection("relationships")
        
        # Verify project exists
        await get_project(project_id, user_id)
        
        # Get dataSources collection
        dataSources_collection = get_collection("dataSources")

        # Get all files from the dataSources collection
        data_sources = await dataSources_collection.find({"projectId": project_id}).to_list(None)
        
        # Ensure we have at least 2 data sources to find relationships
        if len(data_sources) < 2:
            return []
        
       
        
        # Prepare data for LLM analysis
        data_source_info = []
        for ds in data_sources:
            # Extract essential information for each data source
            source_info = {
                "id": ds.get("id"),
                "filename": ds.get("filename"),
                "rows": ds.get("rows"),
                "columns": [col.get("name") for col in ds.get("columnMetadata", [])],
                "column_types": {col.get("name"): col.get("type") for col in ds.get("columnMetadata", [])},
                "sample_data": ds.get("sampleData", [])[:2]  # Just a couple of rows for context
            }
            data_source_info.append(source_info)
        
        # Call the LLM to analyze relationships
        system_prompt = render_prompt("establish_relationships/system.jinja")
        user_prompt = render_prompt("establish_relationships/user.jinja", {
            "data_sources": data_source_info
        })
        llm_response: RelationshipLLMResponse = await ainvoke_llm(
            user_prompt=user_prompt, 
            system_prompt=system_prompt,
            profile="analyze",
            response_model=RelationshipLLMResponse
        )
        relationships = llm_response.relationships
        if len(relationships) == 0:
            return []
        now = datetime.now()
        relationships = [
            {
                **relationship.model_dump(), 
                "projectId": project_id, 
                "userId": user_id,
                "createdAt": now
            } for relationship in llm_response.relationships
        ]
         # Delete all existing relationships for this project
        await relationships_collection.delete_many({"projectId": project_id, "userId": user_id})
        # Insert the new relationship document
        await relationships_collection.insert_many(relationships)
        
        # Update the project with the latest relationship analysis
        await projects_collection.update_one(
            {"_id": ObjectId(project_id)},
            {
                "$set": {
                    "lastUpdatedAt": now
                }
            }
        )

        created_relationships = []
        async for relationship in relationships_collection.find({"projectId": project_id, "userId": user_id}):
            created_relationships.append(Relationship(id=str(relationship["_id"]), **relationship))
        
        return created_relationships
    
    except Exception as e:
        logger.error(f"Relationship regeneration failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Relationship regeneration failed: {str(e)}"
        )

async def get_relationships(project_id: str, user_id: str) -> List[Relationship]:
    """
    Get all relationships for a project including datasets, models, and data sources.
    """
    try:
        relationships_collection = get_collection("relationships")
        
        await get_project(project_id, user_id)

        relationships = []
        async for relationship in relationships_collection.find({"projectId": project_id, "userId": user_id}):
            relationships.append(Relationship(id=str(relationship["_id"]), **relationship))
        
        return relationships
        
    except Exception as e:
        logger.error(f"Failed to fetch project relationships: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch project relationships: {str(e)}"
        )

async def generate_relationships_ai(project_id: str, user_id: str):
    """
    Generate relationships for a project using AI
    """
    pass


