/**
 * report.js — Carby Control
 * Reports page: build download URLs from date filter inputs
 */

function downloadReport(type) {
  const start = document.getElementById('start_date').value;
  const end   = document.getElementById('end_date').value;

  let url = `/reports/download/${type}`;
  const params = new URLSearchParams();
  if (start) params.append('start_date', start);
  if (end)   params.append('end_date',   end);
  if (params.toString()) url += '?' + params.toString();

  // Visual feedback on the button
  const btn = document.getElementById(type + 'Btn');
  if (btn) {
    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="material-icons-round">hourglass_empty</span> Preparing…';
    setTimeout(() => {
      btn.disabled = false;
      btn.innerHTML = originalHTML;
    }, 3000);
  }

  // Trigger download
  window.location.href = url;
}

// ── Date range validation ─────────────────────────────────────────────────────
const startInput = document.getElementById('start_date');
const endInput   = document.getElementById('end_date');

if (startInput && endInput) {
  // Set max date to today
  const today = new Date().toISOString().split('T')[0];
  startInput.max = today;
  endInput.max   = today;

  startInput.addEventListener('change', () => {
    if (startInput.value) {
      endInput.min = startInput.value;
    }
  });

  endInput.addEventListener('change', () => {
    if (endInput.value && startInput.value && endInput.value < startInput.value) {
      endInput.value = startInput.value;
    }
  });
}
