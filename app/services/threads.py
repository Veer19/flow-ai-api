from app.services.mongodb import get_collection
from fastapi import HTTPException
from datetime import datetime, timezone
from app.models.chat import Thread, Message
import logging
from bson.objectid import ObjectId
from typing import List
from app.agent import DataAnalysisAgent
from app.models.data_sources import DataSource
from app.models.agent_response import FormatResponseLLMResponse, ResponseType
from app.agent import DataAnalysisAgentResponse

logger = logging.getLogger(__name__)


async def get_threads(project_id: str, user_id: str) -> List[Thread]:
    try:
        threads_collection = get_collection("threads")
        cursor = threads_collection.find(
            {"project_id": project_id, "user_id": user_id},
            sort=[("last_updated_at", -1)]
        ).limit(10)
        result = await cursor.to_list(length=10)
        result = [Thread(id=str(thread["_id"]), **thread) for thread in result]
        return result
    except Exception as e:
        logger.error(f"Failed to get threads: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get threads")


async def get_thread(thread_id: str, user_id: str) -> Thread:
    try:
        threads_collection = get_collection("threads")
        result = await threads_collection.find_one({"_id": ObjectId(thread_id)})
        if result.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")
        return Thread(id=str(result["_id"]), **result)
    except Exception as e:
        logger.error(f"Failed to get thread: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get thread")


async def get_message(message_id: str):
    try:
        messages_collection = get_collection("messages")
        result = await messages_collection.find_one({"_id": ObjectId(message_id)})
        return Message(id=str(result["_id"]), **result)
    except Exception as e:
        logger.error(f"Failed to get message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get message")


async def get_messages(thread_id: str, user_id: str):
    try:
        messages_collection = get_collection("messages")
        result = await messages_collection.find(
            {"thread_id": thread_id}
        ).sort("timestamp", -1).limit(10).to_list(length=10)
        for message in result:
            if message.get("user_id") != user_id:
                raise HTTPException(status_code=403, detail="Unauthorized")
        result = [Message(id=str(message["_id"]), **message)
                  for message in result]
        result.reverse()
        return result
    except Exception as e:
        logger.error(f"Failed to get messages: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get messages")


async def create_chat_thread_with_message(project_id: str, user_id: str, first_message: str):
    try:
        threads_collection = get_collection("threads")
        now = datetime.now(timezone.utc)
        thread_data = {
            "project_id": project_id,
            "user_id": user_id,
            "status": "OPEN",
            "created_at": now,
            "last_updated_at": now
        }

        result = await threads_collection.insert_one(thread_data)
        created_thread = await get_thread(str(result.inserted_id), user_id)

        await create_user_message(project_id, str(result.inserted_id), user_id, first_message)
        return created_thread

    except Exception as e:
        logger.error(f"Failed to create chat thread: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to create chat thread")


async def create_message(message: dict):
    """
    Create a new message in MongoDB.
    """
    threads_collection = get_collection("threads")
    messages_collection = get_collection("messages")
    result = await messages_collection.insert_one(message)
    await threads_collection.update_one(
        {"_id": ObjectId(message["thread_id"])},
        {
            "$set": {"last_updated_at": message["timestamp"]}
        }
    )
    return result.inserted_id


async def create_assistant_message(project_id: str, thread_id: str, user_id: str, ai_result: FormatResponseLLMResponse):
    """
    Append an AI response message to an existing thread in MongoDB.
    """
    try:
        now = datetime.now(timezone.utc)
        attachments = []
        attach = ai_result.attach
        if attach:
            attach_data = ai_result.data
            if (type(attach_data) == dict):
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

        assistant_message = {
            "project_id": project_id,
            "thread_id": thread_id,
            "user_id": user_id,
            "role": "assistant",
            "content": ai_result.message,
            "timestamp": now,
            "attachments": attachments,
            "feedback": None,
            "metrics": None
        }

        created_message_id = await create_message(assistant_message)

        created_message = await get_message(str(created_message_id))
        return created_message

    except Exception as e:
        logger.error(f"Failed to update chat thread: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to update chat thread")


async def create_user_message(project_id: str, thread_id: str, user_id: str, message: str):
    """
    Append an user message to an existing thread in MongoDB.
    """
    try:
        messages_collection = get_collection("messages")
        now = datetime.now(timezone.utc)

        user_message = {
            "project_id": project_id,
            "thread_id": thread_id,
            "user_id": user_id,
            "role": "user",
            "content": message,
            "timestamp": now,
            "attachments": [],
            "feedback": None,
            "metrics": None
        }
        return await messages_collection.insert_one(user_message)

    except Exception as e:
        logger.error(f"Failed to update chat thread: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to update chat thread")


async def call_agent(project_id: str, thread_id: str, user_id: str, current_message: str, past_messages: List[Message], datasets: List[DataSource]):
    try:
        agent = DataAnalysisAgent()
        agent_response: DataAnalysisAgentResponse = await agent.analyze(
            project_id=project_id,
            query=current_message,
            datasets=datasets,
            past_messages=[message.to_llm_dict()
                           for message in past_messages[-10:]]
        )
        ai_message = await create_assistant_message(project_id, thread_id, user_id, agent_response.result)
        return ai_message, agent_response
    except Exception as e:
        logger.error(f"Failed to call agent: {str(e)}")
        error_message = FormatResponseLLMResponse(
            type=ResponseType.ERROR,
            message="Something went wrong, please try again!"
        )
        ai_message = await create_assistant_message(project_id, thread_id, user_id, error_message)
        return ai_message, None
