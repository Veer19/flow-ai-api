import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from app.config import get_settings

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mongodb")

# Get settings
settings = get_settings()

# MongoDB connection details - prefer settings, fall back to env var
MONGODB_URL = settings.MONGODB_URL if hasattr(settings, 'MONGODB_URL') else os.getenv("MONGODB_URL")

# Global MongoDB client instance
mongodb_client = None
mongodb_db = None

async def connect_to_mongo():
    """Connect to MongoDB Atlas"""
    global mongodb_client, mongodb_db
    
    if not MONGODB_URL:
        logger.error("MONGODB_URL environment variable not set")
        raise ValueError("MONGODB_URL environment variable not set")
    
    try:
        logger.info("Connecting to MongoDB Atlas...")
        # Add connection parameters to improve reliability
        mongodb_client = AsyncIOMotorClient(
            MONGODB_URL,
            serverSelectionTimeoutMS=10000,  # 10 seconds timeout for server selection
            connectTimeoutMS=20000,          # 20 seconds timeout for connection
            socketTimeoutMS=30000,           # 30 seconds timeout for socket operations
            maxPoolSize=10,                  # Maximum connection pool size
            retryWrites=True,                # Retry write operations
            w="majority"                     # Write concern
        )
        
        # Extract database name from connection string or use default
        db_name = MONGODB_URL.split("/")[-1].split("?")[0] or "dataapp"
        mongodb_db = mongodb_client[db_name]
        
        # Verify connection by executing a simple command
        await mongodb_client.admin.command("ping")
        logger.info(f"Connected to MongoDB Atlas - Database: {db_name}")
        
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        if mongodb_client:
            mongodb_client.close()
            mongodb_client = None
        raise

async def close_mongo_connection():
    """Close MongoDB connection"""
    global mongodb_client
    
    if mongodb_client:
        logger.info("Closing MongoDB connection...")
        mongodb_client.close()
        mongodb_client = None
        logger.info("MongoDB connection closed")

def get_database():
    """Get MongoDB database instance"""
    if not mongodb_db:
        raise RuntimeError("MongoDB connection not established. Call connect_to_mongo() first.")
    return mongodb_db

def get_collection(collection_name):
    """Get a MongoDB collection by name"""
    db = get_database()
    return db[collection_name]

settings = get_settings()
_mongodb_client: AsyncIOMotorClient = None

async def connect_to_mongo():
    global _mongodb_client
    _mongodb_client = AsyncIOMotorClient(settings.MONGODB_URL)

async def close_mongo_connection():
    global _mongodb_client
    if _mongodb_client:
        _mongodb_client.close()

def get_database():
    return _mongodb_client.database 