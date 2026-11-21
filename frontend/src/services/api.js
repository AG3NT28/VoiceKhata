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

export function sendAudio(wavBlob, languageCode = 'hi-IN,en-IN') {
  const form = new FormData();
  form.append('audio', wavBlob, 'audio.wav');
  form.append('language_code', languageCode);
  return fetch(`${API_BASE}/voice/command`, { method: 'POST', body: form }).then(toJson);
}

export function sendText(text) {
  return fetch(`${API_BASE}/voice/text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  }).then(toJson);
}

export function undoLast() {
  return fetch(`${API_BASE}/voice/undo`, { method: 'POST' }).then(toJson);
}
export async function speakText(text, language = 'hi-en') {
  const res = await fetch(`${API_BASE}/voice/speak`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, language }),
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try { const b = await res.json(); detail = b.detail || detail; } catch {}
    throw new Error(detail);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  audio.onended = () => URL.revokeObjectURL(url);
  await audio.play();
  return audio;
}
