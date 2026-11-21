const API_BASE = import.meta.env.VITE_API_BASE || '';
const TOKEN_KEY = 'voicekhata.token';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || '';
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function toJson(response) {
  const contentType = response.headers.get('content-type') || '';
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      if (contentType.includes('application/json')) {
        const body = await response.json();
        detail = body.detail || body.message || detail;
        if (Array.isArray(detail)) {
          detail = detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
        }
      } else {
        const text = await response.text();
        if (text.trimStart().startsWith('<!DOCTYPE') || text.trimStart().startsWith('<html')) {
          detail = `API returned HTML instead of JSON (${response.url || 'request'}). Check Vite proxy / backend.`;
        }
      }
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  if (!contentType.includes('application/json')) {
    const text = await response.text();
    if (text.trimStart().startsWith('<!DOCTYPE') || text.trimStart().startsWith('<html')) {
      throw new Error('API returned HTML instead of JSON. Is the backend running and proxied?');
    }
    try {
      return JSON.parse(text);
    } catch {
      throw new Error('API returned a non-JSON response');
    }
  }
  return response.json();
}

function authHeaders(extra = {}) {
  const headers = { ...extra };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

async function apiFetch(path, options = {}) {
  const headers = authHeaders(options.headers || {});
  try {
    const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
    return await toJson(response);
  } catch (err) {
    if (err instanceof TypeError || /failed to fetch/i.test(err.message || '')) {
      throw new Error('Cannot reach server. Is the backend running on port 8000?');
    }
    throw err;
  }
}

/** Exchange a Supabase access token for the shared demo-shop VoiceKhata JWT. */
export async function exchangeSupabaseToken(supabaseAccessToken) {
  return fetch(`${API_BASE}/auth/supabase`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${supabaseAccessToken}` },
  }).then(toJson);
}

/** Passwordless shop login — email only. reset=true wipes shop data for a new email. */
export function loginWithEmail(email, { reset = false } = {}) {
  return apiFetch('/auth/email', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: String(email || '').trim(), reset: Boolean(reset) }),
  });
}

/**
 * Ensure we have a demo-shop JWT.
 * Prefers stored shop email (passwordless); falls back to /auth/demo in ALLOW_DEMO_AUTH mode.
 */
export async function ensureAuth() {
  if (getToken()) return getToken();
  let email = '';
  try {
    email = localStorage.getItem('voicekhata.shopEmail') || '';
  } catch {
    email = '';
  }
  if (email) {
    const data = await loginWithEmail(email);
    setToken(data.access_token);
    return data.access_token;
  }
  const data = await apiFetch('/auth/demo', { method: 'POST' });
  setToken(data.access_token);
  return data.access_token;
}

export function getState() {
  return apiFetch('/voice/state');
}

export function sendAudio(wavBlob, languageCode = 'hi-IN,en-IN') {
  const form = new FormData();
  form.append('audio', wavBlob, 'audio.wav');
  form.append('language_code', languageCode);
  return fetch(`${API_BASE}/voice/command`, {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  }).then(toJson);
}

export function sendText(text) {
  return apiFetch('/voice/text', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
}

export function undoLast() {
  return apiFetch('/voice/undo', { method: 'POST' });
}

export async function speakText(text, language = 'hi-en') {
  const res = await fetch(`${API_BASE}/voice/speak`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ text, language }),
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const b = await res.json();
      detail = b.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  audio.onended = () => URL.revokeObjectURL(url);
  await audio.play();
  return audio;
}

export function listCustomers(q = '') {
  const query = q ? `?q=${encodeURIComponent(q)}&status=active` : '?status=active';
  return apiFetch(`/customers${query}`);
}

export function createCustomer({ name, phone }) {
  return apiFetch('/customers', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, phone: phone || null }),
  });
}

export function updateCustomer(id, payload) {
  return apiFetch(`/customers/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/** Soft-delete: archive so the customer leaves the active list. */
export function archiveCustomer(id) {
  return updateCustomer(id, { status: 'archived' });
}

export function getCustomerByCode(code) {
  return apiFetch(`/customers/by-code/${encodeURIComponent(String(code).trim().toUpperCase())}`);
}

export function getBalance(customerId) {
  return apiFetch(`/customers/${customerId}/balance`);
}

export function createTransaction({
  customerId,
  type,
  amountRupees,
  txnDate,
  idempotencyKey,
}) {
  return apiFetch('/transactions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {}),
    },
    body: JSON.stringify({
      customer_id: customerId,
      type,
      amount_rupees: amountRupees,
      txn_date: txnDate || undefined,
      idempotency_key: idempotencyKey,
    }),
  });
}

export function getDailyReport(date) {
  const query = date ? `?date=${encodeURIComponent(date)}` : '';
  return apiFetch(`/reports/daily${query}`);
}

export async function healthCheck() {
  return apiFetch('/health');
}

export function listInventory(q = '', lowStockOnly = false) {
  const params = new URLSearchParams();
  if (q) params.set('q', q);
  if (lowStockOnly) params.set('low_stock_only', 'true');
  const qs = params.toString();
  return apiFetch(`/inventory${qs ? `?${qs}` : ''}`);
}

export function createInventoryItem(payload) {
  return apiFetch('/inventory', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function updateInventoryItem(id, payload) {
  return apiFetch(`/inventory/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function getItemQuotes(itemId) {
  return apiFetch(`/inventory/${itemId}/quotes`);
}

export function getLowStockSummary() {
  return apiFetch('/inventory/low-stock/summary');
}

/** Canonical stock API (SQLite items + stock_logs). */
export function listStock({ category = '', search = '' } = {}) {
  const params = new URLSearchParams();
  if (category) params.set('category', category);
  if (search) params.set('search', search);
  const qs = params.toString();
  return apiFetch(`/stock${qs ? `?${qs}` : ''}`);
}

export function getStockSummary() {
  return apiFetch('/stock/summary');
}

export function createStockItem(payload) {
  return apiFetch('/stock', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function getStockItem(id) {
  return apiFetch(`/stock/${id}`);
}

export function getStockLog(id) {
  return apiFetch(`/stock/${id}/log`);
}

export function addStock(id, quantity, reason = 'restock') {
  return apiFetch(`/stock/${id}/add`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ quantity, reason }),
  });
}

export function removeStock(id, quantity, reason = 'sold') {
  return apiFetch(`/stock/${id}/remove`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ quantity, reason }),
  });
}

export function adjustStock(id, delta, reason = 'adjust') {
  return apiFetch(`/stock/${id}/adjust`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ delta, reason }),
  });
}

export function listTransactions(customerId, limit = 20) {
  return apiFetch(`/transactions?customer_id=${encodeURIComponent(customerId)}&limit=${limit}`);
}

/** B2B marketplace intelligence */
export function marketplaceSearch(query, { purchaseType = 'wholesale', providers } = {}) {
  return apiFetch('/api/marketplace/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      purchase_type: purchaseType,
      providers: providers || null,
    }),
  });
}

export function marketplaceProviders() {
  return apiFetch('/api/marketplace/providers');
}

export function marketplaceRedirect(offerId) {
  return apiFetch(`/api/marketplace/redirect/${offerId}`, { method: 'POST' });
}

export function marketplaceHistory() {
  return apiFetch('/api/marketplace/history');
}

export function marketplaceImport(file, supplierName = 'Imported Supplier') {
  const form = new FormData();
  form.append('file', file);
  form.append('supplier_name', supplierName);
  return fetch(`${API_BASE}/api/marketplace/suppliers/import`, {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  }).then(toJson);
}

export function marketplaceCompare(offerIds) {
  return apiFetch('/api/marketplace/compare', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ offer_ids: offerIds }),
  });
}

export function marketplaceStars() {
  return apiFetch('/api/marketplace/stars');
}

export function marketplaceStar(offerId) {
  return apiFetch(`/api/marketplace/stars/${offerId}`, { method: 'POST' });
}

export function marketplaceUnstar(offerId) {
  return apiFetch(`/api/marketplace/stars/${offerId}`, { method: 'DELETE' });
}
