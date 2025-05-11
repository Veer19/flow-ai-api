from app.services.mongodb import get_collection
from fastapi import HTTPException
from datetime import datetime, timezone
from app.models.chat import Thread, Message, ThreadListItem
import uuid
import logging
from bson.objectid import ObjectId
from typing import List
from app.agent import DataAnalysisAgent
from app.api.projects import get_project_data_sources
import traceback
import json
logger = logging.getLogger(__name__)

async def get_threads(project_id: str):
    try:
        threads_collection = get_collection("threads")
        cursor = threads_collection.find(
            {"project_id": project_id},
            {"thread_id": 1, "status": 1, "createdAt": 1, "lastUpdatedAt": 1}
        )
        result: List[ThreadListItem] = await cursor.to_list(length=100)
        return result
    except Exception as e:
        logger.error(f"Failed to get threads: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get threads")

async def get_thread(thread_id: str):
    try:
        threads_collection = get_collection("threads")
        result: Thread = await threads_collection.find_one({"thread_id": thread_id})
        return result
    except Exception as e:
        logger.error(f"Failed to get thread: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get thread")
    
async def create_chat_thread(project_id: str, first_message: str):
    try:
        threads_collection = get_collection("threads")

        thread_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        thread_data = Thread(
            thread_id=thread_id,
            project_id=project_id,
            status="OPEN",
            messages=[Message(role="user", content=first_message, timestamp=now, attachments=[], feedback=None, metrics=None)],
            createdAt=now,
            lastUpdatedAt=now
        )

        result = await threads_collection.insert_one(thread_data.model_dump(by_alias=True))
        
        return {
            **thread_data.model_dump(by_alias=True),
            "_id": str(result.inserted_id)
        }

    except Exception as e:
        logger.error(f"Failed to create chat thread: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create chat thread")

async def update_thread_ai(_id: str, ai_result: dict):
    """
    Append an AI response message to an existing thread in MongoDB.
    """
    print("UPDATE THREAD AI")
    print(_id)
    try:
        threads_collection = get_collection("threads")
        now = datetime.now(timezone.utc)
        attachments = []
        # Save ai_result to json
        
        attach = ai_result.get("attach")
        if attach:
            attach_data = ai_result.get("data")
            if(type(attach_data) == dict):
                for key, value in attach_data.items():
                    attachments.append({
                        "type": attach,
                        "attachment": value
                    })
            else:
                attachments.append({
                    "type": attach,
                    "attachment": attach_data
                })
        print("AI RESULT")
        print(ai_result)
        print("ATTACHMENTS")
        print(attachments)
        ai_message = Message(
            role="assistant",
            content=ai_result.get("message", ""),
            timestamp=now,
            attachments=attachments,
            feedback=None,
            metrics=None
        )

        update_result = await threads_collection.update_one(
            {"_id": ObjectId(_id)},
            {
                "$push": {"messages": ai_message.model_dump(by_alias=True)},
                "$set": {"lastUpdatedAt": now}
            }
        )

        if update_result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Thread not found")

        return ai_message

    except Exception as e:
        logger.error(f"Failed to update chat thread: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update chat thread")

async def update_thread_user(thread_id: str, message: str):
    """
    Append an user message to an existing thread in MongoDB.
    """
    try:
        threads_collection = get_collection("threads")
        now = datetime.now(timezone.utc)

        user_message = Message(
            role="user",
            content=message,
            timestamp=now,
            attachments=[],
            feedback=None,
            metrics=None
        )

        update_result = await threads_collection.update_one(
            {"thread_id": thread_id},
            {
                "$push": {"messages": user_message.model_dump(by_alias=True)},
                "$set": {"lastUpdatedAt": now}
            }
        )

        if update_result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Thread not found")

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Failed to update chat thread: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update chat thread")


async def call_agent(project_id: str, thread_id: str, current_message: str, past_messages: List[Message]):
    try:
        agent = DataAnalysisAgent()
        datasets = await get_project_data_sources(project_id)
        ai_state = await agent.analyze(
            project_id=project_id,
            query=current_message,
            datasets=datasets,
            past_messages=past_messages[-10:]
        )
        print("RESULT")
        print(ai_state)
        with open("ai_result.json", "w") as f:
            json.dump(ai_state, f)
        ai_message = await update_thread_ai(thread_id, ai_state['result'])
    except Exception as e:
        logger.error(f"Agent error: {str(e)}")
        logger.error(traceback.format_exc())
        ai_state = None
        ai_message = await update_thread_ai(thread_id, {"message": "Something went wrong. Please try again.", "status": "error"})
    return ai_message, ai_state

async def get_messages(project_id: str, thread_id: str):
    try:
        threads_collection = get_collection("threads")
        result = await threads_collection.find_one(
            {"thread_id": thread_id},
            {"project_id": 1, "messages": 1, "_id": 0}
        )
        # Check if the thread belongs to the project
        if result["project_id"] != project_id:
            raise HTTPException(status_code=404, detail="Thread not found")
        # Return the messages
        return result["messages"]
    except Exception as e:
        logger.error(f"Failed to get messages: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get messages")
