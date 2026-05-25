import os
import logging
import uuid
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Header, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .auth import is_valid_api_key, get_key_owner, add_new_key, get_keys_for_owner
from .database import get_supabase

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)

app = FastAPI(
    title="Speech-to-Text API",
    description="Production-grade SaaS API for Audio Transcription",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



ALLOWED_EXTENSIONS = [".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"]
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB



@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/upload")
def upload(file: UploadFile = File(...)):   
    return {"file_name": file.filename}

@app.post("/transcribe")
def transcribe_endpoint(
    file: UploadFile = File(...), 
    x_api_key: Optional[str] = Header(default=None)
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API Key")
        
    if not is_valid_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API Key")
        
    owner = get_key_owner(x_api_key)
    log.info(f"Incoming async transcription request from user: {owner}")
    
    filename = file.filename or "upload"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Allowed: {ALLOWED_EXTENSIONS}"
        )
        
    audio_bytes = file.file.read()
    if len(audio_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max 25MB.")

    # Rate Limiting: Check concurrent tasks
    supabase = get_supabase()
    
    # Query for tasks that are pending or processing
    response = supabase.table("transcription_tasks").select("task_id").eq("api_key", x_api_key).in_("status", ["pending", "processing"]).execute()
    active_tasks = len(response.data)
        
    if active_tasks >= 2:
        raise HTTPException(
            status_code=429, 
            detail="Rate limit exceeded: You have too many concurrent tasks processing. Please wait for them to finish."
        )

    # Generate a unique task ID
    task_id = str(uuid.uuid4())
    storage_filename = f"{task_id}{ext}"
    
    # Upload to Supabase Storage bucket 'audio-uploads'
    supabase.storage.from_("audio-uploads").upload(
        path=storage_filename, 
        file=audio_bytes,
        file_options={"content-type": f"audio/{ext.strip('.')}"}
    )

    # Insert pending task into database
    supabase.table("transcription_tasks").insert({
        "task_id": task_id,
        "api_key": x_api_key,
        "status": "pending"
    }).execute()

    # Enqueue background task by simply leaving it as pending in the database.
    # The worker will poll Supabase for 'pending' tasks.
    log.info(f"Task {task_id} queued in database for processing.")

    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Audio is processing in the background. Poll the /status endpoint with your task_id."
    }

@app.get("/status/{task_id}")
def get_task_status(task_id: str, x_api_key: Optional[str] = Header(default=None)):
    if not x_api_key or not is_valid_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API Key")

    supabase = get_supabase()
    response = supabase.table("transcription_tasks").select("status, transcript, language, error_message, duration_seconds").eq("task_id", task_id).eq("api_key", x_api_key).execute()
        
    if len(response.data) == 0:
        raise HTTPException(status_code=404, detail="Task not found or you do not have permission to view it.")
        
    task_data = response.data[0]
        
    return task_data

@app.post("/admin/create-key")
def create_key(name: str, admin_secret: str = Header(...)):
    # Simple protection: only you know this secret
    if admin_secret != "my-admin-secret-change-this":
        raise HTTPException(status_code=403, detail="Forbidden")
    key = add_new_key(name)
    return {"name": name, "api_key": key}

@app.get("/developer/keys")
def get_developer_keys(owner: str, admin_secret: str = Header(...)):
    if admin_secret != "my-admin-secret-change-this":
        raise HTTPException(status_code=403, detail="Forbidden")
    keys = get_keys_for_owner(owner)
    return {"owner": owner, "keys": keys}

# Serve the frontend (Must be at the bottom to prevent catching API routes)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)
