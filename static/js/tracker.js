/**
 * tracker.js — EcoTrack
 * Emission Tracker page interactions
 */

// ── Animate log rows on page load ────────────────────────────────────────────
document.querySelectorAll('.log-row').forEach((row, i) => {
  row.style.opacity = '0';
  row.style.transform = 'translateX(20px)';
  row.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
  setTimeout(() => {
    row.style.opacity = '1';
    row.style.transform = 'translateX(0)';
  }, 60 + i * 40);
});

// ── Live preview of entered amount ───────────────────────────────────────────
const amountInput = document.getElementById('amount');
if (amountInput) {
  amountInput.addEventListener('input', () => {
    const val = parseFloat(amountInput.value);
    // Equivalent to driving km (avg 0.21 kg/km)
    const equiv = val ? (val / 0.21).toFixed(1) : 0;
    let hint = document.getElementById('amountHint');
    if (!hint) {
      hint = document.createElement('div');
      hint.id = 'amountHint';
      hint.style.cssText = 'font-size:11px;color:#94a3b8;margin-top:4px;';
      amountInput.closest('.form-group').appendChild(hint);
    }
    if (val > 0) {
      hint.textContent = `≈ equivalent to driving ${equiv} km by car`;
    } else {
      hint.textContent = '';
    }
  });
}

// ── Highlight selected pill ──────────────────────────────────────────────────
document.querySelectorAll('.pill-label input').forEach(radio => {
  radio.addEventListener('change', () => {
    document.querySelectorAll('.pill').forEach(p => p.classList.remove('selected'));
    if (radio.checked) {
      radio.nextElementSibling.classList.add('selected');
    }
  });
});

// ── Form submit button feedback ──────────────────────────────────────────────
const trackerForm = document.getElementById('trackerForm');
if (trackerForm) {
  trackerForm.addEventListener('submit', (e) => {
    const btn = trackerForm.querySelector('button[type="submit"]');
    if (btn && trackerForm.checkValidity()) {
      btn.disabled = true;
      btn.innerHTML = '<span class="material-icons-round">hourglass_empty</span> Logging…';
    }
  });
}
