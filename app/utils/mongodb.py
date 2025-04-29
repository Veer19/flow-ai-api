import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection details from environment variables
MONGODB_CONNECTION_STRING = os.getenv("MONGODB_CONNECTION_STRING")
MONGODB_DATABASE_NAME = os.getenv("MONGODB_DATABASE_NAME", "dataapp")

# Singleton pattern for MongoDB client
class MongoDBClient:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            if not MONGODB_CONNECTION_STRING:
                raise ValueError("MongoDB connection string not found in environment variables")
            
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        if self._instance is not None:
            raise RuntimeError("Use get_instance() to get the MongoDB client instance")
        
        self.client = MongoClient(MONGODB_CONNECTION_STRING)
        self.db = self.client[MONGODB_DATABASE_NAME]
    
    def get_collection(self, collection_name):
        """Get a MongoDB collection by name"""
        return self.db[collection_name]
    
    def close(self):
        """Close the MongoDB connection"""
        if hasattr(self, 'client'):
            self.client.close()

# Helper function to get a collection
def get_collection(collection_name):
    """Get a MongoDB collection by name"""
    mongo_client = MongoDBClient.get_instance()
    return mongo_client.get_collection(collection_name) 