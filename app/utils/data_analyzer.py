import logging
import pandas as pd
import numpy as np
import json
import ast
import traceback
from io import StringIO
import contextlib
import sys
from typing import Dict, List, Any
from datetime import datetime

from app.services.azure_ai import query_azure_openai
from app.utils.json_encoders import convert_numpy_types

# Set up logging
logger = logging.getLogger(__name__)

async def analyze_csv_data(df: pd.DataFrame, column_names: List[str]) -> Dict[str, Any]:
    """
    Analyze CSV data to detect quality issues and generate statistics.
    Uses LLM to generate Python code for intelligent column-specific analysis.
    
    Args:
        df: Pandas DataFrame containing the CSV data
        column_names: List of column names
        
    Returns:
        Dictionary containing statistics and problem columns
    """
    logger.info(f"Analyzing CSV data quality for DataFrame with {len(df)} rows")
    
    # Calculate basic statistics that don't require column-specific analysis
    null_values = df.isna().sum().sum()
    null_percentage = round((null_values / (len(df) * len(df.columns))) * 100, 2) if len(df) * len(df.columns) > 0 else 0
    duplicate_rows = df.duplicated().sum()
    
    logger.info(f"Basic stats: {null_values} null values ({null_percentage}%), {duplicate_rows} duplicate rows")
    
    # Prepare column information for LLM
    column_info = []
    for col in column_names:
        logger.info(f"Analyzing column: {col}")
        # Get basic info about each column
        dtype = str(df[col].dtype)
        null_count = df[col].isna().sum()
        null_pct = round((null_count / len(df)) * 100, 2) if len(df) > 0 else 0
        
        # Get sample values (non-null)
        sample_values = df[col].dropna().head(5).tolist()
        logger.info(f"Sample values: {sample_values}")
        
        # Convert NumPy types to Python native types for JSON serialization
        sample_values = convert_numpy_types(sample_values)
        
        # Add to column info
        column_info.append({
            "name": col,
            "dtype": dtype,
            "null_count": int(null_count),  # Convert to Python int
            "null_percentage": float(null_pct),  # Convert to Python float
            "sample_values": sample_values
        })
    
    # Construct prompt for the LLM to generate Python code
    prompt = f"""
    I have a CSV dataset with {len(df)} rows and {len(column_names)} columns. 
    I need to analyze the data quality and identify potential issues.
    
    Here's information about each column:
    
    {json.dumps(column_info, indent=2)}
    
    For each column, please:
    1. Determine the semantic type (e.g., date, currency, product ID, name, address, etc.)
    2. Generate Python code that performs appropriate data quality checks based on the column's semantic type
    
    The Python code should:
    - Take a pandas DataFrame 'df' and column name as input
    - Return a dictionary with 'issues' (list of strings describing problems), 'semantic_type' (string), and 'suggestion' (string with advice)
    - Handle errors gracefully (no exceptions should be raised)
    - Use pandas, numpy, and standard library functions only
    
    Format your response as a JSON object with a "column_analyses" array containing objects with:
    - column_name: The name of the column
    - semantic_type: The inferred semantic type
    - analysis_code: Python function that performs the analysis (as a string)
    """ + """
    Example of analysis_code for a date column:
    ```python
    def analyze_date_column(df, column_name):
        issues = []
        try:
            # Check for null values
            null_count = df[column_name].isna().sum()
            if null_count > 0:
                issues.append(f"{null_count} null values")
            
            # Try to convert to datetime
            converted_dates = pd.to_datetime(df[column_name], errors='coerce')
            invalid_dates = sum(converted_dates.isna() & ~df[column_name].isna())
            if invalid_dates > 0:
                issues.append(f"{invalid_dates} invalid date formats")
            
            # Check for future dates
            if not converted_dates.isna().all():
                future_dates = sum(converted_dates > pd.Timestamp.now())
                if future_dates > 0:
                    issues.append(f"{future_dates} future dates")
            
            return {
                'issues': issues,
                'semantic_type': 'date',
                'suggestion': 'Fix invalid date formats and verify future dates are intentional'
            }
        except Exception as e:
            return {
                'issues': [f"Error analyzing column: {str(e)}"],
                'semantic_type': 'date',
                'suggestion': 'Review date values manually'
            }
    ```
    """
    
    try:
        # Call the LLM to get analysis code
        logger.info("Calling LLM for Python code generation")
        llm_response = await query_azure_openai(prompt)
        logger.info(f"LLM response: {llm_response}")
        
        # Parse the LLM response
        try:
            # Check if the response is already a dictionary
            if isinstance(llm_response, dict):
                analysis_suggestions = llm_response
            else:
                # Find JSON in the response string
                json_start = llm_response.find('{')
                json_end = llm_response.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = llm_response[json_start:json_end]
                    analysis_suggestions = json.loads(json_str)
                else:
                    # If no JSON found, try to parse the whole response
                    analysis_suggestions = json.loads(llm_response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON, falling back to standard analysis")
            # Fall back to empty suggestions if parsing fails
            analysis_suggestions = {"column_analyses": []}
        
        # Initialize problem columns list
        problem_columns = []
        
        # Define a safe execution environment for running the generated code
        def safe_exec(code_str, df, column_name):
            """Safely execute the generated Python code with limited scope"""
            # Create a copy of the dataframe to prevent modifications
            df_copy = df.copy()
            
            # Create a restricted globals dictionary with only necessary modules
            restricted_globals = {
                'pd': pd,
                'np': np,
                'math': math,
                'df': df_copy,
                'column_name': column_name,
                'datetime': datetime,
                'sum': sum,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'list': list,
                'dict': dict,
                'round': round,
                'min': min,
                'max': max,
                'abs': abs,
                'all': all,
                'any': any,
                'enumerate': enumerate,
                'zip': zip,
                'range': range,
                'print': print,
                '__builtins__': {}  # Restrict built-ins
            }
            
            # Capture stdout to prevent print statements from affecting output
            stdout_capture = StringIO()
            
            try:
                # Parse the code to check for potentially harmful operations
                parsed_code = ast.parse(code_str)
                
                # Execute the code with restricted globals
                with contextlib.redirect_stdout(stdout_capture):
                    exec(code_str, restricted_globals)
                
                # Find the function name by looking for function definitions in the AST
                function_name = None
                for node in parsed_code.body:
                    if isinstance(node, ast.FunctionDef):
                        function_name = node.name
                        break
                
                if function_name and function_name in restricted_globals:
                    # Call the function with our parameters
                    result = restricted_globals[function_name](df_copy, column_name)
                    return result
                else:
                    # If no function was defined or found, return a default result
                    return {
                        'issues': ['No analysis function found in generated code'],
                        'semantic_type': 'unknown',
                        'suggestion': 'Manual review required'
                    }
                
            except SyntaxError as e:
                logger.error(f"Syntax error in generated code: {str(e)}")
                return {
                    'issues': [f'Syntax error in analysis code: {str(e)}'],
                    'semantic_type': 'unknown',
                    'suggestion': 'Manual review required'
                }
            except Exception as e:
                logger.error(f"Error executing generated code: {str(e)}")
                return {
                    'issues': [f'Error in analysis: {str(e)}'],
                    'semantic_type': 'unknown',
                    'suggestion': 'Manual review required'
                }
        
        # Apply the generated code to each column
        for column_analysis in analysis_suggestions.get("column_analyses", []):
            col_name = column_analysis.get("column_name")
            semantic_type = column_analysis.get("semantic_type", "unknown")
            analysis_code = column_analysis.get("analysis_code", "")
            
            # Skip if column doesn't exist in the dataframe
            if col_name not in df.columns:
                continue
            
            logger.info(f"Running generated analysis code for column: {col_name} (type: {semantic_type})")
            
            # Extract the function from the code if it's wrapped in ```python ... ```
            if "```python" in analysis_code:
                start_idx = analysis_code.find("```python") + len("```python")
                end_idx = analysis_code.rfind("```")
                if end_idx > start_idx:
                    analysis_code = analysis_code[start_idx:end_idx].strip()
            
            # Execute the analysis code
            result = safe_exec(analysis_code, df, col_name)
            
            # Add to problem columns if issues were found
            if result and result.get('issues'):
                problem_columns.append({
                    "name": col_name,
                    "semantic_type": result.get('semantic_type', semantic_type),
                    "issues": result.get('issues', []),
                    "suggestion": result.get('suggestion', 'Review data quality')
                })
        
        # If LLM analysis didn't find problems, fall back to basic analysis
        if not problem_columns:
            logger.info("LLM analysis didn't find problems, running basic analysis")
            # Run basic analysis for common issues
            for col in column_names:
                issues = []
                
                # Check for null values
                null_count = df[col].isna().sum()
                if null_count > 0:
                    issues.append(f"{null_count} null values")
                
                # Basic type checks
                if df[col].dtype == 'object':
                    # Try to convert to numeric
                    try:
                        pd.to_numeric(df[col], errors='raise')
                    except:
                        # Try to convert to datetime
                        try:
                            pd.to_datetime(df[col], errors='raise')
                        except:
                            # Check for mixed types
                            if len(df[col].dropna()) > 0:
                                types = df[col].dropna().apply(type).nunique()
                                if types > 1:
                                    issues.append(f"Mixed types detected")
                
                # Add column to problem columns if issues found
                if issues:
                    problem_columns.append({
                        "name": col,
                        "semantic_type": "unknown",
                        "issues": issues,
                        "suggestion": "Review data quality"
                    })
    
    except Exception as e:
        logger.error(f"Error in LLM-based analysis: {str(e)}")
        logger.error(traceback.format_exc())
        # Fall back to basic analysis if LLM fails
        logger.info("Falling back to basic analysis")
        
        # Detect mismatched types (try to convert and count failures)
        mismatched_types = 0
        for col in df.columns:
            if df[col].dtype == 'object':
                # Try to convert to numeric
                try:
                    pd.to_numeric(df[col], errors='raise')
                except:
                    # Try to convert to datetime
                    try:
                        pd.to_datetime(df[col], errors='raise')
                    except:
                        # Count potential mismatches within the column
                        if len(df[col].dropna()) > 0:
                            # Check for mixed types in the column
                            types = df[col].dropna().apply(type).nunique()
                            if types > 1:
                                mismatched_types += df[col].count()
        
        # Detect outliers using IQR method for numeric columns
        outliers = 0
        for col in df.select_dtypes(include=['number']).columns:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            outlier_count = ((df[col] < (Q1 - 1.5 * IQR)) | (df[col] > (Q3 + 1.5 * IQR))).sum()
            outliers += outlier_count
        
        # Calculate completeness
        completeness = round(100 - null_percentage, 2)
        
        # Identify problem columns with basic checks
        problem_columns = []
        for col in df.columns:
            issues = []
            
            # Check for null values
            null_count = df[col].isna().sum()
            if null_count > 0:
                issues.append(f"{null_count} null values")
            
            # Check for type issues in date columns
            if 'date' in col.lower() or 'time' in col.lower():
                try:
                    pd.to_datetime(df[col], errors='raise')
                except:
                    invalid_dates = sum(~pd.to_datetime(df[col], errors='coerce').notna())
                    if invalid_dates > 0:
                        issues.append(f"{invalid_dates} invalid date formats")
            
            # Check for negative values in quantity/amount columns
            if any(keyword in col.lower() for keyword in ['quantity', 'amount', 'price', 'cost', 'value']):
                if pd.api.types.is_numeric_dtype(df[col]):
                    neg_count = (df[col] < 0).sum()
                    if neg_count > 0:
                        issues.append(f"{neg_count} negative values")
            
            # Add column to problem columns if issues found
            if issues:
                # Generate suggestion based on issues
                suggestion = ""
                if "null values" in issues[0]:
                    suggestion = "Consider imputing missing values or filtering rows"
                elif "invalid date formats" in ' '.join(issues):
                    suggestion = "Fix date formats or replace with valid dates"
                elif "negative values" in ' '.join(issues):
                    suggestion = "Verify negative values are appropriate for this column"
                
                problem_columns.append({
                    "name": col,
                    "issues": issues,
                    "suggestion": suggestion
                })
    
    # Create stats object with all the calculated metrics and ensure all values are JSON serializable
    stats = {
        "nullValues": int(null_values),
        "nullPercentage": float(null_percentage),
        "duplicateRows": int(duplicate_rows),
        "mismatchedTypes": int(mismatched_types) if 'mismatched_types' in locals() else 0,
        "outliers": int(outliers) if 'outliers' in locals() else 0,
        "completeness": float(completeness) if 'completeness' in locals() else (100 - null_percentage),
        "problemColumns": convert_numpy_types(problem_columns),
        "llmAnalysisApplied": 'analysis_suggestions' in locals() and len(analysis_suggestions.get("column_analyses", [])) > 0
    }
    
    return stats 