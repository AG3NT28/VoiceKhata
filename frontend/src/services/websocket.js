/**
 * WebSocket client for the /ws/voice channel.
 *
 * Protocol:
 *   Server -> { type: "ready" }
 *   Client -> binary audio (WAV)  OR  JSON { text: "..." }
 *   Server -> { type: "result", ...commandResult, stt: {...} }
 *   Server -> { type: "error", message: "..." }
 */
export class VoiceSocket {
  constructor(url) {
    const apiBase = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '');
    this.url = url || (apiBase
      ? `${apiBase.replace(/^http/, 'ws')}/ws/voice`
      : `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/voice`);
    this.ws = null;
    this.resultHandlers = [];
    this.errorHandlers = [];
    this.readyHandlers = [];
    this._reconnectTimer = null;
    this._intentionalClose = false;
  }

  connect() {
    this._intentionalClose = false;
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);
        this.ws.binaryType = 'arraybuffer';
      } catch (err) {
        reject(err);
        return;
      }
      const onOpen = () => {
        // wait for ready message
      };
      this.ws.onopen = onOpen;
      this.ws.onmessage = (event) => {
        let msg;
        try { msg = JSON.parse(event.data); } catch { return; }
        if (msg.type === 'ready') {
          this.readyHandlers.forEach((h) => h(msg));
          resolve(this);
        } else if (msg.type === 'result') {
          this.resultHandlers.forEach((h) => h(msg));
        } else if (msg.type === 'error') {
          this.errorHandlers.forEach((h) => h(msg));
        }
      };
      this.ws.onerror = (err) => { reject(err); };
      this.ws.onclose = () => {
        this.ws = null;
        if (this._intentionalClose) return;
        // auto-reconnect after 3s
        this._reconnectTimer = setTimeout(() => this.connect().catch(() => {}), 3000);
      };
    });
  }

  sendAudio(blob) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }
    // send as binary
    blob.arrayBuffer().then((buf) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) this.ws.send(buf);
    });
  }

  sendText(text) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }
    this.ws.send(JSON.stringify({ text }));
  }

  onResult(handler) { this.resultHandlers.push(handler); return () => { this.resultHandlers = this.resultHandlers.filter((h) => h !== handler); }; }
  onError(handler) { this.errorHandlers.push(handler); return () => { this.errorHandlers = this.errorHandlers.filter((h) => h !== handler); }; }
  onReady(handler) { this.readyHandlers.push(handler); return () => { this.readyHandlers = this.readyHandlers.filter((h) => h !== handler); }; }

  close() {
    this._intentionalClose = true;
    if (this._reconnectTimer) clearTimeout(this._reconnectTimer);
    this._reconnectTimer = null;
    if (this.ws) { try { this.ws.close(); } catch {} this.ws = null; }
  }

  get connected() {
    return !!this.ws && this.ws.readyState === WebSocket.OPEN;
  }
}

let singleton = null;
export function getSocket() {
  if (!singleton) singleton = new VoiceSocket();
  return singleton;
}
