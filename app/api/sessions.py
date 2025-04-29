from fastapi import APIRouter, HTTPException
from app.models.sessions import UploadSession
from app.services.mongodb import get_database

router = APIRouter()

@router.get("/{session_id}", response_model=UploadSession)
async def get_session(session_id: str):
    """Retrieve session details including files, relationships and blob URLs."""
    try:
        db = get_database()
        session = await db.sessions.find_one({"_id": session_id})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        return UploadSession(**session)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve session: {str(e)}"
        ) 