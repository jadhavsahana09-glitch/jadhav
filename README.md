# 🌱 EcoTrack — Carbon Footprint Web Application

A full-stack web application for monitoring carbon emissions and promoting sustainable lifestyle choices.

## Tech Stack

| Layer     | Technology                             |
|-----------|----------------------------------------|
| Frontend  | HTML5, CSS3 (dark glassmorphism theme) |
| Backend   | Flask 3.x + Flask-Login               |
| Database  | MySQL                                  |
| Charts    | Chart.js                               |
| Reports   | reportlab (PDF) + csv (CSV)            |

## Features

- ✅ **User Authentication** — Password-less Register/Login with 6-digit OTP codes sent to Email (Gmail SMTP) or SMS (Twilio), with on-screen Demo Mode fallback
- ✅ **Dashboard** — CO₂ summary cards, 7-day trend chart, category pie chart
- ✅ **Emission Tracker** — Log emissions across 5 categories with quick reference guide
- ✅ **Progress Tracking** — 6-month bar chart, goals, streak counter, category breakdown
- ✅ **Reports Download** — CSV and PDF exports with optional date range filter

## Project Structure

```
ppjs/
├── app.py               # Flask backend (all routes)
├── config.py            # DB & app configuration
├── requirements.txt     # Python dependencies
├── schema.sql           # MySQL database schema
├── run.bat              # Windows run script
│
├── static/
│   ├── css/style.css    # Premium dark theme
│   └── js/
│       ├── auth.js      # Login/register interactions
│       ├── tracker.js   # Tracker page interactions
│       └── report.js    # Report download logic
│
└── templates/
    ├── base.html        # Layout with sidebar
    ├── index.html       # Landing page
    ├── login.html       # Login page
    ├── register.html    # Register page
    ├── dashboard.html   # Dashboard with charts
    ├── tracker.html     # Emission logger
    ├── progress.html    # Progress & analytics
    └── reports.html     # Report download
```

## Setup Instructions

### 1. MySQL Setup

Open MySQL Workbench (or MySQL CLI) and run the schema:
```bash
mysql -u root -p < schema.sql
```

Or paste the contents of `schema.sql` into MySQL Workbench and execute.

**Default DB credentials** (edit `config.py` if needed):
```
Host:     localhost
User:     root
Password: root
Database: carbon_db
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Application

**Option A — Double-click `run.bat`**

**Option B — Command line:**
```bash
python app.py
```
or
```bash
flask --app app run --debug
```

### 4. Open in Browser

Navigate to: **http://localhost:5000**

### 5. Run Integration Tests (Optional)

To verify that the frontend, backend, database fallback, and PDF/CSV reports are all working together seamlessly:
```bash
python test_integration.py
```

## Emission Categories

| Category  | Icon          | Examples                        |
|-----------|---------------|---------------------------------|
| Transport | 🚗 Car        | Driving, flights, bus           |
| Energy    | ⚡ Bolt       | Electricity, gas                |
| Food      | 🍽️ Restaurant | Meat meals, dairy               |
| Shopping  | 🛍️ Bag       | Clothing, electronics           |
| Waste     | ♻️ Recycle   | Landfill waste                  |

## Resume Line

> *Developed a full-stack web application for monitoring carbon emissions and promoting sustainable lifestyle choices, featuring user authentication, real-time analytics dashboard, progress tracking, and downloadable CSV/PDF reports — built with Flask, MySQL, and vanilla HTML/CSS/JS.*
