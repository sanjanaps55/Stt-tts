const API_BASE_URL = 'http://127.0.0.1:8000';
const WS_URL = 'ws://127.0.0.1:8000/ws/transcribe';

let mediaRecorder = null;
let socket = null;
let isRecording = false;

const micBtn = document.getElementById('micBtn');
const pgStatus = document.getElementById('pgStatus');
const pgResultBox = document.getElementById('pgResultBox');
const pgTranscript = document.getElementById('pgTranscript');

micBtn.addEventListener('click', async () => {
  if (!isRecording) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      socket = new WebSocket(WS_URL);
      
      socket.onopen = () => {
        mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        mediaRecorder.ondataavailable = e => {
          if (e.data.size > 0 && socket.readyState === WebSocket.OPEN) {
            socket.send(e.data);
          }
        };
        // Send data chunks every 250ms for real-time
        mediaRecorder.start(250);
        
        isRecording = true;
        micBtn.classList.add('recording');
        micBtn.textContent = '⏹';
        pgStatus.textContent = 'Streaming... Speak in any language!';
        pgTranscript.textContent = ''; // Clear old transcript
      };

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.text) {
          pgTranscript.textContent += data.text + ' ';
          // Auto scroll to bottom
          pgTranscript.scrollTop = pgTranscript.scrollHeight;
        } else if (data.error) {
          pgStatus.textContent = `Error: ${data.error}`;
        }
      };

      socket.onerror = (error) => {
        console.error("WebSocket Error:", error);
        pgStatus.textContent = 'WebSocket connection error.';
      };

      socket.onclose = () => {
        if (isRecording) stopRecording(stream);
      };

    } catch (err) {
      console.error(err);
      pgStatus.textContent = 'Microphone access denied or error connecting.';
    }
  } else {
    stopRecording();
  }
});

function stopRecording(stream = null) {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
  if (stream) {
    stream.getTracks().forEach(t => t.stop());
  } else if (mediaRecorder && mediaRecorder.stream) {
    mediaRecorder.stream.getTracks().forEach(t => t.stop());
  }
  
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.close();
  }
  
  isRecording = false;
  micBtn.classList.remove('recording');
  micBtn.textContent = '🎤';
  pgStatus.textContent = 'Stopped. Click to record again.';
}
