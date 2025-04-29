from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import datasets, charts, uploads, sessions
from app.services.mongodb import close_mongo_connection, connect_to_mongo
from contextlib import asynccontextmanager
from app.api import projects
from app.middleware.mongodb_serializer import MongoDBSerializerMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(lifespan=lifespan, redirect_slashes=False)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://flow-bzj3ie6pf-veer19s-projects.vercel.app", "http://localhost:3000"],  # Your Next.js app origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add MongoDB serializer middleware
app.add_middleware(MongoDBSerializerMiddleware)

# Include routers
app.include_router(uploads.router, prefix="/upload", tags=["upload"])
app.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
app.include_router(charts.router, prefix="/charts", tags=["charts"])
app.include_router(sessions.router, prefix="/api")
app.include_router(projects.router, prefix="/projects", tags=["projects"])

@app.get("/health")
async def health_check():
    return {"status": "Flow AI API is running"} 