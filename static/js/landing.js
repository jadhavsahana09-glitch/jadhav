/* ═══════════════════════════════════════════════════════════════
   Carby Control — Enhanced Landing Page JS
   Features: Sliders + numbers sync, real-time mini bar chart,
   AI suggestion engine, tips carousel, chatbot, mobile nav
   ═══════════════════════════════════════════════════════════════ */

// ── DOM References ─────────────────────────────────────────────
const demoInputs = {
  transport:   document.getElementById('demoTransport'),
  electricity: document.getElementById('demoElectricity'),
  food:        document.getElementById('demoFood'),
  shopping:    document.getElementById('demoShopping'),
};
const demoNums = {
  transport:   document.getElementById('demoTransportNum'),
  electricity: document.getElementById('demoElectricityNum'),
  food:        document.getElementById('demoFoodNum'),
  shopping:    document.getElementById('demoShoppingNum'),
};
const valLabels = {
  transport:   document.getElementById('transportVal'),
  electricity: document.getElementById('electricityVal'),
  food:        document.getElementById('foodVal'),
  shopping:    document.getElementById('shoppingVal'),
};

const demoTotal         = document.getElementById('demoTotal');
const aiSuggestion      = document.getElementById('aiSuggestion');
const treesNeeded       = document.getElementById('treesNeeded');
const creditsNeeded     = document.getElementById('creditsNeeded');
const landingGoalPct    = document.getElementById('landingGoalPct');
const landingGoalBar    = document.getElementById('landingGoalBar');
const aiMonthlyPred     = document.getElementById('aiMonthlyPred');
const offsetTreesLanding   = document.getElementById('offsetTreesLanding');
const offsetCreditsLanding = document.getElementById('offsetCreditsLanding');

// Emission factors (kg CO₂ per unit)
const factors = {
  transport:   0.21,   // per km
  electricity: 0.23,   // per kWh
  food:        3.1,    // per meat meal
  shopping:    0.03,   // per USD
};

// Unit labels for slider display
const unitLabels = {
  transport:   km  => `${km} km`,
  electricity: kwh => `${kwh} kWh`,
  food:        m   => `${m} meal${m !== '1' ? 's' : ''}`,
  shopping:    d   => `$${d}`,
};

let barChart, pieChart, trendChart, demoMiniChart;

// ── Sync Sliders ↔ Number inputs ────────────────────────────────
Object.keys(demoInputs).forEach(key => {
  const slider = demoInputs[key];
  const num    = demoNums[key];
  const label  = valLabels[key];
  if (!slider) return;

  slider.addEventListener('input', () => {
    if (num)   num.value = slider.value;
    if (label) label.textContent = unitLabels[key](slider.value);
    updateLandingDemo();
  });

  if (num) {
    num.addEventListener('input', () => {
      const v = Math.max(parseFloat(num.value) || 0, 0);
      slider.value = Math.min(v, parseFloat(slider.max));
      if (label) label.textContent = unitLabels[key](v);
      updateLandingDemo();
    });
  }
});

// ── Read current values ──────────────────────────────────────────
function readDemoValues() {
  return {
    transport:   Math.max(parseFloat(demoInputs.transport?.value)   || 0, 0) * factors.transport,
    electricity: Math.max(parseFloat(demoInputs.electricity?.value) || 0, 0) * factors.electricity,
    food:        Math.max(parseFloat(demoInputs.food?.value)        || 0, 0) * factors.food,
    shopping:    Math.max(parseFloat(demoInputs.shopping?.value)    || 0, 0) * factors.shopping,
  };
}

// ── AI Suggestion Engine ─────────────────────────────────────────
function buildSuggestion(values) {
  const entries = Object.entries(values).sort((a, b) => b[1] - a[1]);
  const [topCategory, topValue] = entries[0];
  const savings = Math.max(topValue * 8, 4).toFixed(1);
  const messages = {
    transport:   `🚗 Your transport emissions are highest today (${topValue.toFixed(2)} kg). Use public transport twice a week to save ~${savings} kg CO₂/month.`,
    electricity: `⚡ Electricity leads your footprint (${topValue.toFixed(2)} kg). Shift heavy appliance use to off-peak hours and switch to LEDs to save ~${savings} kg CO₂/month.`,
    food:        `🍖 Food is your top source today (${topValue.toFixed(2)} kg). Replacing a few meat meals with vegetarian alternatives saves ~${savings} kg CO₂/month.`,
    shopping:    `🛍️ Shopping leads your footprint (${topValue.toFixed(2)} kg). Choose durable or second-hand products to save ~${savings} kg CO₂/month.`,
  };
  return messages[topCategory] || messages.transport;
}

// ── Highlight top recommendation row ────────────────────────────
function highlightRecs(values) {
  const entries = Object.entries(values).sort((a, b) => b[1] - a[1]);
  const topKey = entries[0][0];
  ['transport', 'electricity', 'food', 'shopping'].forEach(k => {
    const row = document.getElementById(`rec-${k}`);
    if (row) row.style.background = (k === topKey) ? 'rgba(74,222,128,0.12)' : '';
  });
}

// ── Main update function ─────────────────────────────────────────
function updateLandingDemo() {
  const values = readDemoValues();
  const data   = [values.transport, values.electricity, values.food, values.shopping].map(v => Number(v.toFixed(2)));
  const total  = data.reduce((s, v) => s + v, 0);

  // Total display
  if (demoTotal) demoTotal.textContent = `${total.toFixed(2)} kg CO₂`;

  // AI suggestion
  if (aiSuggestion) aiSuggestion.textContent = buildSuggestion(values);
  highlightRecs(values);

  // Monthly prediction (simple linear × 30)
  const monthlyEst = (total * 30).toFixed(1);
  if (aiMonthlyPred) aiMonthlyPred.textContent = `≈ ${monthlyEst} kg CO₂/month`;

  // Offset calcs
  const trees   = Math.max(Math.ceil((total * 30) / 21), 1);
  const credits = (total / 1000).toFixed(3);
  if (treesNeeded)           treesNeeded.textContent   = trees;
  if (creditsNeeded)         creditsNeeded.textContent = credits;
  if (offsetTreesLanding)    offsetTreesLanding.textContent   = `${trees} tree${trees !== 1 ? 's' : ''}`;
  if (offsetCreditsLanding)  offsetCreditsLanding.textContent = `${credits} credits`;

  // Goal bar
  const goalProgress = Math.min(Math.round(100 - Math.min(total * 3, 55)), 95);
  if (landingGoalPct) landingGoalPct.textContent = `${goalProgress}%`;
  if (landingGoalBar) landingGoalBar.style.width = `${goalProgress}%`;

  // Update main charts
  if (barChart) { barChart.data.datasets[0].data = data; barChart.update(); }
  if (pieChart) { pieChart.data.datasets[0].data = data; pieChart.update(); }

  // Update mini bar chart
  if (demoMiniChart) { demoMiniChart.data.datasets[0].data = data; demoMiniChart.update(); }
}

// ── Initialize Charts ────────────────────────────────────────────
function initLandingCharts() {
  const chartColors = ['#1A759F', '#E9C46A', '#E76F51', '#40916C'];
  const values      = readDemoValues();
  const initialData = [values.transport, values.electricity, values.food, values.shopping].map(v => Number(v.toFixed(2)));

  const baseOpts = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: '#4A6741', boxWidth: 12, font: { size: 12 } } },
    },
    scales: {
      x: { ticks: { color: '#4A6741' }, grid: { display: false } },
      y: { ticks: { color: '#4A6741' }, grid: { color: 'rgba(45,106,79,0.12)' }, beginAtZero: true },
    },
  };

  // Mini demo bar chart (inside calculator panel)
  const miniCanvas = document.getElementById('demoBarChart');
  if (miniCanvas) {
    demoMiniChart = new Chart(miniCanvas, {
      type: 'bar',
      data: {
        labels: ['🚗 Transport', '⚡ Energy', '🍖 Food', '🛍️ Shop'],
        datasets: [{
          data: initialData,
          backgroundColor: chartColors.map(c => `${c}cc`),
          borderColor: chartColors,
          borderWidth: 2,
          borderRadius: 6,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: '#4A6741', font: { size: 11 } }, grid: { display: false } },
          y: { ticks: { color: '#4A6741', font: { size: 11 } }, beginAtZero: true, grid: { color: 'rgba(45,106,79,0.1)' } },
        },
      },
    });
  }

  // Main section bar chart
  const barCanvas = document.getElementById('landingBarChart');
  if (barCanvas) {
    barChart = new Chart(barCanvas, {
      type: 'bar',
      data: {
        labels: ['Transport', 'Electricity', 'Food', 'Shopping'],
        datasets: [{
          label: 'kg CO₂',
          data: initialData,
          backgroundColor: chartColors.map(c => `${c}cc`),
          borderColor: chartColors,
          borderWidth: 2,
          borderRadius: 6,
        }],
      },
      options: { ...baseOpts, plugins: { legend: { display: false } } },
    });
  }

  // Trend line chart (static demo data)
  const trendCanvas = document.getElementById('landingTrendChart');
  if (trendCanvas) {
    trendChart = new Chart(trendCanvas, {
      type: 'line',
      data: {
        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        datasets: [{
          label: 'kg CO₂',
          data: [142, 136, 124, 112, 104, 91],
          borderColor: '#2D6A4F',
          backgroundColor: 'rgba(45,106,79,0.12)',
          fill: true,
          tension: 0.35,
          pointBackgroundColor: '#2D6A4F',
        }],
      },
      options: baseOpts,
    });
  }

  // Doughnut pie chart
  const pieCanvas = document.getElementById('landingPieChart');
  if (pieCanvas) {
    pieChart = new Chart(pieCanvas, {
      type: 'doughnut',
      data: {
        labels: ['Transport', 'Electricity', 'Food', 'Shopping'],
        datasets: [{
          data: initialData,
          backgroundColor: chartColors.map(c => `${c}cc`),
          borderColor: '#ffffff',
          borderWidth: 3,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: '62%',
        plugins: { legend: { position: 'bottom', labels: { color: '#4A6741', boxWidth: 12, font: { size: 12 } } } },
      },
    });
  }
}

// ── Navbar scroll effect ─────────────────────────────────────────
window.addEventListener('scroll', () => {
  const nav = document.getElementById('landingNav');
  if (nav) nav.classList.toggle('nav-scrolled', window.scrollY > 60);
});

// ── Mobile Nav ───────────────────────────────────────────────────
function toggleMobileNav() {
  const drawer  = document.getElementById('mobileNavDrawer');
  const overlay = document.getElementById('mobileNavOverlay');
  const btn     = document.getElementById('navHamburger');
  if (!drawer) return;
  const open = drawer.classList.toggle('open');
  if (overlay) overlay.classList.toggle('open', open);
  if (btn) btn.innerHTML = open
    ? '<span class="material-icons-round">close</span>'
    : '<span class="material-icons-round">menu</span>';
}

// ── Educational Tips Carousel ────────────────────────────────────
let currentTip = 0;
const tips     = document.querySelectorAll('.edu-tip');
const tipDotsEl = document.getElementById('tipDots');

function buildTipDots() {
  if (!tipDotsEl) return;
  tipDotsEl.innerHTML = '';
  tips.forEach((_, i) => {
    const d = document.createElement('button');
    d.className = `tip-dot${i === 0 ? ' active' : ''}`;
    d.setAttribute('aria-label', `Tip ${i+1}`);
    d.onclick = () => goToTip(i);
    tipDotsEl.appendChild(d);
  });
}

function goToTip(idx) {
  tips.forEach(t => t.classList.remove('active'));
  if (tips[idx]) tips[idx].classList.add('active');
  currentTip = idx;
  const dots = document.querySelectorAll('.tip-dot');
  dots.forEach((d, i) => d.classList.toggle('active', i === idx));
}

function nextTip() { goToTip((currentTip + 1) % tips.length); }
function prevTip() { goToTip((currentTip - 1 + tips.length) % tips.length); }

// Auto-rotate tips every 5 seconds
buildTipDots();
let tipTimer = setInterval(nextTip, 5000);

// ── AI Chatbot ───────────────────────────────────────────────────
const chatbotResponses = {
  // Transport
  transport: "🚗 **Transport Tips:**\n• Take public transport 2–3 times/week — saves ~12 kg CO₂/month\n• Carpool for long commutes\n• Walk or cycle trips under 3 km\n• If you drive, maintain tyre pressure to improve fuel efficiency by 3%\n• Consider an EV for your next vehicle",

  car: "🚗 Cars are one of the biggest emission sources. Consider:\n• Carpooling: halves per-person emissions\n• Using buses/trains: 4–10× lower emissions per km\n• Maintaining your car: regular service improves fuel efficiency\n• Drive smoothly — aggressive acceleration burns 30% more fuel",

  electricity: "⚡ **Electricity Savings:**\n• Switch to LED bulbs — use 75% less energy than incandescent\n• Unplug standby devices — they consume 5–10% of home energy\n• Use appliances during off-peak hours\n• Set AC to 24–26°C instead of 18–20°C\n• Install solar panels if you own your home — payback in 4–6 years",

  energy: "⚡ **Energy Efficiency Tips:**\n• LED bulbs save ~300 kWh/year vs incandescent\n• A 5-star rated AC uses 50% less electricity than 1-star\n• Wash clothes in cold water — it's just as effective\n• Use a smart power strip to eliminate phantom loads",

  food: "🍖 **Food Footprint Reduction:**\n• 1 kg of beef = 27 kg CO₂; chicken = 6 kg; lentils = 0.9 kg\n• Try Meatless Monday — reduces food footprint by 15%\n• Buy local and seasonal produce — 30× lower transport emissions\n• Reduce food waste — 1/3 of food produced is wasted\n• Compost organic waste instead of sending to landfill",

  shopping: "🛍️ **Shopping Smarter:**\n• Buy quality, durable goods over cheap disposables\n• Second-hand fashion emits 82% less CO₂ than new fast fashion\n• Choose products with minimal packaging\n• Repair instead of replace — extends product life 2–3×\n• Borrow or rent items you use rarely",

  offset: "🌳 **Carbon Offsets:**\n• 1 tree absorbs ~21 kg CO₂/year\n• Verified carbon credits cost $10–30 per tonne CO₂\n• Partner NGOs: Green Yatra (trees), Blue Carbon (mangroves), Barefoot College (solar)\n• Offsets are a supplement to reduction — not a substitute\n• Use the Carby Control dashboard to calculate your offset needs",

  goal: "🎯 **Setting Carbon Goals:**\n• IPCC recommends 2.5 tonnes CO₂/person/year by 2030\n• Start with a 10% monthly reduction goal — achievable and measurable\n• Track daily to spot patterns — most people are surprised by transport\n• Use the Carby Control dashboard to set and track your goal",

  beginner: "🌱 **Starting Your Eco Journey:**\n1. Calculate your baseline footprint (use our calculator above!)\n2. Identify your top 2 emission sources\n3. Set a 10% monthly reduction goal\n4. Log daily to track progress\n5. Join community challenges for motivation\n6. Celebrate milestones with badges and points!",

  company: "🏢 **Enterprise Carbon Management:**\n• Track Scope 1 (direct), Scope 2 (energy), Scope 3 (supply chain)\n• Generate BRSR, GRI, and CDP-compliant ESG reports\n• Set department-level targets with team dashboards\n• AI forecasting predicts next-quarter emissions\n• Join 50+ companies already using Carby Control Enterprise",

  security: "🔒 **Our Security Features:**\n• CSRF tokens on all forms — prevents cross-site attacks\n• OTP authentication — no passwords stored\n• 256-bit session encryption (HMAC-SHA1)\n• Parameterized SQL queries — injection-proof\n• HTTPS/TLS on all connections via Vercel SSL\n• OTP auto-expiry in 10 minutes",

  default: "🌍 I can help you with:\n• 🚗 Transport emission tips\n• ⚡ Electricity saving strategies\n• 🍖 Food footprint reduction\n• 🛍️ Sustainable shopping\n• 🌳 Carbon offset options\n• 🎯 Setting reduction goals\n• 🏢 Enterprise ESG tracking\n• 🔒 Platform security info\n\nJust ask me anything!"
};

function getChatResponse(msg) {
  const m = msg.toLowerCase();
  if (m.includes('transport') || m.includes('commute') || m.includes('drive') || m.includes('car')) return chatbotResponses.car;
  if (m.includes('bus') || m.includes('train') || m.includes('public transport')) return chatbotResponses.transport;
  if (m.includes('electric') || m.includes('energy') || m.includes('power') || m.includes('bulb')) return chatbotResponses.electricity;
  if (m.includes('food') || m.includes('meat') || m.includes('eat') || m.includes('diet')) return chatbotResponses.food;
  if (m.includes('shop') || m.includes('buy') || m.includes('purchase') || m.includes('fashion')) return chatbotResponses.shopping;
  if (m.includes('offset') || m.includes('tree') || m.includes('ngo') || m.includes('credit')) return chatbotResponses.offset;
  if (m.includes('goal') || m.includes('target') || m.includes('reduce')) return chatbotResponses.goal;
  if (m.includes('start') || m.includes('begin') || m.includes('new') || m.includes('first')) return chatbotResponses.beginner;
  if (m.includes('company') || m.includes('business') || m.includes('enterprise') || m.includes('esg') || m.includes('scope')) return chatbotResponses.company;
  if (m.includes('security') || m.includes('safe') || m.includes('privacy') || m.includes('data') || m.includes('csrf')) return chatbotResponses.security;
  return chatbotResponses.default;
}

function toggleChatbot() {
  const panel    = document.getElementById('chatbotPanel');
  const iconOpen = document.querySelector('.chatbot-icon-open');
  const iconClose= document.querySelector('.chatbot-icon-close');
  if (!panel) return;
  const visible = panel.style.display === 'flex';
  panel.style.display = visible ? 'none' : 'flex';
  if (iconOpen)  iconOpen.style.display  = visible ? 'inline-block' : 'none';
  if (iconClose) iconClose.style.display = visible ? 'none' : 'inline-block';
  if (!visible) {
    const input = document.getElementById('chatbotInput');
    if (input) setTimeout(() => input.focus(), 100);
  }
}

function sendChatMsg(text) {
  const input    = document.getElementById('chatbotInput');
  const messages = document.getElementById('chatbotMessages');
  if (!messages) return;

  const msg = text || (input ? input.value.trim() : '');
  if (!msg) return;
  if (input) input.value = '';

  // User bubble
  const userDiv = document.createElement('div');
  userDiv.className = 'chat-msg user-msg';
  userDiv.textContent = msg;
  messages.appendChild(userDiv);

  // Bot typing indicator
  const typingDiv = document.createElement('div');
  typingDiv.className = 'chat-msg bot-msg chat-typing';
  typingDiv.innerHTML = '<span></span><span></span><span></span>';
  messages.appendChild(typingDiv);
  messages.scrollTop = messages.scrollHeight;

  // Bot response after short delay
  setTimeout(() => {
    messages.removeChild(typingDiv);
    const botDiv = document.createElement('div');
    botDiv.className = 'chat-msg bot-msg';
    // Convert newlines & **bold** to HTML
    botDiv.innerHTML = getChatResponse(msg)
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');
    messages.appendChild(botDiv);
    messages.scrollTop = messages.scrollHeight;
  }, 800);
}

// ── Initialize everything ────────────────────────────────────────
initLandingCharts();
updateLandingDemo();

// Animate security threat meter on scroll into view
const threatFill = document.querySelector('.threat-meter-fill');
if (threatFill) {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        threatFill.style.width = '92%';
        observer.disconnect();
      }
    });
  }, { threshold: 0.3 });
  observer.observe(threatFill);
}
