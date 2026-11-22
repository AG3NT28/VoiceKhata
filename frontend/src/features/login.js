import { clearToken, getToken, loginWithEmail, setToken } from '../services/api.js';

const EMAIL_KEY = 'voicekhata.shopEmail';
const LANG_KEY = 'voiceKhata.language';

export const LANG_CHIPS = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिन्दी' },
  { code: 'te', label: 'తెలుగు' },
  { code: 'kn', label: 'ಕನ್ನಡ' },
  { code: 'ta', label: 'தமிழ்' },
  { code: 'or', label: 'ଓଡ଼ିଆ' },
  { code: 'ml', label: 'മലയാളം' },
  { code: 'bn', label: 'বাংলা' },
  { code: 'mr', label: 'मराठी' },
];

function welcomeKeyFor(email) {
  return `voicekhata.welcomeSeen:${String(email || '').trim().toLowerCase()}`;
}

export function shouldShowWelcome(email) {
  if (!email) return true;
  return localStorage.getItem(welcomeKeyFor(email)) !== '1';
}

export function markWelcomeSeen(email) {
  if (!email) return;
  localStorage.setItem(welcomeKeyFor(email), '1');
}

export function clearWelcomeSeen(email) {
  if (!email) return;
  localStorage.removeItem(welcomeKeyFor(email));
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

function langGridHtml(initialLanguage) {
  return LANG_CHIPS.map(
    (chip) =>
      `<button type="button" class="welcome-lang-btn" data-language="${chip.code}" aria-pressed="${chip.code === initialLanguage}">${chip.label}</button>`,
  ).join('');
}

function wireLanguagePicker(root, { initialLanguage, onLanguage }) {
  let selected = initialLanguage;
  const buttons = () => root.querySelectorAll('.welcome-lang-btn');
  buttons().forEach((btn) => {
    btn.addEventListener('click', () => {
      selected = btn.dataset.language;
      buttons().forEach((b) => {
        b.setAttribute('aria-pressed', String(b.dataset.language === selected));
      });
      try {
        localStorage.setItem(LANG_KEY, selected);
      } catch {}
      onLanguage?.(selected);
    });
  });
  return {
    get selected() {
      return selected;
    },
  };
}

function finishLanguage(overlay, { email, shopReset, isNewSession, language, onLanguage, resolve }) {
  markWelcomeSeen(email);
  try {
    localStorage.setItem(LANG_KEY, language);
  } catch {}
  onLanguage?.(language);
  overlay.classList.add('welcome-exit');
  setTimeout(() => overlay.remove(), 280);
  resolve({ email, shopReset, isNewSession, language });
}

/**
 * Email login, then language pick (fixes post-login language UX).
 * Server resets shared shop data when the email changes.
 */
export async function mountAuthGate({ root, initialLanguage = 'en', onLanguage } = {}) {
  const host = root || document.body;
  const savedEmail = getShopEmail();

  // Returning session: keep shop data, skip overlays
  if (savedEmail && getToken() && !shouldShowWelcome(savedEmail)) {
    return { email: savedEmail, shopReset: false, isNewSession: false };
  }

  if (savedEmail && getToken() && shouldShowWelcome(savedEmail)) {
    return showLanguageStep(host, {
      email: savedEmail,
      initialLanguage,
      onLanguage,
      shopReset: false,
      isNewSession: false,
    });
  }

  return new Promise((resolve) => {
    const overlay = document.createElement('div');
    overlay.id = 'authOverlay';
    overlay.className = 'auth-overlay';
    overlay.innerHTML = `
      <div class="auth-card" role="dialog" aria-labelledby="authTitle" aria-modal="true">
        <p class="welcome-eyebrow">VoiceKhata</p>
        <div id="authStepEmail">
          <h1 id="authTitle" class="welcome-title">Shop login</h1>
          <p class="welcome-sub">Enter shop email — no password. A new email starts a fresh shop.</p>
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
        <div id="authStepLanguage" hidden>
          <h1 id="langTitle" class="welcome-title">Choose language</h1>
          <p class="welcome-sub">You can change this anytime in Profile</p>
          <div class="welcome-lang-grid" role="group" aria-label="Languages">
            ${langGridHtml(initialLanguage)}
          </div>
          <p id="langNotice" class="form-notice" role="status" aria-live="polite" hidden></p>
          <div class="auth-actions">
            <button type="button" id="langContinue" class="welcome-enter">Enter shop</button>
          </div>
        </div>
      </div>
    `;
    host.append(overlay);

    const notice = overlay.querySelector('#authNotice');
    const form = overlay.querySelector('#authForm');
    const emailInput = overlay.querySelector('#authEmail');
    const continueBtn = overlay.querySelector('#authContinue');
    const stepEmail = overlay.querySelector('#authStepEmail');
    const stepLang = overlay.querySelector('#authStepLanguage');
    const langContinue = overlay.querySelector('#langContinue');
    if (savedEmail) emailInput.value = savedEmail;

    const picker = wireLanguagePicker(stepLang, { initialLanguage, onLanguage });

    function setAuthNotice(message, isError = true) {
      notice.textContent = message || '';
      notice.hidden = !message;
      notice.classList.toggle('error', Boolean(isError && message));
    }

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      continueBtn.disabled = true;
      setAuthNotice('');
      const email = emailInput.value.trim().toLowerCase();
      try {
        // Server decides reset when email differs from last active shop email
        const data = await loginWithEmail(email);
        setToken(data.access_token);
        setShopEmail(data.email || email);
        const shopReset = Boolean(data.shop_reset);
        if (shopReset) {
          clearWelcomeSeen(data.email || email);
          setAuthNotice('Fresh shop ready for this email.', false);
        }
        stepEmail.hidden = true;
        stepLang.hidden = false;
        overlay.querySelector('#authTitle')?.removeAttribute('id');
        langContinue.focus();
        langContinue.onclick = () => {
          finishLanguage(overlay, {
            email: data.email || email,
            shopReset,
            isNewSession: true,
            language: picker.selected,
            onLanguage,
            resolve,
          });
        };
      } catch (err) {
        setAuthNotice(err.message || 'Could not sign in');
        continueBtn.disabled = false;
      }
    });

    emailInput.focus();
  });
}

function showLanguageStep(host, { email, initialLanguage, onLanguage, shopReset, isNewSession }) {
  return new Promise((resolve) => {
    const overlay = document.createElement('div');
    overlay.id = 'authOverlay';
    overlay.className = 'auth-overlay';
    overlay.innerHTML = `
      <div class="auth-card" role="dialog" aria-labelledby="langTitle" aria-modal="true">
        <p class="welcome-eyebrow">VoiceKhata</p>
        <h1 id="langTitle" class="welcome-title">Choose language</h1>
        <p class="welcome-sub">You can change this anytime in Profile</p>
        <div class="welcome-lang-grid" role="group" aria-label="Languages">
          ${langGridHtml(initialLanguage)}
        </div>
        <div class="auth-actions">
          <button type="button" id="langContinue" class="welcome-enter">Enter shop</button>
        </div>
      </div>
    `;
    host.append(overlay);
    const picker = wireLanguagePicker(overlay, { initialLanguage, onLanguage });
    const langContinue = overlay.querySelector('#langContinue');
    langContinue.addEventListener('click', () => {
      finishLanguage(overlay, {
        email,
        shopReset,
        isNewSession: Boolean(isNewSession),
        language: picker.selected,
        onLanguage,
        resolve,
      });
    });
    langContinue.focus();
  });
}

/** @deprecated use mountAuthGate language step */
export function mountWelcome() {
  return null;
}
