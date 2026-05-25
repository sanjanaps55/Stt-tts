from .database import get_supabase
import os 
from faster_whisper import WhisperModel
import logging

log = logging.getLogger(__name__)

log.info("Loading Whisper Model.....")
# Using int8 compute type for CPU optimization. If you have a GPU, change device to "cuda" and compute_type="float16"
model = WhisperModel("base", device="cpu", compute_type="int8")
log.info("Model Loaded Successfully")

def run_transcription_task(task_id: str, file_path: str, storage_filename: str = None):
    log.info(f"Task {task_id} started processing...")
    
    supabase = get_supabase()
    supabase.table("transcription_tasks").update({"status": "processing"}).eq("task_id", task_id).execute()

    try:
        # Transcribe the audio file directly with VAD filter to skip silence (huge speedup)
        segments, info = model.transcribe(file_path, beam_size=5, vad_filter=True)
        
        # faster-whisper returns a generator, so we join the segments
        transcript = " ".join([segment.text for segment in segments]).strip()
        language = info.language
        duration_seconds = info.duration
        
        supabase.table("transcription_tasks").update({
            "status": "completed",
            "transcript": transcript,
            "language": language,
            "duration_seconds": duration_seconds
        }).eq("task_id", task_id).execute()
            
        log.info(f"Task {task_id} completed successfully.")
        
    except Exception as e:
        error_msg = str(e)
        log.error(f"Task {task_id} failed: {error_msg}")
        supabase.table("transcription_tasks").update({
            "status": "failed",
            "error_message": error_msg
        }).eq("task_id", task_id).execute()
            
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        if storage_filename:
            try:
                log.info(f"Removing {storage_filename} from Supabase Storage...")
                supabase.storage.from_("audio-uploads").remove([storage_filename])
            except Exception as e:
                log.error(f"Failed to delete {storage_filename} from storage: {e}")
