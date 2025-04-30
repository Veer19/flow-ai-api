import logging
from typing import List, Dict, Any
import json
from datetime import datetime
from app.utils.json_encoders import ensure_json_serializable
from app.services.mongodb import get_collection
from app.services.azure_ai import query_azure_openai
from bson.objectid import ObjectId
from app.prompts.generate_chart_ideas import get_generate_chart_ideas_prompt
from app.prompts.generate_chart_sample_data import get_generate_chart_sample_data_prompt
from app.prompts.generate_chart_data_code import get_generate_chart_code_prompt
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fetch_project_data(project_id: str) -> Dict[str, Any]:
    try:
        # Get collections
        projects_collection = get_collection("projects")
        
        # Get project details
        project = await projects_collection.find_one({"_id": ObjectId(project_id)})
        if not project:
            logger.error(f"Project with ID {project_id} not found")
            return None
        
        return project
        
    except Exception as e:
        logger.error(f"Error fetching project data: {str(e)}")
        return None


async def fetch_project_data_sources(project_id: str) -> Dict[str, Any]:
    try:
        # Get collections
        data_sources_collection = get_collection("dataSources")
            
        # Get data sources - use the collection object, not a dictionary
        data_sources_cursor = data_sources_collection.find({"projectId": project_id})
        data_sources = await data_sources_cursor.to_list(None)
        return data_sources
        
    except Exception as e:
        logger.error(f"Error fetching project data: {str(e)}")
        return None
    
async def fetch_project_relationships(project_id: str) -> Dict[str, Any]:
    try:
        # Get collections
        relationships_collection = get_collection("relationships")
        
        # Get relationships
        relationship = await relationships_collection.find_one(
            {"projectId": project_id},
            sort=[("createdAt", -1)]  # Get the most recent
        )
        
        return relationship.get("relationships", []) if relationship else []
        
    except Exception as e:
        logger.error(f"Error fetching project data: {str(e)}")
        return None

async def generate_chart_concepts(project_id: str):
    """
    Generate chart recommendations for a project based on its data sources and relationships,
    including ApexCharts configuration code for each chart.
    
    Args:
        project_id: The ID of the project
        
    Returns:
        Dictionary with chart recommendations and their ApexCharts configurations
    """
    try:
        # Fetch project data
        project = await fetch_project_data(project_id)
        if not project:
            error_msg = f"Could not fetch data for project {project_id}"
            logger.error(error_msg)
            return {"error": error_msg, "success": False}
        
        data_sources = await fetch_project_data_sources(project_id)
        relationships = await fetch_project_relationships(project_id)
        if not data_sources:
            error_msg = f"No data sources found for project {project_id}"
            logger.warning(error_msg)
            return {"error": error_msg, "success": False}
            
        # Prepare data source information for the LLM
        data_source_info = []
        for ds in data_sources:
            source_info = {
                "filename": ds.get("filename"),
                "columns": [col.get("name") for col in ds.get("columnMetadata", [])],
                "column_types": {col.get("name"): col.get("type") for col in ds.get("columnMetadata", [])},
                "sample_data": ds.get("sampleData", [])[:2],  # Just a couple of rows for context
                "stats": ds.get("stats", {})
            }
            data_source_info.append(source_info)
        
        # Construct prompt for the LLM
        prompt = get_generate_chart_ideas_prompt(
            json.dumps(ensure_json_serializable({
                "project": project, 
                "dataSources": data_sources, 
                "relationships": relationships
            }), 
            separators=(',', ':'), 
            ensure_ascii=False)
        )
        # Call the LLM to generate chart recommendations
        llm_response = await query_azure_openai(prompt, temperature=0.8)
        
        # Parse the LLM response to extract the JSON
        try:
            # Find JSON in the response string
            charts = llm_response
            
                
            # If the response is a dict with a charts key, extract that
            if isinstance(charts, dict) and "charts" in charts:
                charts = charts["charts"]
           
            # Ensure we have a list
            if not isinstance(charts, list):
                error_msg = "LLM response did not contain a valid chart list"
                logger.error(error_msg)
                return {"error": error_msg, "success": False, "raw_response": llm_response}
                
            # Add timestamp and ID to each chart
            for chart in charts:
                chart["generatedAt"] = datetime.now().isoformat()
                chart["projectId"] = project_id
            
            # Limit to at most 4 charts
            charts = charts[:4]
            return {
                "success": True, 
                "charts": charts,
            }
        except Exception as e:
            error_msg = f"Error parsing LLM response: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Raw response: {llm_response}")
            return {"error": error_msg, "success": False, "raw_response": llm_response}
            
    except Exception as e:
        error_msg = f"Error generating chart ideas: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg, "success": False}

async def generate_chart(chart: Dict[str, Any]):
    """
    Generate chart recommendations for a project based on its data sources and relationships,
    including ApexCharts configuration code for each chart.
    
    Args:
        project_id: The ID of the project
        
    Returns:
        Dictionary with chart recommendations and their ApexCharts configurations
    """
    try:
        # Fetch project data
        project_id = chart["projectId"]
        data_sources = await fetch_project_data_sources(project_id)
        relationships = await fetch_project_relationships(project_id)
        if not data_sources:
            error_msg = f"No data sources found for project {project_id}"
            logger.warning(error_msg)
            return {"error": error_msg, "success": False}
        logger.info(f"Generating ApexCharts configuration for chart: {chart.get('title')}")
        chart_config = await generate_chart_sample_data(chart, data_sources)
        print("chart_config", chart_config)
        
        if chart_config:
            # Merge chart description with chart configuration
            series, options = await generate_chart_real_data(project_id, chart, chart_config.get("series"), chart_config.get("options"))
            enhanced_chart = {
                **chart,  # Original chart description
                "options": options,
                "series": series,
                "configGeneratedAt": chart_config.get("generatedAt"),
                "status": "generated"
            }
            return enhanced_chart
        else:
            # If chart config generation failed, include the original chart with error info
            chart["configError"] = chart_config.get("error")
            chart["configSuccess"] = False
            return None

    except Exception as e:
        error_msg = f"Error generating charts: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg, "success": False}

async def generate_chart_sample_data(chart_description: Dict[str, Any], data_sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate ApexCharts configuration code for a specific chart description
    
    Args:
        project_id: The ID of the project
        chart_description: The chart description object with type, title, etc.
        
    Returns:
        Dictionary with 'options' and 'series' keys for ApexCharts, or error information
    """
    try:
        
        # Find the specific data sources needed for this chart
        chart_data_sources = []
        if isinstance(chart_description.get("dataSource"), list):
            source_filenames = chart_description["dataSource"]
            for ds in data_sources:
                if ds.get("filename") in source_filenames:
                    chart_data_sources.append(ds)
        else:
            # Handle case where dataSource might be a single string
            source_filename = chart_description.get("dataSource")
            if source_filename:
                for ds in data_sources:
                    if ds.get("filename") == source_filename:
                        chart_data_sources.append(ds)
        
        if not chart_data_sources:
            error_msg = f"Could not find specified data sources for chart: {chart_description.get('title')}"
            logger.error(error_msg)
            return {"error": error_msg, "success": False}
        
        # Prepare data for the LLM
        chart_info = {
            "chartType": chart_description.get("chartType"),
            "title": chart_description.get("title"),
            "description": chart_description.get("description"),
            "columns": chart_description.get("columns", []),
            "transformations": chart_description.get("transformations", "")
        }
        
        # Prepare sample data from the data sources
        data_samples = []
        for ds in chart_data_sources:
            sample = {
                "filename": ds.get("filename"),
                "columns": [col.get("name") for col in ds.get("columnMetadata", [])],
                "column_types": {col.get("name"): col.get("type") for col in ds.get("columnMetadata", [])},
                "sample_data": ds.get("sampleData", [])[:5],  # Include more sample rows for better code generation
                "stats": ds.get("stats", {})
            }
            data_samples.append(sample)
        
        # Construct prompt for the LLM
        prompt = get_generate_chart_sample_data_prompt(
            json.dumps(ensure_json_serializable(chart_info), 
            separators=(',', ':'), 
            ensure_ascii=False),
            json.dumps(ensure_json_serializable(data_samples), 
            separators=(',', ':'), 
            ensure_ascii=False)
        )
        
        chart_config = await query_azure_openai(prompt)
        
        try:
            # Validate that the response has the required keys
            if not isinstance(chart_config, dict) or 'options' not in chart_config or 'series' not in chart_config:
                error_msg = "LLM response did not contain valid 'options' and 'series' keys"
                logger.error(error_msg)
                return {"error": error_msg, "success": False, "raw_response": chart_config}
            
            # Add metadata
            chart_config["generatedAt"] = datetime.now().isoformat()
            
            return chart_config
            
        except Exception as e:
            error_msg = f"Error parsing chart configuration: {str(e)}"
            logger.error(error_msg)
            return None
            
    except Exception as e:
        error_msg = f"Error generating chart code: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg, "success": False}

async def generate_chart_real_data(project_id: str, chart_info: Dict[str, Any], sample_series: List[Dict[str, Any]], sample_options: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generate real data for a chart based on the provided series configuration
    
    Args:
        project_id: The ID of the project
        chart_info: The chart description object with type, title, etc.
        sample_series: The sample series data generated by the LLM
        sample_options: The sample options data generated by the LLM
        
    Returns:
        Updated series data based on the full dataset
    """
    # try:
        # Fetch project data
    data_sources = await fetch_project_data_sources(project_id)
    
    
    
    # Find the specific data sources needed for this chart
    chart_data_sources = []
    if isinstance(chart_info.get("dataSource"), list):
        source_filenames = chart_info["dataSource"]
        for ds in data_sources:
            if ds.get("filename") in source_filenames:
                chart_data_sources.append(ds)
    else:
        # Handle case where dataSource might be a single string
        source_filename = chart_info.get("dataSource")
        if source_filename:
            for ds in data_sources:
                if ds.get("filename") == source_filename:
                    chart_data_sources.append(ds)
    
    if not chart_data_sources:
        logger.error(f"Could not find specified data sources for chart: {chart_info.get('title')}")
        return sample_series, sample_options  # Return sample data if we can't find the data sources
    
    # Import necessary libraries for data processing
    import pandas as pd
    import io
    from app.utils.blob_storage import download_from_blob_storage
    
    # Download and load data from blob storage
    dataframes = {}
    for ds in chart_data_sources:
        try:
            # Get blob path
            blob_path = ds.get("blobPath")
            if not blob_path:
                logger.warning(f"No blob path found for data source: {ds.get('filename')}")
                continue
            
            # Download blob content
            blob_content = await download_from_blob_storage(blob_path)
            if not blob_content:
                logger.warning(f"Could not download blob for data source: {ds.get('filename')}")
                continue
            
            # Convert to DataFrame - try different encodings
            try:
                # First try UTF-8
                df = pd.read_csv(io.BytesIO(blob_content))
                dataframes[ds.get("filename")] = df
                logger.info(f"Successfully loaded data for {ds.get('filename')} with {len(df)} rows")
            except UnicodeDecodeError:
                try:
                    # If UTF-8 fails, try Latin-1 (a more permissive encoding)
                    df = pd.read_csv(io.BytesIO(blob_content), encoding='latin1')
                    dataframes[ds.get("filename")] = df
                    logger.info(f"Successfully loaded data for {ds.get('filename')} with {len(df)} rows using latin1 encoding")
                except Exception as encoding_error:
                    try:
                        # If Latin-1 fails, try with error handling
                        df = pd.read_csv(io.BytesIO(blob_content), encoding='utf-8', errors='replace')
                        dataframes[ds.get("filename")] = df
                        logger.info(f"Successfully loaded data for {ds.get('filename')} with {len(df)} rows using error replacement")
                    except Exception as replace_error:
                        logger.error(f"Failed to read {ds.get('filename')} with multiple encodings: {str(replace_error)}")
                        continue
            
        except Exception as e:
            logger.error(f"Error loading data for {ds.get('filename')}: {str(e)}")
            continue
    
    if not dataframes:
        logger.error("Could not load any data from blob storage")
        return sample_series, sample_options  # Return sample data if we couldn't load any real data
        
    available_dataframes = ", ".join([f"df_{i} (filename: {name})" for i, name in enumerate(dataframes.keys())])
    print(f"Available dataframes: {available_dataframes}")
    # Filter data_info based on the available dataframes
    data_sources = [ds for ds in data_sources if ds.get("filename") in dataframes.keys()]
    print(f"Filtered data_info: {data_sources}")
    # Prepare the prompt for the LLM to generate data processing code
    prompt = get_generate_chart_code_prompt(
        json.dumps(ensure_json_serializable(chart_info), 
        separators=(',', ':'), 
        ensure_ascii=False),
        json.dumps(ensure_json_serializable(data_sources), 
        separators=(',', ':'), 
        ensure_ascii=False),
        json.dumps(ensure_json_serializable({"series": sample_series, "options": sample_options}), 
        separators=(',', ':'), 
        ensure_ascii=False),
    )
    # Call the LLM to generate data processing code
    llm_response = await query_azure_openai(prompt, response_type='text')
    
    # Extract the Python code from the response
    code = llm_response
    
    
    namespace = {}
    exec(code, {}, namespace)   # second arg {} keeps globals clean
    build_chart = namespace["build_chart"]
    chart_data = build_chart(dataframes)        
    return chart_data['series'], chart_data['options']
        
            
    # except Exception as e:
    #     logger.error(f"Error generating real chart data: {str(e)}")
    #     return None, None  # Return sample data on error


