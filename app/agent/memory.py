from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, UTC
from typing import List, Dict

class MemoryStore:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["chat_threads"]

    async def load_thread(self, thread_id: str) -> Dict:
        doc = await self.collection.find_one({"thread_id": thread_id})
        if not doc:
            return {
                "thread_id": thread_id,
                "status": "OPEN",
                "messages": [],
                "createdAt": datetime.now(UTC),
                "updatedAt": datetime.now(UTC)
            }
        return doc

    async def append_messages(self, thread_id: str, new_messages: List[Dict]):
        await self.collection.update_one(
            {"thread_id": thread_id},
            {
                "$push": {"messages": {"$each": new_messages}},
                "$set": {"updatedAt": datetime.now(UTC)},
                "$setOnInsert": {
                    "createdAt": datetime.now(UTC),
                    "status": "OPEN"
                }
            },
            upsert=True
        )

    async def get_recent_messages(self, thread_id: str, max_tokens: int = 3000) -> List[Dict]:
        doc = await self.collection.find_one({"thread_id": thread_id}, {"messages": 1})
        if not doc or "messages" not in doc:
            return []

        messages = doc["messages"]
        total = 0
        result = []

        for msg in reversed(messages):
            est = len(msg.get("content", "").split())
            if total + est > max_tokens:
                break
            result.insert(0, msg)
            total += est

        return result
