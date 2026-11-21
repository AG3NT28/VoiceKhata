/**
 * Microphone capture + conversion to 16 kHz mono WAV.
 * Gnani Prisma accepts WAV/MP3/OGG/FLAC/AAC/M4A (not webm), so we
 * decode the MediaRecorder blob and re-encode it as PCM WAV in-browser.
 *
 * Improvements (Phase A):
 *  - VAD level meter (onLevel callback) for mic feedback
 *  - Silence trimming (leading/trailing) to reduce payload + latency
 *  - 8s auto-stop cap
 */

export function isRecordingSupported() {
  return Boolean(navigator.mediaDevices?.getUserMedia && window.MediaRecorder);
}

export class VoiceRecorder {
  constructor({ onLevel } = {}) {
    this.mediaRecorder = null;
    this.stream = null;
    this.chunks = [];
    this.startedAt = 0;
    this.onLevel = onLevel || null;
    this._autoStopTimer = null;
    this._audioCtx = null;
    this._analyser = null;
    this._rafId = null;
  }

  async start() {
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, sampleRate: 16000, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });

    // VAD level meter
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      this._audioCtx = new AudioCtx();
      const source = this._audioCtx.createMediaStreamSource(this.stream);
      this._analyser = this._audioCtx.createAnalyser();
      this._analyser.fftSize = 512;
      source.connect(this._analyser);
      const data = new Uint8Array(this._analyser.frequencyBinCount);
      const tick = () => {
        if (!this._analyser) return;
        this._analyser.getByteTimeDomainData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i += 1) {
          const v = (data[i] - 128) / 128;
          sum += v * v;
        }
        const rms = Math.sqrt(sum / data.length);
        if (this.onLevel) this.onLevel(Math.min(1, rms * 4));
        this._rafId = requestAnimationFrame(tick);
      };
      this._rafId = requestAnimationFrame(tick);
    } catch {
      /* level meter optional */
    }

    const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', ''];
    const mimeType = candidates.find((type) => !type || MediaRecorder.isTypeSupported(type));
    this.mediaRecorder = new MediaRecorder(this.stream, mimeType ? { mimeType } : undefined);
    this.chunks = [];
    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) this.chunks.push(event.data);
    };
    this.startedAt = Date.now();
    this.mediaRecorder.start();

    this._autoStopTimer = setTimeout(() => {
      if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
        this.mediaRecorder.stop();
      }
    }, 8000);
  }

  async stop() {
    if (!this.mediaRecorder) return null;
    const recorder = this.mediaRecorder;
    clearTimeout(this._autoStopTimer);
    if (this._rafId) cancelAnimationFrame(this._rafId);
    this._rafId = null;
    if (this._audioCtx) { try { this._audioCtx.close(); } catch {} this._audioCtx = null; this._analyser = null; }

    const rawBlob = await new Promise((resolve) => {
      recorder.onstop = () => {
        resolve(new Blob(this.chunks, { type: recorder.mimeType || 'audio/webm' }));
      };
      try { recorder.stop(); } catch { /* already stopped */ }
    });

    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
    this.mediaRecorder = null;
    if (this.onLevel) this.onLevel(0);

    if (!rawBlob.size) return null;
    return blobToWav(rawBlob);
  }

  cancel() {
    clearTimeout(this._autoStopTimer);
    if (this._rafId) cancelAnimationFrame(this._rafId);
    this._rafId = null;
    if (this._audioCtx) { try { this._audioCtx.close(); } catch {} this._audioCtx = null; this._analyser = null; }
    try { this.mediaRecorder?.stop(); } catch { /* already stopped */ }
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
    this.mediaRecorder = null;
    this.chunks = [];
    if (this.onLevel) this.onLevel(0);
  }
}

export async function blobToWav(blob, targetRate = 16000) {
  const arrayBuffer = await blob.arrayBuffer();
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  const ctx = new AudioCtx();
  let decoded;
  try {
    decoded = await ctx.decodeAudioData(arrayBuffer.slice(0));
  } finally {
    ctx.close();
  }

  const frames = Math.max(1, Math.ceil(decoded.duration * targetRate));
  const offline = new OfflineAudioContext(1, frames, targetRate);
  const source = offline.createBufferSource();
  source.buffer = decoded;
  source.connect(offline.destination);
  source.start(0);
  const rendered = await offline.startRendering();
  const samples = rendered.getChannelData(0);

  // Silence trimming: find first/last sample above threshold, add padding.
  const trimmed = trimSilence(samples, targetRate);
  return encodeWav(trimmed, targetRate);
}

function trimSilence(samples, sampleRate, threshold = 0.012, padSeconds = 0.15) {
  if (samples.length === 0) return samples;
  const pad = Math.floor(sampleRate * padSeconds);
  let first = 0;
  let last = samples.length - 1;
  // find first
  for (let i = 0; i < samples.length; i += 1) {
    if (Math.abs(samples[i]) > threshold) { first = Math.max(0, i - pad); break; }
    if (i === samples.length - 1) return samples; // all silence, keep as-is
  }
  // find last
  for (let i = samples.length - 1; i >= 0; i -= 1) {
    if (Math.abs(samples[i]) > threshold) { last = Math.min(samples.length - 1, i + pad); break; }
  }
  if (last <= first) return samples;
  return samples.slice(first, last + 1);
}

function encodeWav(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(view, 8, 'WAVE');
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(view, 36, 'data');
  view.setUint32(40, samples.length * 2, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
    offset += 2;
  }

  return new Blob([view], { type: 'audio/wav' });
}

function writeString(view, offset, text) {
  for (let i = 0; i < text.length; i += 1) {
    view.setUint8(offset + i, text.charCodeAt(i));
  }
}

let cachedVoice = null;

export function speak(text, lang = 'hi-IN') {
  if (!text || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  const voices = window.speechSynthesis.getVoices();
  cachedVoice = cachedVoice || voices.find((v) => v.lang?.toLowerCase().startsWith('hi'))
    || voices.find((v) => v.lang?.toLowerCase().startsWith('en-in'))
    || voices[0];
  if (cachedVoice) utterance.voice = cachedVoice;
  utterance.lang = lang;
  utterance.rate = 1.0;
  utterance.pitch = 1.0;
  window.speechSynthesis.speak(utterance);
}

export function stopSpeaking() {
  window.speechSynthesis?.cancel();
}
