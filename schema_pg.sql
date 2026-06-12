-- ============================================================
--  EcoTrack — PostgreSQL Database Schema
--  Run this to recreate the database with OTP support
-- ============================================================

-- ── USERS (no password — OTP login only) ─────────────────────
CREATE TABLE IF NOT EXISTS users (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    email      VARCHAR(150) UNIQUE DEFAULT NULL,
    phone      VARCHAR(20)  UNIQUE DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (email IS NOT NULL OR phone IS NOT NULL)
);

-- ── OTP TOKENS ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS otp_tokens (
    id         SERIAL PRIMARY KEY,
    identifier VARCHAR(150) NOT NULL,   -- email or phone
    otp_code   VARCHAR(6)   NOT NULL,
    expires_at TIMESTAMP    NOT NULL,
    used       SMALLINT     DEFAULT 0,
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ident ON otp_tokens(identifier);
CREATE INDEX IF NOT EXISTS idx_expire ON otp_tokens(expires_at);

-- ── EMISSION CATEGORIES ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS categories (
    id    SERIAL PRIMARY KEY,
    name  VARCHAR(50) NOT NULL,
    icon  VARCHAR(50),
    color VARCHAR(20)
);

-- Insert categories if empty
INSERT INTO categories (id, name, icon, color) 
SELECT 1, 'Transport', 'directions_car', '#4ade80'
WHERE NOT EXISTS (SELECT 1 FROM categories WHERE id = 1);

INSERT INTO categories (id, name, icon, color) 
SELECT 2, 'Energy',    'bolt',           '#facc15'
WHERE NOT EXISTS (SELECT 1 FROM categories WHERE id = 2);

INSERT INTO categories (id, name, icon, color) 
SELECT 3, 'Food',      'restaurant',     '#f472b6'
WHERE NOT EXISTS (SELECT 1 FROM categories WHERE id = 3);

INSERT INTO categories (id, name, icon, color) 
SELECT 4, 'Shopping',  'shopping_bag',   '#a78bfa'
WHERE NOT EXISTS (SELECT 1 FROM categories WHERE id = 4);

INSERT INTO categories (id, name, icon, color) 
SELECT 5, 'Waste',     'delete_sweep',   '#60a5fa'
WHERE NOT EXISTS (SELECT 1 FROM categories WHERE id = 5);

-- ── EMISSION LOGS ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS emission_logs (
    id          SERIAL PRIMARY KEY,
    user_id     INT            NOT NULL,
    category_id INT            NOT NULL,
    amount      DECIMAL(10,3)  NOT NULL,
    description TEXT,
    log_date    DATE           NOT NULL,
    created_at  TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)     REFERENCES users(id)      ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT
);

-- ── USER GOALS ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS goals (
    id             SERIAL PRIMARY KEY,
    user_id        INT           NOT NULL UNIQUE,
    monthly_target DECIMAL(10,3) NOT NULL DEFAULT 100.000,
    created_at     TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
