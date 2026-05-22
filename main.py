from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from auth import is_valid_api_key,get_key_owner,add_new_key
from transcriber import transcribe_audio
import logging
import uvicorn
import os
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)

app = FastAPI(
    title="Speech-to-Text API",
    description="Transcribe audio via browser mic or API key.",
    version="1.0.0"
)

# Serve the frontend folder as static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")
ALLOWED_EXTENSIONS = [".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"]
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


@app.get("/")
def serve_frontend():
    return FileResponse("frontend/index.html")

# Health Check
@app.get("/health")
def health():
    return {"status": "healthy"}
#Post checkcing 
@app.post("/posttest")
def posttest():
    return {"message": "Post working"}
#---Upload---
@app.post("/upload")
def upload(file:UploadFile = File(...)):   
    return {"file_name": file.filename}

@app.post("/transcribe")
async def transcribe_endpoint(file:UploadFile = File(...),x_api_key:Optional[str]=Header(default=None)):
    if x_api_key is not None:
        if not is_valid_api_key(x_api_key):
            raise HTTPException(status_code=401, detail="Invalid API Key")
        owner=get_key_owner(x_api_key)
        logging.info(f"Incoming request from {owner} for {file.filename}")
    else:
        logging.info("No API Key Provided")
        return {"message": "No API Key Provided"}
    filename = file.filename or "upload"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Allowed: {ALLOWED_EXTENSIONS}"
        )
    audio_bytes = await file.read()
    if len(audio_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max 25MB.")

    # Save temporarily for Whisper
    temp_path = f"temp_{filename}"
    with open(temp_path, "wb") as f:
        f.write(audio_bytes)

    logging.info(f"Transcribing: {filename} ({len(audio_bytes)} bytes)")
    result = transcribe_audio(temp_path)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {result['error']}")
    logging.info(f"Done — language: {result['language']}")

    return {
        "transcript": result["transcript"],
        "language": result["language"],
        "filename": filename
    }
@app.post("/admin/create-key")
def create_key(name: str, admin_secret: str = Header(...)):
    # Simple protection: only you know this secret
    if admin_secret != "my-admin-secret-change-this":
        raise HTTPException(status_code=403, detail="Forbidden")
    key = add_new_key(name)
    return {"name": name, "api_key": key}
    #----Start server-----
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
