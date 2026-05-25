import requests
import time

BASE_URL = "http://127.0.0.1:8000"
ADMIN_SECRET = "my-admin-secret-change-this"

def run_test():
    print("--- 1. Generating API Key ---")
    response = requests.post(
        f"{BASE_URL}/admin/create-key?name=test_user",
        headers={"admin-secret": ADMIN_SECRET}
    )
    if response.status_code != 200:
        print("Failed to create key:", response.text)
        return
        
    api_key = response.json()["api_key"]
    print(f"Success! Generated API Key: {api_key}\n")

    print("--- 2. Submitting Audio File ---")
    # Using the harvard.wav file that is already in your project folder
    try:
        with open("harvard.wav", "rb") as f:
            response = requests.post(
                f"{BASE_URL}/transcribe",
                headers={"x-api-key": api_key},
                files={"file": ("harvard.wav", f, "audio/wav")}
            )
    except FileNotFoundError:
        print("Could not find harvard.wav in the folder. Please ensure there is an audio file to test with.")
        return

    if response.status_code != 200:
        print("Failed to submit audio:", response.text)
        return
        
    task_id = response.json()["task_id"]
    print(f"Success! Task queued. Task ID: {task_id}\n")

    print("--- 3. Polling for Status ---")
    while True:
        status_response = requests.get(
            f"{BASE_URL}/status/{task_id}",
            headers={"x-api-key": api_key}
        )
        
        data = status_response.json()
        status = data["status"]
        
        print(f"Current Status: {status}...")
        
        if status == "completed":
            print("\n Transcription Finished!")
            print("Transcript:", data["transcript"])
            print("Seconds Billed:", data["duration_seconds"])
            break
        elif status == "failed":
            print("\n Transcription Failed!")
            print("Error:", data["error_message"])
            break
            
        # Wait 2 seconds before checking again
        time.sleep(2)

if __name__ == "__main__":
    run_test()
