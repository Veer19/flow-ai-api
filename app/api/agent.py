from fastapi import APIRouter, HTTPException, Body
from typing import Dict  
import logging
import traceback

from app.config import get_settings
from app.agent import DataAnalysisAgent
from app.utils.json_encoders import ensure_json_serializable
from app.api.projects import get_project_data_sources
import time
from app.services.chat_service import create_chat_thread, get_thread, update_thread_user, get_messages, get_threads, call_agent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
router = APIRouter()

@router.post("/{project_id}")
async def create_agent_thread_endpoint(project_id: str, body: Dict[str, str] = Body(...)):
    """
    Invoke the data analysis agent with a natural language query
    """
    try:
        # Create a new thread in mongo db
        thread = await create_chat_thread(project_id, body['message'])
        return ensure_json_serializable({
            "thread": thread,
            "status": "success"
        })
    except Exception as e:
        logger.error(f"Error creating thread: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error creating thread: {str(e)}")
    
#Get threads for a project
@router.get("/{projectId}/threads")
async def get_threads_endpoint(projectId: str):
    """
    Get all threads for a project
    """
    threads = await get_threads(projectId)
    return ensure_json_serializable(threads)


@router.post("/{projectId}/thread/{threadId}")
async def invoke_agent_endpoint(projectId: str, threadId: str, body: Dict[str, str] = Body(...)):
    """
    Invoke the data analysis agent with a natural language query
    """
    if "message" not in body:
        raise HTTPException(status_code=400, detail="Request body must include 'message' field")
    
    try:
        # Fetch datasets using projectId

        await update_thread_user(threadId, body["message"])
        # Fetch the thread from mongo db
        thread = await get_thread(threadId)

        past_messages = thread["messages"][-10:]
        print("LATEST MESSAGES")
        print(past_messages)
        
        # Update the thread with the new messages
        # Return the ai message
        ai_message, ai_state = await call_agent(projectId, thread['_id'], body["message"], past_messages)
        
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
@router.get("/{projectId}/thread/{threadId}/messages")
async def get_messages_endpoint(projectId: str, threadId: str):
    """
    Get all messages of a thread
    """
    messages = await get_messages(projectId, threadId)
    return ensure_json_serializable(messages)
