import uuid
import numpy as np
from typing import List
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl

from config import settings
from database import get_db, EventPhoto, PhotoFaceEmbedding, SessionLocal
from ml_pipeline import decode_base64_to_cv2, extract_primary_face_embedding
from drive_service import extract_folder_id, index_drive_folder_task

# ==========================================
# FastAPI Initialization
# ==========================================
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Search event photos using ArcFace facial recognition."
)

# Mount static folder for serving HTML, CSS, and JavaScript
app.mount("/static", StaticFiles(directory="static"), name="static")

# Track indexing tasks state
indexing_tasks = {}

# ==========================================
# Pydantic Schemas
# ==========================================
class IndexDriveRequest(BaseModel):
    drive_link: str

class SearchFaceRequest(BaseModel):
    image: str  # Base64 encoded selfie string from webcam or file upload

# ==========================================
# Background Processing Wrapper
# ==========================================
async def background_indexing_wrapper(task_id: str, drive_link: str):
    global indexing_tasks
    indexing_tasks[task_id] = {
        "status": "processing",
        "progress": "Scanning and indexing Drive vector embeddings..."
    }
    
    try:
        await index_drive_folder_task(drive_link)
        indexing_tasks[task_id] = {
            "status": "completed",
            "message": "Indexing completed successfully."
        }
    except Exception as e:
        print(f"Background indexing error: {e}")
        indexing_tasks[task_id] = {
            "status": "failed",
            "message": f"Indexing failed: {str(e)}"
        }

# ==========================================
# API Endpoints
# ==========================================
@app.get("/")
def read_root():
    """Serves the main frontend UI."""
    return FileResponse("static/index.html")


@app.post("/api/index-drive")
def start_drive_indexing(payload: IndexDriveRequest, background_tasks: BackgroundTasks):
    """
    Parses a Google Drive folder link/ID and initiates background 
    in-memory face extraction and indexing.
    """
    # Check if any task is actively processing
    for task in indexing_tasks.values():
        if task.get("status") == "processing":
            raise HTTPException(
                status_code=400, 
                detail="An indexing process is already running. Please wait for it to complete."
            )

    folder_id = extract_folder_id(payload.drive_link)
    if not folder_id:
        raise HTTPException(
            status_code=400, 
            detail="Invalid Google Drive folder URL or ID format."
        )

    task_id = str(uuid.uuid4())
    indexing_tasks[task_id] = {
        "status": "processing",
        "folder_id": folder_id
    }
    
    # Trigger background task
    background_tasks.add_task(background_indexing_wrapper, task_id, payload.drive_link)
    
    return {
        "status": "started",
        "task_id": task_id,
        "folder_id": folder_id,
        "message": "Folder indexing started in background."
    }


@app.get("/api/index-status/{task_id}")
def get_indexing_status(task_id: str):
    """Returns the current background indexing status for a task."""
    task = indexing_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/api/search-face")
def search_face_in_drive(payload: SearchFaceRequest, db=Depends(get_db)):
    all_stored_faces = db.query(PhotoFaceEmbedding).all()
    if not all_stored_faces:
        raise HTTPException(
            status_code=400, 
            detail="No event photos have been indexed yet."
        )

    frame = decode_base64_to_cv2(payload.image)
    if frame is None:
        raise HTTPException(status_code=400, detail="Failed to decode submitted selfie image.")

    query_vector = extract_primary_face_embedding(frame)
    if query_vector is None:
        raise HTTPException(
            status_code=400, 
            detail="Could not extract a valid face embedding from your selfie. Please ensure good lighting and face the camera directly."
        )

    query_vector = np.array(query_vector, dtype=np.float32)
    q_std = np.std(query_vector)
    
    print(f"Query Vector Stats -> Std: {q_std:.6f}, Norm: {np.linalg.norm(query_vector):.4f}")

    if q_std < 0.01:
        raise HTTPException(
            status_code=400, 
            detail="Selfie image feature extraction failed (collapsed vector). Please retake the selfie."
        )

    matched_photo_ids = set()
    similarity_threshold = settings.FACE_SIMILARITY_THRESHOLD

    print(f"\n--- Running Cosine Search (Threshold: {similarity_threshold}) ---")
    
    scores = []
    for record in all_stored_faces:
        stored_vector = np.array(record.get_vector(), dtype=np.float32)
        
        # Skip invalid stored vectors
        if np.std(stored_vector) < 0.01:
            continue
            
        s_norm = np.linalg.norm(stored_vector)
        if s_norm > 0:
            stored_vector = stored_vector / s_norm
        
        similarity = float(np.dot(query_vector, stored_vector))
        scores.append((record.photo_id, similarity))

        if similarity >= similarity_threshold:
            matched_photo_ids.add(record.photo_id)

    if scores:
        top_scores = sorted(scores, key=lambda x: x[1], reverse=True)[:5]
        print(f"Top 5 match scores: {top_scores}\n")

    if not matched_photo_ids:
        return {
            "status": "success",
            "count": 0,
            "results": [],
            "message": "No matching photos found in this album."
        }

    matched_photos = db.query(EventPhoto).filter(EventPhoto.id.in_(list(matched_photo_ids))).all()

    results = [
        {
            "id": photo.id,
            "file_name": photo.file_name,
            "drive_link": photo.view_link,
            "preview_url": f"https://lh3.googleusercontent.com/d/{photo.drive_file_id}=s800"
        }
        for photo in matched_photos
    ]

    return {
        "status": "success",
        "count": len(results),
        "results": results
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)