/**
 * auth.js — Carby Control
 * Login & Register page interactions
 */

// ── Password visibility toggle ──────────────────────────────────────────────
function togglePassword(inputId, btn) {
  const input = document.getElementById(inputId);
  const icon  = btn.querySelector('.material-icons-round');
  if (input.type === 'password') {
    input.type = 'text';
    icon.textContent = 'visibility_off';
  } else {
    input.type = 'password';
    icon.textContent = 'visibility';
  }
}

// ── Password strength meter (register page) ─────────────────────────────────
const passwordInput = document.getElementById('password');
const strengthFill  = document.getElementById('strengthFill');
const strengthLabel = document.getElementById('strengthLabel');

if (passwordInput && strengthFill) {
  passwordInput.addEventListener('input', () => {
    const val = passwordInput.value;
    const score = calcStrength(val);
    const configs = [
      { pct: '0%',   color: '',        label: '' },
      { pct: '25%',  color: '#f87171', label: 'Weak' },
      { pct: '50%',  color: '#fb923c', label: 'Fair' },
      { pct: '75%',  color: '#facc15', label: 'Good' },
      { pct: '100%', color: '#4ade80', label: 'Strong' },
    ];
    const cfg = configs[score];
    strengthFill.style.width = cfg.pct;
    strengthFill.style.background = cfg.color;
    if (strengthLabel) {
      strengthLabel.textContent = cfg.label;
      strengthLabel.style.color = cfg.color;
    }
  });
}

function calcStrength(pw) {
  if (!pw) return 0;
  let score = 0;
  if (pw.length >= 6)  score++;
  if (pw.length >= 10) score++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
  if (/\d/.test(pw) && /[^A-Za-z0-9]/.test(pw)) score++;
  return Math.min(score, 4);
}

// ── Real-time password match validation (register page) ─────────────────────
const confirmInput = document.getElementById('confirm_password');
if (confirmInput && passwordInput) {
  confirmInput.addEventListener('input', () => {
    if (confirmInput.value && confirmInput.value !== passwordInput.value) {
      confirmInput.style.borderColor = '#f87171';
    } else {
      confirmInput.style.borderColor = '';
    }
  });
}

// ── Form submission feedback ─────────────────────────────────────────────────
const forms = document.querySelectorAll('#loginForm, #registerForm');
forms.forEach(form => {
  form.addEventListener('submit', (e) => {
    const btn = form.querySelector('button[type="submit"]');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="material-icons-round" style="animation:spin 0.8s linear infinite">refresh</span> Please wait…';
    }
  });
});
