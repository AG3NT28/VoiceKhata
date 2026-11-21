import { clearToken, getToken, loginWithEmail, setToken } from '../services/api.js';

const SEEN_KEY = 'voicekhata.welcomeSeen';
const EMAIL_KEY = 'voicekhata.shopEmail';

const LANG_CHIPS = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिन्दी' },
  { code: 'te', label: 'తెలుగు' },
  { code: 'ta', label: 'தமிழ்' },
  { code: 'or', label: 'ଓଡ଼ିଆ' },
  { code: 'ml', label: 'മലയാളം' },
  { code: 'bn', label: 'বাংলা' },
  { code: 'mr', label: 'मराठी' },
];

export function shouldShowWelcome() {
  return localStorage.getItem(SEEN_KEY) !== '1';
}

export function markWelcomeSeen() {
  localStorage.setItem(SEEN_KEY, '1');
}

export function getShopEmail() {
  return localStorage.getItem(EMAIL_KEY) || '';
}

export function setShopEmail(email) {
  const value = String(email || '').trim().toLowerCase();
  if (value) localStorage.setItem(EMAIL_KEY, value);
  else localStorage.removeItem(EMAIL_KEY);
}

export function clearShopSession() {
  clearToken();
  localStorage.removeItem(EMAIL_KEY);
}

/**
 * Email-only gate (no password). Issues demo-shop JWT via POST /auth/email.
 */
export async function mountAuthGate({ root } = {}) {
  const host = root || document.body;
  const savedEmail = getShopEmail();
  if (savedEmail && getToken()) {
    return { email: savedEmail };
  }
  if (savedEmail) {
    try {
      const data = await loginWithEmail(savedEmail);
      setToken(data.access_token);
      setShopEmail(data.email || savedEmail);
      return { email: data.email || savedEmail };
    } catch {
      clearToken();
    }
  }

  return new Promise((resolve) => {
    const overlay = document.createElement('div');
    overlay.id = 'authOverlay';
    overlay.className = 'auth-overlay';
    overlay.innerHTML = `
      <div class="auth-card" role="dialog" aria-labelledby="authTitle">
        <p class="welcome-eyebrow">VoiceKhata</p>
        <h1 id="authTitle" class="welcome-title">Shop login</h1>
        <p class="welcome-sub">Enter your shop email — no password needed</p>
        <form id="authForm" class="auth-form">
          <label class="auth-field">
            <span>Shop email</span>
            <input id="authEmail" type="email" autocomplete="email" required placeholder="shop@example.com" />
          </label>
          <p id="authNotice" class="form-notice" role="status" aria-live="polite" hidden></p>
          <div class="auth-actions">
            <button type="submit" id="authContinue" class="welcome-enter">Continue</button>
          </div>
        </form>
      </div>
    `;
    host.append(overlay);

    const notice = overlay.querySelector('#authNotice');
    const form = overlay.querySelector('#authForm');
    const emailInput = overlay.querySelector('#authEmail');
    const continueBtn = overlay.querySelector('#authContinue');
    if (savedEmail) emailInput.value = savedEmail;

    function setAuthNotice(message, isError = true) {
      notice.textContent = message || '';
      notice.hidden = !message;
      notice.classList.toggle('error', Boolean(isError && message));
    }

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      continueBtn.disabled = true;
      setAuthNotice('');
      try {
        const data = await loginWithEmail(emailInput.value);
        setToken(data.access_token);
        setShopEmail(data.email || emailInput.value);
        overlay.classList.add('welcome-exit');
        setTimeout(() => overlay.remove(), 280);
        resolve({ email: data.email || emailInput.value.trim().toLowerCase() });
      } catch (err) {
        setAuthNotice(err.message || 'Could not sign in');
        continueBtn.disabled = false;
      }
    });

    emailInput.focus();
  });
}

/**
 * Mount a one-time welcome overlay with rotating language chips.
 * onContinue(languageCode) is called when the user enters the app.
 */
export function mountWelcome({ root, onContinue, initialLanguage = 'en' }) {
  if (!root || !shouldShowWelcome()) return null;

  const overlay = document.createElement('div');
  overlay.id = 'welcomeOverlay';
  overlay.className = 'welcome-overlay';
  overlay.innerHTML = `
    <div class="welcome-card" role="dialog" aria-labelledby="welcomeTitle">
      <p class="welcome-eyebrow">VoiceKhata</p>
      <h1 id="welcomeTitle" class="welcome-title">Bolke khata</h1>
      <p class="welcome-sub">Pick a language — switch anytime in Profile</p>
      <div class="welcome-orbit" aria-hidden="true">
        ${LANG_CHIPS.map((chip, i) =>
          `<span class="welcome-chip" style="--i:${i}">${chip.label}</span>`,
        ).join('')}
      </div>
      <div class="welcome-lang-grid" role="group" aria-label="Languages">
        ${LANG_CHIPS.map(
          (chip) =>
            `<button type="button" class="welcome-lang-btn" data-language="${chip.code}" aria-pressed="${chip.code === initialLanguage}">${chip.label}</button>`,
        ).join('')}
      </div>
      <button type="button" class="welcome-enter" id="welcomeEnter">Enter shop</button>
    </div>
  `;
  root.append(overlay);

  let selected = initialLanguage;
  overlay.querySelectorAll('.welcome-lang-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      selected = btn.dataset.language;
      overlay.querySelectorAll('.welcome-lang-btn').forEach((b) => {
        b.setAttribute('aria-pressed', String(b.dataset.language === selected));
      });
    });
  });

  overlay.querySelector('#welcomeEnter').addEventListener('click', () => {
    markWelcomeSeen();
    overlay.classList.add('welcome-exit');
    setTimeout(() => overlay.remove(), 320);
    onContinue?.(selected);
  });

  return overlay;
}
