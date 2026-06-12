import os

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'Carby Control-otp-secret-2024')

    # Vercel Postgres
    POSTGRES_URL   = os.environ.get('POSTGRES_URL')

    # MySQL — change these to match YOUR MySQL setup
    MYSQL_HOST     = os.environ.get('MYSQL_HOST',     'localhost')
    MYSQL_USER     = os.environ.get('MYSQL_USER',     'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'root')      # ← change if needed
    MYSQL_DB       = os.environ.get('MYSQL_DB',       'carbon_db')

    # ── OTP Settings ─────────────────────────────────────────────
    OTP_EXPIRY_MINUTES = 10   # OTP valid for 10 minutes

    # ── Email Settings (Gmail SMTP) ───────────────────────────────
    # Set DEMO_MODE = True  → OTP shown on screen (no email needed)
    # Set DEMO_MODE = False → Real email sent via Gmail
    DEMO_MODE = True

    MAIL_SERVER   = 'smtp.gmail.com'
    MAIL_PORT     = 465
    MAIL_USE_SSL  = True
    # To use real email: set these OR use environment variables
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')   # your Gmail address
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')

    # ── SMS Settings (Twilio) ───────────────────────────────
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN  = os.environ.get('TWILIO_AUTH_TOKEN', '')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')   # Gmail App Password (not login password)
    #
    # How to get Gmail App Password:
    # 1. Go to myaccount.google.com → Security → 2-Step Verification → App passwords
    # 2. Create a password for "Mail"
    # 3. Paste it as MAIL_PASSWORD above (or in the MAIL_PASSWORD env var)
