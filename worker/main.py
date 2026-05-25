import time
import logging
from .database import get_supabase
from .transcriber import run_transcription_task

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | Worker | %(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)

def main():
    log.info("Starting Worker Polling Loop...")
    supabase = get_supabase()

    while True:
        try:
            # Poll for pending tasks
            response = supabase.table("transcription_tasks").select("task_id").eq("status", "pending").limit(1).execute()
            
            if response.data:
                task_id = response.data[0]["task_id"]
                log.info(f"Found pending task: {task_id}")
                
                # Search for the file in Supabase Storage
                try:
                    # List files in the bucket
                    files = supabase.storage.from_("audio-uploads").list()
                    # The API saves files as {task_id}{ext}
                    target_file = next((f for f in files if f["name"].startswith(task_id)), None)
                    
                    if target_file:
                        storage_filename = target_file["name"]
                        local_file_path = f"worker_temp_{storage_filename}"
                        
                        log.info(f"Downloading {storage_filename} from Supabase Storage...")
                        # Download the file to local disk for processing
                        res = supabase.storage.from_("audio-uploads").download(storage_filename)
                        with open(local_file_path, "wb") as f:
                            f.write(res)
                            
                        # Run the transcription synchronously
                        run_transcription_task(task_id, local_file_path, storage_filename)
                    else:
                        log.error(f"Could not find audio file for task {task_id} in Storage")
                        supabase.table("transcription_tasks").update({
                            "status": "failed",
                            "error_message": "Audio file not found in Supabase Storage"
                        }).eq("task_id", task_id).execute()
                except Exception as e:
                    log.error(f"Error accessing Supabase Storage for task {task_id}: {e}")
                    supabase.table("transcription_tasks").update({
                        "status": "failed",
                        "error_message": f"Storage error: {str(e)}"
                    }).eq("task_id", task_id).execute()
            else:
                # No pending tasks, sleep for a bit to avoid hammering the database
                time.sleep(3)
                
        except Exception as e:
            log.error(f"Error in polling loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
