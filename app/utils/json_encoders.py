from bson import ObjectId
from datetime import datetime
import math
import numpy as np
import json
from typing import Any, Dict, List, Union

def serialize_mongodb_objects(obj: Any) -> Any:
    """
    Recursively serialize MongoDB objects to JSON-compatible types.
    
    Args:
        obj: The object to serialize
        
    Returns:
        A JSON-serializable version of the object
    """
    if obj is None:
        return None
    elif isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            # Handle None keys
            key = "null_key" if k is None else k
            result[key] = serialize_mongodb_objects(v)
        return result
    elif isinstance(obj, list):
        return [serialize_mongodb_objects(item) for item in obj]
    elif isinstance(obj, float):
        # Handle special float values
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return serialize_mongodb_objects(obj.tolist())
    elif hasattr(obj, '__dict__'):
        return serialize_mongodb_objects(obj.__dict__)
    else:
        return obj

def sanitize_for_json(obj: Any) -> Any:
    """
    Sanitize an object to ensure it can be serialized to JSON.
    Handles special float values like NaN and Infinity.
    
    Args:
        obj: The object to sanitize
        
    Returns:
        A JSON-serializable version of the object
    """
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    else:
        return obj

def make_json_safe(obj: Any) -> Any:
    """
    Aggressively sanitize an object to ensure it can be serialized to JSON.
    Converts any problematic values to strings.
    
    Args:
        obj: The object to sanitize
        
    Returns:
        A guaranteed JSON-serializable version of the object
    """
    if isinstance(obj, dict):
        return {str(k): make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_safe(item) for item in obj]
    else:
        try:
            # Test if the value is JSON serializable
            json.dumps(obj)
            return obj
        except:
            # If not, convert to string
            return str(obj)

def ensure_json_serializable(obj: Any) -> Any:
    """
    Comprehensive function to ensure an object is JSON serializable.
    Applies multiple sanitization steps and validates the result.
    
    Args:
        obj: The object to process
        
    Returns:
        A guaranteed JSON-serializable version of the object
    """
    # First, convert MongoDB objects
    serialized = serialize_mongodb_objects(obj)
    
    # Then sanitize special float values
    sanitized = sanitize_for_json(serialized)
    
    # Validate by attempting to serialize to JSON
    try:
        json_str = json.dumps(sanitized)
        return json.loads(json_str)  # Return the validated object
    except Exception as e:
        print(f"JSON serialization error: {str(e)}")
        # If that fails, use the more aggressive approach
        return make_json_safe(sanitized)

def convert_numpy_types(obj):
    """
    Recursively convert NumPy types to Python native types for JSON serialization.
    
    Args:
        obj: The object to convert
        
    Returns:
        Object with NumPy types converted to Python native types
    """
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return convert_numpy_types(obj.tolist())
    elif isinstance(obj, np.bool_):
        return bool(obj)
    else:
        return obj 