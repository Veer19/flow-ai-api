import logging
import json
from datetime import datetime
from bson.objectid import ObjectId
from typing import List, Dict, Any

from app.services.azure_ai import query_azure_openai
from app.services.mongodb import get_collection
from app.utils.json_encoders import ensure_json_serializable

# Set up logging
logger = logging.getLogger(__name__)

async def analyze_relationships(project_id: str, data_sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze relationships between data sources in a project.
    
    Args:
        project_id: The ID of the project
        data_sources: List of data source documents
        
    Returns:
        Dictionary with relationship analysis results
    """
    logger.info(f"Analyzing relationships for project {project_id} with {len(data_sources)} data sources")
    
    try:
        # Get the collections
        projects_collection = get_collection("projects")
        relationships_collection = get_collection("relationships")
        
        # Delete all existing relationships for this project
        delete_result = await relationships_collection.delete_many({"projectId": project_id})
        deleted_count = delete_result.deleted_count
        logger.info(f"Deleted {deleted_count} existing relationships for project {project_id}")
        
        # Prepare data for LLM analysis
        data_source_info = []
        for ds in data_sources:
            # Extract essential information for each data source
            source_info = {
                "id": ds.get("id"),
                "filename": ds.get("filename"),
                "columns": [col.get("name") for col in ds.get("columnMetadata", [])],
                "column_types": {col.get("name"): col.get("type") for col in ds.get("columnMetadata", [])},
                "sample_data": ds.get("sampleData", [])[:2]  # Just a couple of rows for context
            }
            data_source_info.append(source_info)
        
        # Construct prompt for the LLM
        prompt = f"""
        I have {len(data_sources)} datasets in my project. I need to understand how they might be related.
        
        Here are the datasets with their column information:
        
        {json.dumps(data_source_info, indent=2)}
        
        Please analyze these datasets and identify potential join keys between datasets (columns that could be used to join datasets together).
        For each relationship, provide:
        - The two datasets involved
        - The type of relationship
        - The columns that establish the relationship
        - Confidence level (high, medium, low)
        - A brief explanation of why you think this relationship exists
        
        Format your response as a JSON object with a "relationships" array.
        """
        
        # Call the LLM to analyze relationships
        logger.info("Calling LLM to analyze relationships")
        llm_response = await query_azure_openai(prompt)
        
        # Parse the LLM response to extract the JSON
        try:
            # Check if the response is already a dictionary (might be pre-parsed)
            if isinstance(llm_response, dict):
                relationships_data = llm_response
            else:
                # Find JSON in the response string
                json_start = llm_response.find('{')
                json_end = llm_response.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = llm_response[json_start:json_end]
                    relationships_data = json.loads(json_str)
                else:
                    # If no JSON found, try to parse the whole response
                    relationships_data = json.loads(llm_response)
        except json.JSONDecodeError:
            # If JSON parsing fails, extract structured data manually
            logger.warning("Failed to parse LLM response as JSON")
            relationships_data = {
                "relationships": [],
                "raw_llm_response": str(llm_response)  # Convert to string to ensure it's serializable
            }
        
        # Store the relationship analysis in a new document
        relationship_doc = {
            "projectId": project_id,
            "relationships": relationships_data.get("relationships", []),
            "raw_llm_response": str(llm_response) if isinstance(llm_response, str) else json.dumps(llm_response),
            "dataSourceCount": len(data_sources),
            "createdAt": datetime.now().isoformat()
        }
        
        # Store in relationships collection
        await relationships_collection.insert_one(relationship_doc)
        
        # Also update the project with the latest relationship analysis
        await projects_collection.update_one(
            {"_id": ObjectId(project_id)},
            {
                "$set": {
                    "lastRelationshipAnalysis": datetime.now().isoformat(),
                    "relationshipCount": len(relationships_data.get("relationships", []))
                }
            }
        )
        
        return {
            "success": True,
            "message": "Relationships analyzed successfully",
            "relationships_analyzed": True,
            "old_relationships_deleted": deleted_count,
            "new_relationships_created": len(relationships_data.get("relationships", []))
        }
        
    except Exception as e:
        logger.error(f"Error analyzing relationships: {str(e)}")
        return {
            "success": True,
            "message": "Files uploaded successfully but relationship analysis failed",
            "relationships_analyzed": False,
            "error": str(e)
        } 