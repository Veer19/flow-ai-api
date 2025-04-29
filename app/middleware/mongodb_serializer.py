from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.utils.json_encoders import serialize_mongodb_objects
import json
import math
import numpy as np

class MongoDBSerializerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Only process JSON responses
        if isinstance(response, JSONResponse):
            # Get the response content
            content = response.body
            
            # If it's already bytes, decode it
            if isinstance(content, bytes):
                try:
                    content = json.loads(content.decode('utf-8'))
                except Exception as e:
                    print(f"Error decoding response: {str(e)}")
                    # If we can't decode it, return the original response
                    return response
            
            # Serialize MongoDB objects in the response
            try:
                serialized_content = serialize_mongodb_objects(content)
                
                # Create a new response with serialized content
                return JSONResponse(
                    content=serialized_content,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                    background=response.background
                )
            except Exception as e:
                print(f"Error serializing response: {str(e)}")
                # If serialization fails, try a more aggressive approach
                try:
                    # Custom JSON encoder for problematic values
                    class SafeJSONEncoder(json.JSONEncoder):
                        def default(self, obj):
                            if isinstance(obj, ObjectId):
                                return str(obj)
                            if isinstance(obj, datetime):
                                return obj.isoformat()
                            if isinstance(obj, float):
                                if math.isnan(obj) or math.isinf(obj):
                                    return None
                            if isinstance(obj, np.integer):
                                return int(obj)
                            if isinstance(obj, np.floating):
                                if np.isnan(obj) or np.isinf(obj):
                                    return None
                                return float(obj)
                            if isinstance(obj, np.ndarray):
                                return obj.tolist()
                            return super().default(obj)
                    
                    # Convert to JSON string and back to ensure it's safe
                    json_str = json.dumps(content, cls=SafeJSONEncoder)
                    safe_content = json.loads(json_str)
                    
                    return JSONResponse(
                        content=safe_content,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type,
                        background=response.background
                    )
                except Exception as fallback_error:
                    print(f"Fallback serialization failed: {str(fallback_error)}")
                    # If all else fails, return a simplified error response
                    return JSONResponse(
                        content={"error": "Response contained values that couldn't be serialized to JSON"},
                        status_code=500
                    )
        
        return response 