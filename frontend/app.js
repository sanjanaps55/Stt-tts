const API_BASE_URL = 'http://127.0.0.1:8000';

// Navigation Logic
const navLinks = document.querySelectorAll('.nav-link');
const viewSections = document.querySelectorAll('.view-section');

navLinks.forEach(link => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    const targetId = link.getAttribute('data-target');
    
    // Update active nav
    navLinks.forEach(nav => nav.classList.remove('active'));
    link.classList.add('active');
    
    // Update active view
    viewSections.forEach(section => {
      section.classList.remove('active');
      if (section.id === targetId) {
        section.classList.add('active');
      }
    });
  });
});

// Dashboard Logic
const fetchKeysBtn = document.getElementById('fetchKeysBtn');
const createKeyBtn = document.getElementById('createKeyBtn');
const keysList = document.getElementById('keysList');
const devOwnerInput = document.getElementById('devOwner');
const devSecretInput = document.getElementById('devSecret');

// Playground key is now hardcoded for demo purposes
// No local storage save required

async function fetchKeys() {
  const owner = devOwnerInput.value.trim();
  const secret = devSecretInput.value.trim();
  if (!owner || !secret) return alert("Please enter Username and Admin Secret");

  keysList.innerHTML = '<p>Loading...</p>';
  try {
    const res = await fetch(`${API_BASE_URL}/developer/keys?owner=${encodeURIComponent(owner)}`, {
      headers: { 'admin-secret': secret }
    });
    if (!res.ok) throw new Error("Unauthorized or Error");
    
    const data = await res.json();
    renderKeys(data.keys);
  } catch (err) {
    keysList.innerHTML = `<p style="color: #ef4444;">Error fetching keys: ${err.message}</p>`;
  }
}

async function createKey() {
  const owner = devOwnerInput.value.trim();
  const secret = devSecretInput.value.trim();
  if (!owner || !secret) return alert("Please enter Username and Admin Secret");

  try {
    const res = await fetch(`${API_BASE_URL}/admin/create-key?name=${encodeURIComponent(owner)}`, {
      method: 'POST',
      headers: { 'admin-secret': secret }
    });
    if (!res.ok) throw new Error("Unauthorized or Error");
    
    await fetchKeys(); // Refresh list
  } catch (err) {
    alert(`Error creating key: ${err.message}`);
  }
}

function renderKeys(keys) {
  if (!keys || keys.length === 0) {
    keysList.innerHTML = '<p>No keys found.</p>';
    return;
  }
  
  keysList.innerHTML = '';
  keys.forEach(key => {
    const div = document.createElement('div');
    div.className = 'api-key-item';
    div.innerHTML = `
      <span class="api-key-value">${key}</span>
    `;
    keysList.appendChild(div);
  });
}

fetchKeysBtn.addEventListener('click', fetchKeys);
createKeyBtn.addEventListener('click', createKey);

// Playground Logic
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

const micBtn = document.getElementById('micBtn');
const pgStatus = document.getElementById('pgStatus');
const pgResultBox = document.getElementById('pgResultBox');
const pgTranscript = document.getElementById('pgTranscript');

micBtn.addEventListener('click', async () => {
  if (!isRecording) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      audioChunks = [];

      mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
      mediaRecorder.onstop = async () => {
        const blob = new Blob(audioChunks, { type: 'audio/webm' });
        stream.getTracks().forEach(t => t.stop());
        await submitAudio(blob, 'recording.webm');
      };

      mediaRecorder.start();
      isRecording = true;
      micBtn.classList.add('recording');
      micBtn.textContent = '⏹';
      pgStatus.textContent = 'Recording... click to stop';
    } catch (err) {
      pgStatus.textContent = 'Microphone access denied.';
    }
  } else {
    mediaRecorder.stop();
    isRecording = false;
    micBtn.classList.remove('recording');
    micBtn.textContent = '🎤';
    pgStatus.textContent = 'Processing...';
  }
});

async function uploadPlaygroundFile() {
  const file = document.getElementById('pgFileInput').files[0];
  if (!file) { pgStatus.textContent = 'Please select a file first.'; return; }
  pgStatus.textContent = 'Uploading and transcribing...';
  await submitAudio(file, file.name);
}

async function submitAudio(blob, filename) {
  const apiKey = 'playground-key'; // Hardcoded for playground

  const formData = new FormData();
  formData.append('file', blob, filename);

  try {
    const res = await fetch(`${API_BASE_URL}/transcribe`, { 
      method: 'POST', 
      headers: { 'x-api-key': apiKey },
      body: formData 
    });
    
    const data = await res.json();
    if (!res.ok) {
      pgStatus.textContent = 'Error: ' + (data.detail || 'Something went wrong');
      return;
    }

    // Since it's async now, we need to poll the status
    const taskId = data.task_id;
    pgStatus.textContent = `Task ${taskId} queued. Polling...`;
    pollStatus(taskId, apiKey);

  } catch (err) {
    pgStatus.textContent = 'Could not reach the server. Is it running?';
  }
}

async function pollStatus(taskId, apiKey) {
  const interval = setInterval(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/status/${taskId}`, {
        headers: { 'x-api-key': apiKey }
      });
      const data = await res.json();
      
      if (data.status === 'completed') {
        clearInterval(interval);
        pgTranscript.textContent = data.transcript;
        pgResultBox.classList.add('visible');
        pgStatus.textContent = `Done! (Language: ${data.language}, Duration: ${data.duration_seconds}s)`;
      } else if (data.status === 'failed') {
        clearInterval(interval);
        pgStatus.textContent = `Error: ${data.error_message}`;
      } else {
        pgStatus.textContent = `Status: ${data.status}...`;
      }
    } catch (err) {
      clearInterval(interval);
      pgStatus.textContent = 'Error polling status.';
    }
  }, 2000); // Poll every 2 seconds
}

// Initialization complete
