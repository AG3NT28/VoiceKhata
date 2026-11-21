const API_BASE = import.meta.env.VITE_API_BASE || '';

async function toJson(response) {
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail || body.message || detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return response.json();
}

export function getState() {
  return fetch(`${API_BASE}/voice/state`).then(toJson);
}

export function sendAudio(wavBlob) {
  const form = new FormData();
  form.append('audio', wavBlob, 'audio.wav');
  return fetch(`${API_BASE}/voice/command`, { method: 'POST', body: form }).then(toJson);
}

export function sendText(text) {
  return fetch(`${API_BASE}/voice/text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  }).then(toJson);
}

export { API_BASE };
