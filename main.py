from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.services.mongodb import close_mongo_connection, connect_to_mongo
from contextlib import asynccontextmanager
from app.api.projects import router as projects_router
from app.middleware.mongodb_serializer import MongoDBSerializerMiddleware
from app.api.auth import verify_jwt_token
from fastapi import Depends

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(lifespan=lifespan, redirect_slashes=False)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://flow-ai-murex.vercel.app", "http://localhost:3000"],  # Your Next.js app origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add MongoDB serializer middleware
app.add_middleware(MongoDBSerializerMiddleware)

# Include routers

@app.get("/health")
async def health_check():
    return {"status": "Flow AI API is running"} 
app.include_router(projects_router, prefix="/projects", tags=["projects"])

@app.get("/secure-data")
async def get_secure_data(user: dict = Depends(verify_jwt_token)):
    return {"message": f"Hello {user['sub']}, here’s your protected data."}