from openai import AzureOpenAI
from fastapi import HTTPException
import json
from app.config import get_settings
from typing import Dict, Any
import os
from pathlib import Path

settings = get_settings()

# Load series samples
SERIES_SAMPLES_PATH = Path(__file__).parent.parent / "data" / "series_sample.json"
with open(SERIES_SAMPLES_PATH) as f:
    SERIES_SAMPLES = json.load(f)

async def query_azure_openai(prompt: str, response_type = 'json', temperature = 0.3) -> str:
    """Send a prompt to Azure OpenAI using the official SDK."""
    try:
        client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_KEY,
            api_version="2024-08-01-preview",
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
        
        # Set up the response format correctly based on the response_type
        if response_type == 'json':
            response_format = {
                "type": "json_object"  # Changed from json_schema to json_object
            }
        else:
            response_format = None  # No specific format for text responses
        
        response = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": """
                    You are a helpful assistant that provides accurate, detailed responses.""" + 
                    """
                    - The assistant MUST NOT wrap the JSON in markdown code fences.
                    - The assistant MUST NOT add any text before or after the JSON array.
                    """ if response_type == 'json' else ""},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,  # Lower temperature for more consistent output
        )
        
        content = response.choices[0].message.content
        if response_type == 'json':
            try:
                return json.loads(content)  # Validate JSON
            except json.JSONDecodeError:
                return []  # Return empty array on JSON parse error
        else:
            return content
    except json.JSONDecodeError:
        return "[]"
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Azure OpenAI API error: {str(e)}"
        )

async def generate_chart_suggestions(prompt: str) -> str:
    """Generate chart suggestions using Azure OpenAI."""
    try:
        client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_KEY,
            api_version="2024-02-15-preview",
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
        
        response = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {
                    "role": "system", 
                    "content": """You are a data visualization expert. 
                        Analyze data and suggest insightful charts from a library of charts given in the following link - https://apexcharts.com/react-chart-demos/ 
                        Focus on creating visualizations that reveal patterns and insights in the data.

                        IMPORTANT:
                        Only return a valid JSON array of chart configurations in the exact following format:
                        [
                            {
                                "chart_type": "type of chart from the library",
                                "title": "meaningful chart title",
                                "description": "detailed description of the chart",
                                "columns_involved": "List of columns to be used along with which file they are from"
                            }
                        ]
                        Example - 
                        [
                            {
                                "chart_type": "bar",
                                "title": "Total Quantity of Products Sold by Product Segment",
                                "description": "detailed description of the chart",
                                "columns_involved": ["sales.quantity", "sales.product_segment"]
                            }
                        ]
                    """
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        content = response.choices[0].message.content
        print("--------------------------------")
        print(content)
        json.loads(content)  # Validate JSON
        return content
        
    except json.JSONDecodeError:
        return "[]"
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Azure OpenAI API error: {str(e)}"
        ) 
    
async def generate_python_code(prompt: str) -> str:
    """Generate Python code using Azure OpenAI."""
    try:
        client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_KEY,
            api_version="2024-02-15-preview",
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
        
        # Format series samples for better LLM understanding
        formatted_samples = "ApexCharts Series Format Examples:\n\n"
        for chart_type, sample in SERIES_SAMPLES.items():
            formatted_samples += f"{chart_type.title()} Chart:\n"
            formatted_samples += f"chart_data = {json.dumps(sample, indent=2)}\n\n"
        system_prompt = f"""You are a Python code generation expert specializing in data analysis with pandas.
            Given a chart description, generate the necessary pandas code to process the data.
            
            Rules:
            1. Return ONLY a valid JSON array of strings, where each string is a minified line of Python code
            2. Use pandas and common Python libraries only
            3. Handle potential missing or invalid data
            4. MUST create a variable named 'chart_data' with the processed data
            5. Use clear variable names that match the context
            6. 
            
            The code should prepare 'chart_data' in an ApexCharts-compatible format.
            {formatted_samples}

            IMPORTANT:
            1. The final code MUST assign the result to a variable named 'chart_data'
            2. Format must exactly match the examples above for the specified chart type
            """
        response = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0,  # Set to 0 for more consistent formatting
            max_tokens=1000
        )
        
        content = response.choices[0].message.content
        print("--------------------------------")
        print(content)
        # Validate JSON format
        json.loads(content)
        return content
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Azure OpenAI API error: {str(e)}"
        )

async def generate_chart_options(data_context: str, chart_config: Dict[str, Any]) -> Dict[str, Any]:
    """Generate ApexCharts options based on chart type and configuration."""
    try:
        prompt = f"""
        {data_context}
        Generate ApexCharts options for a {chart_config['chart_type']} chart.
        Title: {chart_config['title']}
        Description: {chart_config['description']}
        Columns involved: {chart_config['columns_involved']}
        
        Return only a valid JSON object with ApexCharts options.
        Focus on readability and best practices for this chart type.
        Use the unqiue values of the columns involved to determine the categories for the chart if needed.
        """
        
        client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_KEY,
            api_version="2024-02-15-preview",
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
        
        response = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {
                    "role": "system", 
                    "content": """You are an ApexCharts configuration expert.
                        Generate chart options following ApexCharts format (https://apexcharts.com/docs/options/).
                        
                        IMPORTANT:
                        1. Return only a valid JSON object
                        2. Include essential options like:
                           - chart: { type, height, toolbar }
                           - title: { text, align }
                           - xaxis: { type, categories }
                           - yaxis: { title }
                           - colors, theme, tooltip
                        3. Use readable formatting
                        4. Set sensible defaults
                        5. Include animations
                        6. Add responsive breakpoints
                        
                        Example for bar chart:
                        {
                            "chart": {
                                "type": "bar",
                                "height": 350,
                                "toolbar": { "show": true }
                            },
                            "title": {
                                "text": "Sales Analysis",
                                "align": "center"
                            },
                            "xaxis": {
                                "title": { "text": "Categories" }
                            },
                            "yaxis": {
                                "title": { "text": "Values" }
                            },
                            "theme": { "mode": "light" }
                        }
                    """
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=1000
        )
        
        options = json.loads(response.choices[0].message.content)
        return options
        
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid chart options generated: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating chart options: {str(e)}"
        )