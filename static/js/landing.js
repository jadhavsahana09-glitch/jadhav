const demoInputs = {
  transport: document.getElementById('demoTransport'),
  electricity: document.getElementById('demoElectricity'),
  food: document.getElementById('demoFood'),
  shopping: document.getElementById('demoShopping'),
};

const demoTotal = document.getElementById('demoTotal');
const aiSuggestion = document.getElementById('aiSuggestion');
const treesNeeded = document.getElementById('treesNeeded');
const creditsNeeded = document.getElementById('creditsNeeded');
const landingGoalPct = document.getElementById('landingGoalPct');
const landingGoalBar = document.getElementById('landingGoalBar');

const factors = {
  transport: 0.21,
  electricity: 0.23,
  food: 3.1,
  shopping: 0.03,
};

let barChart;
let pieChart;
let trendChart;

function readDemoValues() {
  return {
    transport: Math.max(parseFloat(demoInputs.transport?.value) || 0, 0) * factors.transport,
    electricity: Math.max(parseFloat(demoInputs.electricity?.value) || 0, 0) * factors.electricity,
    food: Math.max(parseFloat(demoInputs.food?.value) || 0, 0) * factors.food,
    shopping: Math.max(parseFloat(demoInputs.shopping?.value) || 0, 0) * factors.shopping,
  };
}

function buildSuggestion(values) {
  const entries = Object.entries(values).sort((a, b) => b[1] - a[1]);
  const [topCategory, topValue] = entries[0];
  const savings = Math.max(topValue * 8, 4).toFixed(1);

  const messages = {
    transport: `Your transport emissions are highest today. Use public transport twice a week to save about ${savings} kg CO2/month.`,
    electricity: `Electricity is leading your footprint. Shift heavy appliance use and switch to LEDs to save about ${savings} kg CO2/month.`,
    food: `Food is leading your footprint. Replacing a few meat meals with vegetarian meals can save about ${savings} kg CO2/month.`,
    shopping: `Shopping is leading your footprint. Choose durable or second-hand products to save about ${savings} kg CO2/month.`,
  };

  return messages[topCategory];
}

function updateLandingDemo() {
  const values = readDemoValues();
  const labels = ['Transport', 'Electricity', 'Food', 'Shopping'];
  const data = [values.transport, values.electricity, values.food, values.shopping].map(v => Number(v.toFixed(2)));
  const total = data.reduce((sum, value) => sum + value, 0);

  if (demoTotal) demoTotal.textContent = `${total.toFixed(2)} kg CO2`;
  if (aiSuggestion) aiSuggestion.textContent = buildSuggestion(values);
  if (treesNeeded) treesNeeded.textContent = Math.max(Math.ceil((total * 30) / 21), 1);
  if (creditsNeeded) creditsNeeded.textContent = (total / 1000).toFixed(3);

  const goalProgress = Math.min(Math.round(100 - Math.min(total * 3, 55)), 95);
  if (landingGoalPct) landingGoalPct.textContent = `${goalProgress}%`;
  if (landingGoalBar) landingGoalBar.style.width = `${goalProgress}%`;

  if (barChart) {
    barChart.data.datasets[0].data = data;
    barChart.update();
  }
  if (pieChart) {
    pieChart.data.datasets[0].data = data;
    pieChart.update();
  }
}

function initLandingCharts() {
  const chartColors = ['#1A759F', '#E9C46A', '#E76F51', '#40916C'];
  const values = readDemoValues();
  const initialData = [values.transport, values.electricity, values.food, values.shopping].map(v => Number(v.toFixed(2)));

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: { color: '#4A6741', boxWidth: 12, font: { size: 12 } },
      },
    },
    scales: {
      x: { ticks: { color: '#4A6741' }, grid: { display: false } },
      y: { ticks: { color: '#4A6741' }, grid: { color: 'rgba(45,106,79,0.12)' }, beginAtZero: true },
    },
  };

  const barCanvas = document.getElementById('landingBarChart');
  if (barCanvas) {
    barChart = new Chart(barCanvas, {
      type: 'bar',
      data: {
        labels: ['Transport', 'Electricity', 'Food', 'Shopping'],
        datasets: [{
          label: 'kg CO2',
          data: initialData,
          backgroundColor: chartColors.map(color => `${color}cc`),
          borderColor: chartColors,
          borderWidth: 2,
          borderRadius: 6,
        }],
      },
      options: { ...chartOptions, plugins: { legend: { display: false } } },
    });
  }

  const trendCanvas = document.getElementById('landingTrendChart');
  if (trendCanvas) {
    trendChart = new Chart(trendCanvas, {
      type: 'line',
      data: {
        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        datasets: [{
          label: 'kg CO2',
          data: [142, 136, 124, 112, 104, 91],
          borderColor: '#2D6A4F',
          backgroundColor: 'rgba(45,106,79,0.12)',
          fill: true,
          tension: 0.35,
          pointBackgroundColor: '#2D6A4F',
        }],
      },
      options: chartOptions,
    });
  }

  const pieCanvas = document.getElementById('landingPieChart');
  if (pieCanvas) {
    pieChart = new Chart(pieCanvas, {
      type: 'doughnut',
      data: {
        labels: ['Transport', 'Electricity', 'Food', 'Shopping'],
        datasets: [{
          data: initialData,
          backgroundColor: chartColors.map(color => `${color}cc`),
          borderColor: '#ffffff',
          borderWidth: 3,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '62%',
        plugins: {
          legend: { position: 'bottom', labels: { color: '#4A6741', boxWidth: 12, font: { size: 12 } } },
        },
      },
    });
  }
}

Object.values(demoInputs).forEach(input => {
  if (input) input.addEventListener('input', updateLandingDemo);
});

initLandingCharts();
updateLandingDemo();
