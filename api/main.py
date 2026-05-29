import os
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
import asyncio
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import websockets as dg_websockets
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

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




@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/tts/preload")
async def tts_preload(request: Request):
    payload = await request.json()
    tts_url = os.getenv("TTS_API_URL")
    if not tts_url:
        return {"error": "TTS_API_URL not found in .env"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{tts_url}/tts/preload", json=payload, timeout=10.0)
            # Try parsing json if possible, else return text
            try:
                return resp.json()
            except:
                return {"message": resp.text}
    except Exception as e:
        log.error(f"TTS preload error: {e}")
        return {"error": str(e)}

@app.post("/tts/stream")
async def tts_stream(request: Request):
    payload = await request.json()
    tts_url = os.getenv("TTS_API_URL")
    
    if not tts_url:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="TTS_API_URL not found in .env")

    log.info(f"🚀 PROOF: Routing audio generation to external server -> {tts_url}")
    
    async def proxy_stream():
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream("POST", f"{tts_url}/tts/stream", json=payload, timeout=30.0) as response:
                    async for chunk in response.aiter_bytes():
                        yield chunk
        except Exception as e:
            log.error(f"TTS stream error: {e}")

    return StreamingResponse(proxy_stream(), media_type="application/octet-stream")

@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    await websocket.accept()
    
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
    if not DEEPGRAM_API_KEY:
        await websocket.send_json({"error": "DEEPGRAM_API_KEY not found in .env"})
        await websocket.close()
        return

    # Deepgram's nova-2 model automatically detects language if we don't specify it,
    # or we can use language=multi depending on the model tier.
    dg_url = "wss://api.deepgram.com/v1/listen?model=nova-2&smart_format=true"
    
    try:
        async with dg_websockets.connect(
            dg_url,
            additional_headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"}
        ) as deepgram_ws:
            
            async def sender():
                try:
                    while True:
                        data = await websocket.receive_bytes()
                        await deepgram_ws.send(data)
                except WebSocketDisconnect:
                    pass
                except Exception as e:
                    log.error(f"Sender error: {e}")

            async def receiver():
                try:
                    while True:
                        result = await deepgram_ws.recv()
                        res_json = json.loads(result)
                        
                        if "channel" in res_json:
                            transcript = res_json["channel"]["alternatives"][0]["transcript"]
                            if transcript:
                                await websocket.send_json({"text": transcript})
                except Exception as e:
                    log.error(f"Receiver error: {e}")
            
            await asyncio.gather(sender(), receiver())

    except Exception as e:
        log.error(f"Deepgram connection error: {e}")
        try:
            await websocket.send_json({"error": "Failed to connect to transcription provider."})
            await websocket.close()
        except:
            pass

# Serve the frontend (Must be at the bottom to prevent catching API routes)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)
