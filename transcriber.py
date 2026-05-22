import os 
import whisper

print("Loading Whisper Model.....")
model = whisper.load_model("base")
print("Model Loaded Successfully")

def transcribe_audio(file_path: str) -> dict:
    try:
        result = model.transcribe(file_path)
        return {
            "success": True,
            "transcript": result['text'].strip(),
            "language": result['language']
        }
    except Exception as e:
        return { 
            "success": False,
            "error": str(e)
        }
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

