/**
 * tracker.js — Carby Control
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

// ── Highlight selected pill & Handle category change ──────────────────────────
const amountInput = document.getElementById('amount');
const manualToggle = document.getElementById('manualToggle');

function getActiveCategoryId() {
  const checked = document.querySelector('input[name="category_id"]:checked');
  return checked ? checked.value : null;
}

function calculateCO2() {
  // If manual entry is toggled, do not overwrite the amount
  if (manualToggle && manualToggle.checked) return;
  
  const catId = getActiveCategoryId();
  let co2 = 0;
  
  if (catId == '1') {
    // Transport
    const multiplier = parseFloat(document.getElementById('transportMode').value) || 0;
    const distance = parseFloat(document.getElementById('transportDistance').value) || 0;
    co2 = multiplier * distance;
  } else if (catId == '2') {
    // Energy
    const usage = parseFloat(document.getElementById('energyUsage').value) || 0;
    co2 = usage * 0.23;
  } else if (catId == '3') {
    // Food
    const multiplier = parseFloat(document.getElementById('foodType').value) || 0;
    const meals = parseFloat(document.getElementById('foodMeals').value) || 0;
    co2 = multiplier * meals;
  } else if (catId == '4') {
    // Shopping
    const spend = parseFloat(document.getElementById('shoppingAmount').value) || 0;
    co2 = spend * 0.03; // 0.3 per 10
  } else if (catId == '5') {
    // Waste
    const bags = parseFloat(document.getElementById('wasteBags').value) || 0;
    co2 = bags * 1.5;
  }
  
  if (amountInput) {
    amountInput.value = co2 > 0 ? co2.toFixed(3) : '';
  }
}

document.querySelectorAll('.pill-label input').forEach(radio => {
  radio.addEventListener('change', () => {
    // Styling the pills
    document.querySelectorAll('.pill').forEach(p => p.classList.remove('selected'));
    if (radio.checked) {
      radio.nextElementSibling.classList.add('selected');
    }
    
    // Switch the dynamic input groups
    document.querySelectorAll('.calc-group').forEach(group => {
      group.style.display = 'none';
    });
    const targetGroup = document.getElementById('inputGroup_' + radio.value);
    if (targetGroup) {
      targetGroup.style.display = 'block';
    }
    
    // Trigger calculation
    calculateCO2();
  });
});

// Initialize on load
const initCat = getActiveCategoryId();
if (initCat) {
  const targetGroup = document.getElementById('inputGroup_' + initCat);
  if (targetGroup) targetGroup.style.display = 'block';
}

// ── Listen to input changes for calculations ────────────────────────────────
document.querySelectorAll('.calc-trigger, #transportMode, #foodType').forEach(el => {
  el.addEventListener('input', calculateCO2);
  el.addEventListener('change', calculateCO2);
});

// ── Manual Toggle logic ──────────────────────────────────────────────────────
if (manualToggle && amountInput) {
  manualToggle.addEventListener('change', () => {
    if (manualToggle.checked) {
      amountInput.readOnly = false;
      amountInput.style.backgroundColor = '#ffffff';
      amountInput.focus();
    } else {
      amountInput.readOnly = true;
      amountInput.style.backgroundColor = '#e2e8f0';
      calculateCO2(); // Recalculate based on existing inputs
    }
  });
}

// ── Form submit button feedback ──────────────────────────────────────────────
const trackerForm = document.getElementById('trackerForm');
if (trackerForm) {
  trackerForm.addEventListener('submit', (e) => {
    const btn = trackerForm.querySelector('button[type="submit"]');
    if (btn && trackerForm.checkValidity()) {
      btn.disabled = true;
      btn.replaceChildren();
      const icon = document.createElement('span');
      icon.className = 'material-icons-round';
      icon.textContent = 'hourglass_empty';
      btn.append(icon, document.createTextNode(' Logging…'));
    }
  });
}
