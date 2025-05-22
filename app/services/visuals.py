from app.services.mongodb import get_collection
from fastapi import HTTPException
from app.services.projects import get_project
from app.models.visuals import Visual
from typing import List
import asyncio
import logging
from app.services.data_sources import get_data_sources
from app.services.relationships import get_relationships
from app.utils.json_encoders import ensure_json_serializable
import json
from pathlib import Path
from app.models.visuals import VisualType, VisualConceptsLLMResponse, VisualConcept, VisualSampleDataLLMResponse, VisualData, VisualPythonCodeLLMResponse
from app.utils.prompt_engine import render_prompt
from app.utils.llm_provider import ainvoke_llm
from app.models.data_sources import DataSource
from app.services.stats import get_project_stats
from app.models.stats import ProjectStats
from app.models.relationships import Relationship
from app.models.projects import Project
from app.utils.code_executer import execute_pandas_code
from app.utils.blob_storage import get_dataframes_dict
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_visuals(project_id: str, user_id: str):
    """Get all visuals for a project"""
    try:
        visuals_collection = get_collection("visuals")
        await get_project(project_id, user_id)

        # Get all charts for the project
        visuals: List[Visual] = []
        async for visual in visuals_collection.find({"project_id": project_id, "user_id": user_id}):
            visuals.append(Visual(id=str(visual["_id"]), **visual))

        return visuals
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting charts: {str(e)}")


async def generate_visual_concepts(project: Project, data_sources: List[DataSource], stats: List[ProjectStats], relationships: List[Relationship]):
    """Create a new visual for a project"""
    try:
        # Fetch project data

        # Prepare data source information for the LLM
        data_source_info = [ds.to_llm_dict() for ds in data_sources]
        stats_info = [stat.to_llm_dict() for stat in stats]
        relationships_info = [r.to_llm_dict() for r in relationships]

        system_prompt = render_prompt("generate_visual_concepts/system.jinja")
        user_prompt = render_prompt("generate_visual_concepts/user.jinja", {
            "project_details": ensure_json_serializable(project),
            "data_sources": ensure_json_serializable(data_source_info),
            "relationships": ensure_json_serializable(relationships_info),
            "visual_types": [visual_type.value for visual_type in VisualType],
            "number_of_visuals": 4,
            "stats": ensure_json_serializable(stats_info)
        })
        llm_response: VisualConceptsLLMResponse = await ainvoke_llm(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            profile="analyze",
            response_model=VisualConceptsLLMResponse
        )
        visual_concepts: List[VisualConcept] = llm_response.visual_concepts
        return visual_concepts

    except Exception as e:
        error_msg = f"Error generating chart ideas: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=500, detail=f"Error generating chart ideas: {str(e)}")


async def get_visual_data(visual_concept: VisualConcept, data_sources: List[DataSource], relationships: List[Relationship]):
    """Get visual data for a visual concept"""
    try:

        visual_sample_data = await generate_visual_sample_data(
            visual_concept=visual_concept,
            data_sources=data_sources,
            relationships=relationships
        )
        visual_python_code = await generate_visual_python_code(
            data_sources=data_sources,
            relationships=relationships,
            visual_concept=visual_concept,
            visual_sample_data=visual_sample_data
        )

        dataframes = await get_dataframes_dict(data_sources)
        result = execute_pandas_code(
            visual_python_code, dataframes)

        return {
            **visual_concept.model_dump(),
            "python_code": visual_python_code,
            "data": result
        }
    except Exception as e:
        error_msg = f"Error getting visual data: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=500, detail=f"Error getting visual data: {str(e)}")


async def generate_visual_sample_data(visual_concept: VisualConcept, data_sources: List[DataSource], relationships: List[Relationship]):
    """Generate sample data for a visual concept"""
    try:
        # Construct prompt for the LLM
        SERIES_SAMPLES_PATH = Path(
            __file__).parent.parent / "data" / "series_sample.json"
        all_sample_series_output = {}
        with open(SERIES_SAMPLES_PATH) as f:
            all_sample_series_output = json.load(f)
        sample_series_output = all_sample_series_output[visual_concept.type]

        used_data_source_info = [ds.to_llm_dict() for ds in data_sources if str(
            ds.id) in visual_concept.required_dataset_ids]

        relationships_info = [r.to_llm_dict() for r in relationships]

        system_prompt = render_prompt(
            "generate_visual_sample_data/system.jinja")
        user_prompt = render_prompt("generate_visual_sample_data/user.jinja", {
            "datasets": ensure_json_serializable(used_data_source_info),
            "relationships": ensure_json_serializable(relationships_info),
            "visual_concept": ensure_json_serializable(visual_concept.to_llm_dict()),
            "sample_series_output": ensure_json_serializable(sample_series_output)
        })

        llm_response: VisualSampleDataLLMResponse = await ainvoke_llm(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            profile="analyze",
            response_model=VisualSampleDataLLMResponse
        )
        visual_sample_data: VisualData = llm_response.visual_sample_data
        return visual_sample_data

    except Exception as e:
        error_msg = f"Error generating sample data: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=500, detail=f"Error generating sample data: {str(e)}")


async def generate_visual_python_code(data_sources: List[DataSource], relationships: List[Relationship], visual_concept: VisualConcept, visual_sample_data: VisualData | dict[str, VisualData]):
    """Generate Python code for a visual"""
    try:
        # Construct prompt for the LLM
        data_source_info = [ds.to_llm_dict() for ds in data_sources]
        relationships_info = [r.to_llm_dict() for r in relationships]

        system_prompt = render_prompt(
            "generate_visual_python_code/system.jinja")
        user_prompt = render_prompt("generate_visual_python_code/user.jinja", {
            "datasets": ensure_json_serializable(data_source_info),
            "relationships": ensure_json_serializable(relationships_info),
            "visual_concept": ensure_json_serializable(visual_concept.to_llm_dict()),
            "sample_data": ensure_json_serializable(visual_sample_data)
        })

        llm_response: VisualPythonCodeLLMResponse = await ainvoke_llm(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            profile="analyze",
            response_model=VisualPythonCodeLLMResponse
        )
        visual_python_code: str = llm_response.visual_python_code
        return visual_python_code

    except Exception as e:
        error_msg = f"Error generating Python code: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=500, detail=f"Error generating Python code: {str(e)}")


async def generate_visuals(project_id: str, user_id: str = "google-oauth2|105273317112514853668"):
    """Create a new visual for a project"""
    try:
        project = await get_project(project_id, user_id)
        data_sources: List[DataSource] = await get_data_sources(project_id, user_id)
        relationships: List[Relationship] = await get_relationships(project_id, user_id)
        stats: List[ProjectStats] = await get_project_stats(project_id, user_id)

        visual_concepts: List[VisualConcept] = await generate_visual_concepts(
            project=project,
            data_sources=data_sources,
            stats=stats,
            relationships=relationships
        )

        # Generate sample data for all visual concepts in parallel
        tasks = [
            get_visual_data(
                visual_concept=concept,
                data_sources=[
                    data_source for data_source in data_sources if data_source.id in concept.required_dataset_ids],
                relationships=relationships
            ) for concept in visual_concepts
        ]
        visual_data_list = await asyncio.gather(*tasks)
        # Combine visual concepts with their sample data, filtering out any failed generations

        # Save the visuals to the database
        visuals_collection = get_collection("visuals")
        now = datetime.now()
        await visuals_collection.insert_many([{
            **visual_data,
            "project_id": project_id,
            "user_id": user_id,
            "status": "READY",
            "created_at": now
        } for visual_data in visual_data_list])

        # Fetch created visuals
        created_visuals = []
        async for visual in visuals_collection.find({"project_id": project_id, "user_id": user_id}):
            created_visuals.append(Visual(id=str(visual["_id"]), **visual))

        return created_visuals
    except Exception as e:
        error_msg = f"Error generating visual: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=500, detail=f"Error generating visual: {str(e)}")
