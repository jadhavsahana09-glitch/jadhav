"""
EcoTrack — Carbon Footprint Web Application
Flask Backend with OTP Authentication (Email / Phone)
"""

import csv
import io
import json
import random
import smtplib
from datetime import date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import mysql.connector
import sqlite3
from config import Config
from flask import (Flask, flash, make_response, redirect,
                   render_template, request, session, url_for)
from flask_login import (LoginManager, UserMixin, current_user,
                         login_required, login_user, logout_user)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)
from twilio.rest import Client

# ─── App & Extensions ─────────────────────────────────────────────────────────
app = Flask(__name__)
app.config.from_object(Config)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'


@app.context_processor
def inject_now():
    return {
        'now': datetime.now(),
        'db_mode': DB_MODE
    }


# ─── DB Helper & SQLite Fallback ──────────────────────────────────────────────
DB_MODE = 'mysql'
_db_initialized = False

def sqlite_row_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def translate_query(query: str, is_sqlite: bool) -> str:
    if not is_sqlite:
        return query
    
    # 1. Parameter placeholder translation
    translated = query.replace('%s', '?')
    
    # 2. Date/time function translations
    translated = translated.replace('NOW()', "datetime('now', 'localtime')")
    translated = translated.replace("DATE_SUB(CURDATE(), INTERVAL 6 DAY)", "date('now', 'localtime', '-6 days')")
    translated = translated.replace("DATE_SUB(CURDATE(), INTERVAL 6 MONTH)", "date('now', 'localtime', '-6 months')")
    translated = translated.replace('CURDATE()', "date('now', 'localtime')")
    
    # 3. DATE_FORMAT translation
    translated = translated.replace("DATE_FORMAT(log_date, '%%Y-%%m')", "strftime('%Y-%m', log_date)")
    translated = translated.replace("DATE_FORMAT(log_date, '%Y-%m')", "strftime('%Y-%m', log_date)")
    
    # 4. Upsert (On Duplicate Key Update) translation
    if "ON DUPLICATE KEY UPDATE" in query:
        translated = translated.replace(
            "ON DUPLICATE KEY UPDATE monthly_target = VALUES(monthly_target)",
            "ON CONFLICT(user_id) DO UPDATE SET monthly_target = excluded.monthly_target"
        )
        
    return translated

class QueryTranslatingCursor:
    def __init__(self, cursor, is_sqlite):
        self._cursor = cursor
        self._is_sqlite = is_sqlite

    def execute(self, query, params=None):
        translated = translate_query(query, self._is_sqlite)
        if params is not None:
            self._cursor.execute(translated, params)
        else:
            self._cursor.execute(translated)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def close(self):
        self._cursor.close()

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def __getattr__(self, name):
        return getattr(self._cursor, name)

class QueryTranslatingConnection:
    def __init__(self, conn, is_sqlite):
        self._conn = conn
        self._is_sqlite = is_sqlite

    def cursor(self, dictionary=False):
        if self._is_sqlite:
            cur = self._conn.cursor()
            return QueryTranslatingCursor(cur, is_sqlite=True)
        else:
            cur = self._conn.cursor(dictionary=dictionary)
            return QueryTranslatingCursor(cur, is_sqlite=False)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)

def init_sqlite_db():
    import os
    db_file = 'carbon_db.sqlite'
    db_exists = os.path.exists(db_file)
    conn = sqlite3.connect(db_file)
    if not db_exists:
        cur = conn.cursor()
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       VARCHAR(100) NOT NULL,
            email      VARCHAR(150) UNIQUE DEFAULT NULL,
            phone      VARCHAR(20)  UNIQUE DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CHECK (email IS NOT NULL OR phone IS NOT NULL)
        );

        CREATE TABLE IF NOT EXISTS otp_tokens (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            identifier VARCHAR(150) NOT NULL,
            otp_code   VARCHAR(6)   NOT NULL,
            expires_at DATETIME     NOT NULL,
            used       INTEGER      DEFAULT 0,
            created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_ident ON otp_tokens (identifier);
        CREATE INDEX IF NOT EXISTS idx_expire ON otp_tokens (expires_at);

        CREATE TABLE IF NOT EXISTS categories (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  VARCHAR(50) NOT NULL,
            icon  VARCHAR(50),
            color VARCHAR(20)
        );

        INSERT OR IGNORE INTO categories (id, name, icon, color) VALUES
        (1, 'Transport', 'directions_car', '#4ade80'),
        (2, 'Energy',    'bolt',           '#facc15'),
        (3, 'Food',      'restaurant',     '#f472b6'),
        (4, 'Shopping',  'shopping_bag',   '#a78bfa'),
        (5, 'Waste',     'delete_sweep',   '#60a5fa');

        CREATE TABLE IF NOT EXISTS emission_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER        NOT NULL,
            category_id INTEGER        NOT NULL,
            amount      DECIMAL(10,3)  NOT NULL,
            description TEXT,
            log_date    DATE           NOT NULL,
            created_at  TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id)     REFERENCES users(id)      ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS goals (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER       NOT NULL UNIQUE,
            monthly_target DECIMAL(10,3) NOT NULL DEFAULT 100.000,
            created_at     TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)
        conn.commit()
        cur.close()
    conn.close()

def verify_and_init_db():
    global _db_initialized, DB_MODE
    if _db_initialized:
        return
    
    try:
        # Connect to MySQL server (without DB name)
        conn = mysql.connector.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD']
        )
        cur = conn.cursor()
        
        # Create DB if it doesn't exist
        db_name = app.config['MYSQL_DB']
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cur.execute(f"USE {db_name}")
        
        # Check if 'users' table exists, if not, load schema
        cur.execute("SHOW TABLES LIKE 'users'")
        if not cur.fetchone():
            import os
            schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
            if os.path.exists(schema_path):
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema_sql = f.read()
                
                for result in cur.execute(schema_sql, multi=True):
                    pass
                conn.commit()
                app.logger.info("Database schema initialized successfully from schema.sql")
                
        cur.close()
        conn.close()
        DB_MODE = 'mysql'
        _db_initialized = True
        app.logger.info("Database initialized successfully in MySQL mode.")
    except Exception as e:
        app.logger.warning(f"MySQL connection failed: {e}. Falling back to SQLite.")
        DB_MODE = 'sqlite'
        init_sqlite_db()
        _db_initialized = True
        app.logger.info("Database initialized successfully in SQLite fallback mode.")

@app.before_request
def before_request():
    if request.endpoint == 'static' or request.path.startswith('/static/') or request.path == '/favicon.ico':
        return
    verify_and_init_db()

@app.errorhandler(mysql.connector.Error)
def handle_db_error(e):
    if DB_MODE == 'sqlite':
        return redirect(url_for('index'))
    return render_template('db_error.html', error=str(e)), 500

@app.errorhandler(sqlite3.Error)
def handle_sqlite_error(e):
    return render_template('db_error.html', error=str(e)), 500

def get_db():
    if DB_MODE == 'sqlite':
        conn = sqlite3.connect('carbon_db.sqlite')
        conn.row_factory = sqlite_row_factory
        conn.execute("PRAGMA foreign_keys = ON")
        return QueryTranslatingConnection(conn, is_sqlite=True)
    else:
        return QueryTranslatingConnection(
            mysql.connector.connect(
                host=app.config['MYSQL_HOST'],
                user=app.config['MYSQL_USER'],
                password=app.config['MYSQL_PASSWORD'],
                database=app.config['MYSQL_DB'],
            ),
            is_sqlite=False
        )


# ─── User Model ───────────────────────────────────────────────────────────────
class User(UserMixin):
    def __init__(self, id, name, email='', phone=''):
        self.id    = id
        self.name  = name
        self.email = email
        self.phone = phone


@login_manager.user_loader
def load_user(user_id):
    try:
        db  = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        cur.close(); db.close()
        if row:
            return User(row['id'], row['name'], row.get('email') or '', row.get('phone') or '')
    except Exception:
        pass
    return None


# ─── OTP Helpers ──────────────────────────────────────────────────────────────
def generate_otp() -> str:
    return str(random.randint(100000, 999999))


def store_otp(identifier: str, otp: str):
    """Delete old OTPs for this identifier and store a fresh one."""
    db  = get_db()
    cur = db.cursor()
    cur.execute(
        "DELETE FROM otp_tokens WHERE identifier = %s OR expires_at < NOW()",
        (identifier,)
    )
    expires_at = datetime.now() + timedelta(minutes=app.config['OTP_EXPIRY_MINUTES'])
    cur.execute(
        "INSERT INTO otp_tokens (identifier, otp_code, expires_at) VALUES (%s, %s, %s)",
        (identifier, otp, expires_at)
    )
    db.commit(); cur.close(); db.close()


def verify_otp_code(identifier: str, otp_code: str) -> bool:
    """Check OTP and mark it used if valid."""
    db  = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT id FROM otp_tokens
        WHERE identifier = %s AND otp_code = %s
          AND expires_at > NOW() AND used = 0
        ORDER BY created_at DESC LIMIT 1
    """, (identifier, otp_code))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE otp_tokens SET used = 1 WHERE id = %s", (row['id'],))
        db.commit()
    cur.close(); db.close()
    return row is not None


def send_email_otp(to_email: str, otp: str) -> bool:
    """Send OTP via Gmail SMTP. Returns True on success."""
    from_email = app.config.get('MAIL_USERNAME', '')
    password   = app.config.get('MAIL_PASSWORD', '')
    if not from_email or not password:
        return False

    msg             = MIMEMultipart('alternative')
    msg['Subject']  = '🌱 Your EcoTrack Login OTP'
    msg['From']     = f'EcoTrack <{from_email}>'
    msg['To']       = to_email

    html = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 520px;
                margin: 0 auto; background: #0d1117; border-radius: 16px;
                padding: 40px; color: #e2e8f0;">
      <div style="text-align:center; margin-bottom:32px;">
        <span style="font-size:40px;">🌱</span>
        <h1 style="color:#4ade80; margin:8px 0 0; font-size:26px; letter-spacing:-0.5px;">
          EcoTrack
        </h1>
      </div>
      <h2 style="font-size:20px; color:#e2e8f0; margin-bottom:8px;">
        Your one-time login code
      </h2>
      <p style="color:#94a3b8; margin-bottom:28px; font-size:14px; line-height:1.6;">
        Use the code below to sign in to your EcoTrack account.
        It expires in <strong style="color:#4ade80;">10 minutes</strong>.
      </p>
      <div style="background:#151d27; border:2px solid #4ade80; border-radius:12px;
                  padding:28px; text-align:center; margin-bottom:28px;">
        <div style="font-size:48px; font-weight:900; letter-spacing:14px; color:#4ade80;">
          {otp}
        </div>
      </div>
      <p style="font-size:12px; color:#475569; text-align:center; line-height:1.6;">
        If you didn't request this code, you can safely ignore this email.<br/>
        Never share this OTP with anyone.
      </p>
    </div>
    """

    msg.attach(MIMEText(html, 'html'))
    try:
        with smtplib.SMTP_SSL(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as srv:
            srv.login(from_email, password)
            srv.sendmail(from_email, to_email, msg.as_string())
        return True
    except Exception as e:
        app.logger.error(f'Email send failed: {e}')
        return False

def send_sms_otp(to_phone: str, otp: str) -> bool:
    """Send OTP via Twilio SMS. Returns True on success."""
    account_sid = app.config.get('TWILIO_ACCOUNT_SID', '')
    auth_token  = app.config.get('TWILIO_AUTH_TOKEN', '')
    from_phone  = app.config.get('TWILIO_PHONE_NUMBER', '')
    
    if not account_sid or not auth_token or not from_phone:
        return False
        
    try:
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=f"Your EcoTrack login code is: {otp}. It expires in 10 minutes.",
            from_=from_phone,
            to=to_phone
        )
        return True
    except Exception as e:
        app.logger.error(f'SMS send failed: {e}')
        return False

def dispatch_otp(identifier: str, otp: str):
    """
    Send OTP via email (if configured) or SMS (if configured) or display it on screen (DEMO_MODE).
    Returns (sent_silently: bool, demo_code: str | None)
    """
    is_em = is_email(identifier)

    if not app.config.get('DEMO_MODE', True):
        if is_em:
            if send_email_otp(identifier, otp):
                return True, None   # sent via email, don't reveal on screen
        else:
            if send_sms_otp(identifier, otp):
                return True, None   # sent via SMS, don't reveal on screen
        # fall through to demo mode if sending failed or missing config

    # Demo / phone fallback — show OTP in flash
    return False, otp


def is_email(identifier: str) -> bool:
    return '@' in identifier


# ─── Landing ─────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


# ─── Register (Step 1) ────────────────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name       = request.form.get('name', '').strip()
        identifier = request.form.get('identifier', '').strip()

        errors = []
        if not name:       errors.append('Full name is required.')
        if not identifier: errors.append('Email or phone number is required.')

        if not errors:
            db  = get_db(); cur = db.cursor(dictionary=True)
            if is_email(identifier):
                cur.execute("SELECT id FROM users WHERE email = %s", (identifier,))
            else:
                cur.execute("SELECT id FROM users WHERE phone = %s", (identifier,))
            existing = cur.fetchone()
            cur.close(); db.close()

            if existing:
                errors.append('An account already exists with this email/phone. '
                               'Please log in instead.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('register.html')

        otp = generate_otp()
        store_otp(identifier, otp)
        sent, demo_code = dispatch_otp(identifier, otp)

        session['otp_identifier'] = identifier
        session['otp_purpose']    = 'register'
        session['register_name']  = name

        if demo_code:
            flash(f'🔐 DEMO — Your OTP is: <strong>{demo_code}</strong>', 'otp')
        else:
            flash(f'OTP sent to {identifier}. Check your inbox!', 'success')

        return redirect(url_for('verify_otp'))

    return render_template('register.html')


# ─── Login (Step 1) ───────────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()

        if not identifier:
            flash('Please enter your email or phone number.', 'danger')
            return render_template('login.html')

        db  = get_db(); cur = db.cursor(dictionary=True)
        if is_email(identifier):
            cur.execute("SELECT * FROM users WHERE email = %s", (identifier,))
        else:
            cur.execute("SELECT * FROM users WHERE phone = %s", (identifier,))
        user_row = cur.fetchone()
        cur.close(); db.close()

        if not user_row:
            flash('No account found. Please register first.', 'danger')
            return render_template('login.html')

        otp = generate_otp()
        store_otp(identifier, otp)
        sent, demo_code = dispatch_otp(identifier, otp)

        session['otp_identifier'] = identifier
        session['otp_purpose']    = 'login'

        if demo_code:
            flash(f'🔐 DEMO — Your OTP is: <strong>{demo_code}</strong>', 'otp')
        else:
            flash(f'OTP sent to {identifier}. Check your inbox!', 'success')

        return redirect(url_for('verify_otp'))

    return render_template('login.html')


# ─── Verify OTP (Step 2) ──────────────────────────────────────────────────────
@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'otp_identifier' not in session:
        flash('Session expired. Please start again.', 'warning')
        return redirect(url_for('login'))

    identifier = session['otp_identifier']
    purpose    = session.get('otp_purpose', 'login')

    if request.method == 'POST':
        # Collect 6 individual digit boxes → one string
        digits    = [request.form.get(f'otp{i}', '').strip() for i in range(1, 7)]
        otp_input = ''.join(digits)

        if len(otp_input) != 6 or not otp_input.isdigit():
            flash('Please enter the complete 6-digit OTP.', 'danger')
            return render_template('otp_verify.html',
                                   identifier=identifier, purpose=purpose)

        if verify_otp_code(identifier, otp_input):
            # ── Valid OTP ─────────────────────────────────────────
            db  = get_db(); cur = db.cursor(dictionary=True)

            if purpose == 'register':
                name = session.pop('register_name', 'User')
                if is_email(identifier):
                    cur.execute(
                        "INSERT INTO users (name, email) VALUES (%s, %s)",
                        (name, identifier)
                    )
                else:
                    cur.execute(
                        "INSERT INTO users (name, phone) VALUES (%s, %s)",
                        (name, identifier)
                    )
                uid = cur.lastrowid
                cur.execute(
                    "INSERT INTO goals (user_id, monthly_target) VALUES (%s, 100.000)",
                    (uid,)
                )
                db.commit()
                user_obj = User(
                    id=uid,
                    name=name,
                    email=identifier if is_email(identifier) else '',
                    phone='' if is_email(identifier) else identifier
                )

            else:  # login
                if is_email(identifier):
                    cur.execute("SELECT * FROM users WHERE email = %s", (identifier,))
                else:
                    cur.execute("SELECT * FROM users WHERE phone = %s", (identifier,))
                row      = cur.fetchone()
                user_obj = User(row['id'], row['name'], row.get('email') or '', row.get('phone') or '')

            cur.close(); db.close()

            login_user(user_obj, remember=True)
            session.pop('otp_identifier', None)
            session.pop('otp_purpose', None)

            flash(f'Welcome, {user_obj.name}! 🌱', 'success')
            return redirect(url_for('dashboard'))

        else:
            flash('Invalid or expired OTP. Please try again.', 'danger')

    return render_template('otp_verify.html',
                           identifier=identifier, purpose=purpose)


# ─── Resend OTP ───────────────────────────────────────────────────────────────
@app.route('/resend-otp', methods=['POST'])
def resend_otp():
    if 'otp_identifier' not in session:
        return redirect(url_for('login'))

    identifier = session['otp_identifier']
    otp        = generate_otp()
    store_otp(identifier, otp)
    sent, demo_code = dispatch_otp(identifier, otp)

    if demo_code:
        flash(f'🔐 DEMO — New OTP is: <strong>{demo_code}</strong>', 'otp')
    else:
        flash(f'New OTP sent to {identifier}!', 'success')

    return redirect(url_for('verify_otp'))


# ─── Logout ───────────────────────────────────────────────────────────────────
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))


# ─── Dashboard ────────────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    db  = get_db(); cur = db.cursor(dictionary=True)
    now       = datetime.now()
    first_day = now.replace(day=1).strftime('%Y-%m-%d')

    cur.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total FROM emission_logs
        WHERE user_id = %s AND log_date >= %s
    """, (current_user.id, first_day))
    month_total = float(cur.fetchone()['total'])

    cur.execute("""
        SELECT c.name, c.color, COALESCE(SUM(e.amount), 0) AS total
        FROM emission_logs e JOIN categories c ON e.category_id = c.id
        WHERE e.user_id = %s AND e.log_date >= %s
        GROUP BY c.id, c.name, c.color ORDER BY total DESC
    """, (current_user.id, first_day))
    category_data = cur.fetchall()

    cur.execute("""
        SELECT log_date, COALESCE(SUM(amount), 0) AS total FROM emission_logs
        WHERE user_id = %s AND log_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
        GROUP BY log_date ORDER BY log_date
    """, (current_user.id,))
    daily_rows = cur.fetchall()

    cur.execute("SELECT monthly_target FROM goals WHERE user_id = %s", (current_user.id,))
    goal_row       = cur.fetchone()
    monthly_target = float(goal_row['monthly_target']) if goal_row else 100.0

    cur.execute("""
        SELECT e.id, e.amount, e.description, e.log_date,
               c.name AS category_name, c.color AS category_color, c.icon AS category_icon
        FROM emission_logs e JOIN categories c ON e.category_id = c.id
        WHERE e.user_id = %s ORDER BY e.log_date DESC, e.created_at DESC LIMIT 5
    """, (current_user.id,))
    recent_entries = cur.fetchall()

    cur.execute("SELECT COUNT(*) AS cnt FROM emission_logs WHERE user_id = %s", (current_user.id,))
    total_entries  = cur.fetchone()['cnt']
    cur.close(); db.close()

    day_labels, daily_chart = [], []
    daily_map = {str(r['log_date']): float(r['total']) for r in daily_rows}
    for i in range(6, -1, -1):
        d = now - timedelta(days=i)
        day_labels.append(d.strftime('%b %d'))
        daily_chart.append(daily_map.get(d.strftime('%Y-%m-%d'), 0))

    goal_pct = min(round((month_total / monthly_target) * 100, 1), 100) if monthly_target else 0

    return render_template('dashboard.html',
        month_total=round(month_total, 2),
        monthly_target=monthly_target, goal_pct=goal_pct,
        total_entries=total_entries, category_data=category_data,
        recent_entries=recent_entries,
        day_labels=json.dumps(day_labels), daily_chart=json.dumps(daily_chart),
        cat_labels=json.dumps([c['name']        for c in category_data]),
        cat_values=json.dumps([float(c['total']) for c in category_data]),
        cat_colors=json.dumps([c['color']        for c in category_data]),
    )


# ─── Dashboard JSON API ───────────────────────────────────────────────────────
@app.route('/api/dashboard-data')
@login_required
def api_dashboard_data():
    db  = get_db(); cur = db.cursor(dictionary=True)
    now       = datetime.now()
    first_day = now.replace(day=1).strftime('%Y-%m-%d')

    cur.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total FROM emission_logs
        WHERE user_id = %s AND log_date >= %s
    """, (current_user.id, first_day))
    month_total = float(cur.fetchone()['total'])

    cur.execute("""
        SELECT c.name, c.color, COALESCE(SUM(e.amount), 0) AS total
        FROM emission_logs e JOIN categories c ON e.category_id = c.id
        WHERE e.user_id = %s AND e.log_date >= %s
        GROUP BY c.id, c.name, c.color ORDER BY total DESC
    """, (current_user.id, first_day))
    category_data = cur.fetchall()

    cur.execute("""
        SELECT log_date, COALESCE(SUM(amount), 0) AS total FROM emission_logs
        WHERE user_id = %s AND log_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
        GROUP BY log_date ORDER BY log_date
    """, (current_user.id,))
    daily_rows = cur.fetchall()

    cur.execute("SELECT monthly_target FROM goals WHERE user_id = %s", (current_user.id,))
    goal_row       = cur.fetchone()
    monthly_target = float(goal_row['monthly_target']) if goal_row else 100.0

    cur.execute("""
        SELECT e.id, e.amount, e.description, e.log_date,
               c.name AS category_name, c.color AS category_color, c.icon AS category_icon
        FROM emission_logs e JOIN categories c ON e.category_id = c.id
        WHERE e.user_id = %s ORDER BY e.log_date DESC, e.created_at DESC LIMIT 5
    """, (current_user.id,))
    recent_entries = cur.fetchall()

    cur.execute("SELECT COUNT(*) AS cnt FROM emission_logs WHERE user_id = %s", (current_user.id,))
    total_entries  = cur.fetchone()['cnt']
    cur.close(); db.close()

    day_labels, daily_chart = [], []
    daily_map = {str(r['log_date']): float(r['total']) for r in daily_rows}
    for i in range(6, -1, -1):
        d = now - timedelta(days=i)
        day_labels.append(d.strftime('%b %d'))
        daily_chart.append(daily_map.get(d.strftime('%Y-%m-%d'), 0))

    goal_pct = min(round((month_total / monthly_target) * 100, 1), 100) if monthly_target else 0

    # Format recent entries for JSON serialization
    formatted_recent = []
    for r in recent_entries:
        formatted_recent.append({
            'id': r['id'],
            'amount': float(r['amount']),
            'description': r['description'],
            'log_date': str(r['log_date']),
            'category_name': r['category_name'],
            'category_color': r['category_color'],
            'category_icon': r['category_icon']
        })

    return {
        'month_total': round(month_total, 2),
        'monthly_target': monthly_target,
        'goal_pct': goal_pct,
        'total_entries': total_entries,
        'recent_entries': formatted_recent,
        'day_labels': day_labels,
        'daily_chart': daily_chart,
        'cat_labels': [c['name'] for c in category_data],
        'cat_values': [float(c['total']) for c in category_data],
        'cat_colors': [c['color'] for c in category_data]
    }


# ─── Tracker ──────────────────────────────────────────────────────────────────
@app.route('/tracker', methods=['GET', 'POST'])
@login_required
def tracker():
    db  = get_db(); cur = db.cursor(dictionary=True)

    if request.method == 'POST':
        cat_id      = request.form.get('category_id')
        amount_str  = request.form.get('amount', '')
        description = request.form.get('description', '').strip()
        log_date    = request.form.get('log_date', date.today().isoformat())
        try:
            amount = float(amount_str)
            if amount <= 0:
                flash('Amount must be greater than zero.', 'danger')
            else:
                cur.execute("""
                    INSERT INTO emission_logs (user_id, category_id, amount, description, log_date)
                    VALUES (%s, %s, %s, %s, %s)
                """, (current_user.id, cat_id, amount, description or None, log_date))
                db.commit()
                flash(f'✅ {amount} kg CO₂ logged!', 'success')
                cur.close(); db.close()
                return redirect(url_for('tracker'))
        except (ValueError, TypeError):
            flash('Please enter a valid numeric amount.', 'danger')

    cur.execute("SELECT * FROM categories ORDER BY name")
    categories = cur.fetchall()

    cur.execute("""
        SELECT e.id, e.amount, e.description, e.log_date,
               c.name AS category_name, c.color AS category_color, c.icon AS category_icon
        FROM emission_logs e JOIN categories c ON e.category_id = c.id
        WHERE e.user_id = %s ORDER BY e.log_date DESC, e.created_at DESC LIMIT 30
    """, (current_user.id,))
    logs = cur.fetchall()
    cur.close(); db.close()
    return render_template('tracker.html', categories=categories, logs=logs,
                           today=date.today().isoformat())


@app.route('/tracker/delete/<int:log_id>', methods=['POST'])
@login_required
def delete_log(log_id):
    db  = get_db(); cur = db.cursor()
    cur.execute("DELETE FROM emission_logs WHERE id = %s AND user_id = %s",
                (log_id, current_user.id))
    db.commit(); cur.close(); db.close()
    flash('Entry deleted.', 'info')
    return redirect(url_for('tracker'))


# ─── Progress ─────────────────────────────────────────────────────────────────
@app.route('/progress')
@login_required
def progress():
    db  = get_db(); cur = db.cursor(dictionary=True)
    now       = datetime.now()
    first_day = now.replace(day=1).strftime('%Y-%m-%d')

    cur.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total FROM emission_logs
        WHERE user_id = %s AND log_date >= %s
    """, (current_user.id, first_day))
    month_total = float(cur.fetchone()['total'])

    last_end   = (now.replace(day=1) - timedelta(days=1)).strftime('%Y-%m-%d')
    last_start = (now.replace(day=1) - timedelta(days=1)).replace(day=1).strftime('%Y-%m-%d')
    cur.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total FROM emission_logs
        WHERE user_id = %s AND log_date BETWEEN %s AND %s
    """, (current_user.id, last_start, last_end))
    last_month_total = float(cur.fetchone()['total'])

    cur.execute("""
        SELECT DATE_FORMAT(log_date, '%%Y-%%m') AS month, SUM(amount) AS total
        FROM emission_logs
        WHERE user_id = %s AND log_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
        GROUP BY month ORDER BY month
    """, (current_user.id,))
    monthly_rows = cur.fetchall()

    cur.execute("""
        SELECT c.name, c.color, COALESCE(SUM(e.amount), 0) AS total
        FROM emission_logs e JOIN categories c ON e.category_id = c.id
        WHERE e.user_id = %s GROUP BY c.id, c.name, c.color ORDER BY total DESC
    """, (current_user.id,))
    all_category = cur.fetchall()

    cur.execute("SELECT monthly_target FROM goals WHERE user_id = %s", (current_user.id,))
    goal_row       = cur.fetchone()
    monthly_target = float(goal_row['monthly_target']) if goal_row else 100.0

    cur.execute("""
        SELECT DISTINCT log_date FROM emission_logs
        WHERE user_id = %s ORDER BY log_date DESC
    """, (current_user.id,))
    logged_dates = [r['log_date'] for r in cur.fetchall()]
    streak = 0
    today  = date.today()
    for i, d in enumerate(logged_dates):
        if d == today - timedelta(days=i): streak += 1
        else: break

    cur.close(); db.close()

    month_labels, month_values = [], []
    monthly_map = {r['month']: float(r['total']) for r in monthly_rows}
    for i in range(5, -1, -1):
        d = now - timedelta(days=30 * i)
        month_labels.append(d.strftime('%b %Y'))
        month_values.append(monthly_map.get(d.strftime('%Y-%m'), 0))

    change_pct = 0
    if last_month_total > 0:
        change_pct = round(((month_total - last_month_total) / last_month_total) * 100, 1)
    goal_pct = min(round((month_total / monthly_target) * 100, 1), 100) if monthly_target else 0

    return render_template('progress.html',
        month_total=round(month_total, 2), monthly_target=monthly_target,
        goal_pct=goal_pct, streak=streak, change_pct=change_pct,
        all_category=all_category,
        month_labels=json.dumps(month_labels), month_values=json.dumps(month_values),
        cat_labels=json.dumps([c['name']        for c in all_category]),
        cat_values=json.dumps([float(c['total']) for c in all_category]),
        cat_colors=json.dumps([c['color']        for c in all_category]),
    )


@app.route('/progress/update-goal', methods=['POST'])
@login_required
def update_goal():
    try:
        target = float(request.form.get('monthly_target', ''))
        if target <= 0: raise ValueError
        db  = get_db(); cur = db.cursor()
        cur.execute("""
            INSERT INTO goals (user_id, monthly_target) VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE monthly_target = VALUES(monthly_target)
        """, (current_user.id, target))
        db.commit(); cur.close(); db.close()
        flash(f'Goal updated to {target} kg CO₂/month!', 'success')
    except Exception:
        flash('Invalid goal value.', 'danger')
    return redirect(url_for('progress'))


# ─── Reports ──────────────────────────────────────────────────────────────────
@app.route('/reports')
@login_required
def reports():
    db  = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT COUNT(*) AS count, COALESCE(SUM(amount), 0) AS total,
               MIN(log_date) AS first_log, MAX(log_date) AS last_log
        FROM emission_logs WHERE user_id = %s
    """, (current_user.id,))
    stats = cur.fetchone()

    cur.execute("""
        SELECT c.name, c.color, c.icon, COALESCE(SUM(e.amount), 0) AS total
        FROM emission_logs e JOIN categories c ON e.category_id = c.id
        WHERE e.user_id = %s GROUP BY c.id, c.name, c.color, c.icon ORDER BY total DESC
    """, (current_user.id,))
    by_category = cur.fetchall()
    cur.close(); db.close()
    return render_template('reports.html', stats=stats, by_category=by_category)


@app.route('/reports/download/csv')
@login_required
def download_csv():
    start_date = request.args.get('start_date', '')
    end_date   = request.args.get('end_date', '')
    db  = get_db(); cur = db.cursor(dictionary=True)
    q      = """
        SELECT e.log_date, c.name AS category, e.amount, e.description, e.created_at
        FROM emission_logs e JOIN categories c ON e.category_id = c.id
        WHERE e.user_id = %s
    """
    params = [current_user.id]
    if start_date: q += " AND e.log_date >= %s"; params.append(start_date)
    if end_date:   q += " AND e.log_date <= %s"; params.append(end_date)
    q += " ORDER BY e.log_date DESC"
    cur.execute(q, params); logs = cur.fetchall()
    cur.close(); db.close()

    out = io.StringIO()
    w   = csv.writer(out)
    w.writerow(['Date', 'Category', 'CO2 (kg)', 'Description', 'Logged At'])
    for log in logs:
        w.writerow([log['log_date'], log['category'],
                    f"{log['amount']:.3f}", log['description'] or '', log['created_at']])
    resp = make_response(out.getvalue())
    resp.headers['Content-Disposition'] = 'attachment; filename=carbon_report.csv'
    resp.headers['Content-Type']        = 'text/csv; charset=utf-8'
    return resp


@app.route('/reports/download/pdf')
@login_required
def download_pdf():
    start_date = request.args.get('start_date', '')
    end_date   = request.args.get('end_date', '')
    db  = get_db(); cur = db.cursor(dictionary=True)
    q      = """
        SELECT e.log_date, c.name AS category, e.amount, e.description
        FROM emission_logs e JOIN categories c ON e.category_id = c.id
        WHERE e.user_id = %s
    """
    params = [current_user.id]
    if start_date: q += " AND e.log_date >= %s"; params.append(start_date)
    if end_date:   q += " AND e.log_date <= %s"; params.append(end_date)
    q += " ORDER BY e.log_date DESC"
    cur.execute(q, params); logs = cur.fetchall()
    cur.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count
        FROM emission_logs WHERE user_id = %s
    """, (current_user.id,)); stats = cur.fetchone()
    cur.close(); db.close()

    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=letter,
                               leftMargin=50, rightMargin=50, topMargin=60, bottomMargin=40)
    styles = getSampleStyleSheet(); elements = []
    elements.append(Paragraph('🌱 EcoTrack — Carbon Footprint Report', styles['Title']))
    elements.append(Paragraph(f'User: {current_user.name}  |  Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f'<b>Total CO₂:</b> {float(stats["total"]):.2f} kg  |  <b>Entries:</b> {stats["count"]}', styles['Normal']))
    elements.append(Spacer(1, 20))

    data = [['Date', 'Category', 'CO₂ (kg)', 'Description']]
    for log in logs:
        data.append([str(log['log_date']), log['category'],
                     f"{float(log['amount']):.3f}", (log['description'] or '')[:60]])
    t = Table(data, colWidths=[80, 100, 80, 240])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1, 0), colors.HexColor('#14532d')),
        ('TEXTCOLOR',     (0,0),(-1, 0), colors.white),
        ('FONTNAME',      (0,0),(-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0),(-1,-1), 9),
        ('ROWBACKGROUNDS',(0,1),(-1,-1), [colors.white, colors.HexColor('#f0fdf4')]),
        ('GRID',          (0,0),(-1,-1), 0.4, colors.HexColor('#d1d5db')),
        ('TOPPADDING',    (0,0),(-1,-1), 5), ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('LEFTPADDING',   (0,0),(-1,-1), 8),
    ]))
    elements.append(t)
    doc.build(elements); buf.seek(0)
    resp = make_response(buf.getvalue())
    resp.headers['Content-Disposition'] = 'attachment; filename=carbon_report.pdf'
    resp.headers['Content-Type']        = 'application/pdf'
    return resp


# ─── Run ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
