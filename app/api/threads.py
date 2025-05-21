from fastapi import APIRouter, HTTPException, Body
from typing import Dict  
import logging
import traceback

from app.config import get_settings
from app.utils.json_encoders import ensure_json_serializable
from app.services.threads import create_chat_thread_with_message, get_thread, get_messages, get_threads, call_agent, create_user_message
from app.api.auth import verify_jwt_token
from fastapi import Depends
from typing import List
from app.models.chat import Message
from app.services.data_sources import get_data_sources
from app.models.data_sources import DataSource


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
router = APIRouter()

@router.post("")
async def create_thread_endpoint(project_id: str, body: Dict[str, str] = Body(...), user: dict = Depends(verify_jwt_token)):
    """
    Invoke the data analysis agent with a natural language query
    """
    try:
        # Create a new thread in mongo db
        thread = await create_chat_thread_with_message(project_id, user.get("sub"), body['message'])
        return ensure_json_serializable(thread)
    except Exception as e:
        logger.error(f"Error creating thread: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error creating thread: {str(e)}")
    
#Get threads for a project
@router.get("")
async def get_threads_endpoint(project_id: str, user: dict = Depends(verify_jwt_token)):
    """
    Get all threads for a project
    """
    threads = await get_threads(project_id, user.get("sub"))
    return ensure_json_serializable(threads)

@router.get("/{thread_id}")
async def get_thread_endpoint(thread_id: str, user: dict = Depends(verify_jwt_token)):
    """
    Get a thread for a project
    """
    thread = await get_thread(thread_id, user.get("sub"))
    return ensure_json_serializable(thread)

@router.get("/{thread_id}/messages")
async def get_thread_messages_endpoint(thread_id: str, user: dict = Depends(verify_jwt_token)):
    """
    Get messages of a thread
    """
    messages = await get_messages(thread_id, user.get("sub"))
    return ensure_json_serializable(messages)


@router.post("/{thread_id}")
async def invoke_thread_agent_endpoint(project_id: str, thread_id: str, body: Dict[str, str] = Body(...), user: dict = Depends(verify_jwt_token)):
    """
    Invoke the data analysis agent with a natural language query
    """
    if "message" not in body:
        raise HTTPException(status_code=400, detail="Request body must include 'message' field")
    
    try:
        # Fetch datasets using projectId
        await create_user_message(project_id, thread_id, user.get("sub"), body["message"])
        # Fetch the thread from mongo db
        messages:List[Message] = await get_messages(thread_id, user.get("sub"))
        past_messages = messages

        datasets: List[DataSource] = await get_data_sources(project_id, user.get("sub"))
        
        ai_message, ai_state = await call_agent(project_id, thread_id, user.get("sub"), body["message"], past_messages, datasets)
        
        return ensure_json_serializable({
            "message": ai_message,
            "status": "success"
        })
    except Exception as e:
        logger.error(f"Agent error: {str(e)}")
        logger.error(traceback.format_exc())
        # Add error status to last message of the thread
        raise HTTPException(status_code=500, detail=f"Agent processing error: {str(e)}")
    

# Create an enpoint to get messages of a thread using this route - 
# `${API_BASE_URL}/chat/${projectId}/thread/${threadId}/messages`
@router.get("/{thread_id}/messages")
async def get_messages_endpoint(project_id: str, thread_id: str, user: dict = Depends(verify_jwt_token)):
    """
    Get all messages of a thread
    """
    messages = await get_messages(project_id, thread_id)
    return ensure_json_serializable(messages)
