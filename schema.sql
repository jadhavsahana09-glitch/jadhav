-- ============================================================
--  EcoTrack — Updated Database Schema (OTP Auth)
--  Run this to recreate the database with OTP support
-- ============================================================

DROP DATABASE IF EXISTS carbon_db;
CREATE DATABASE carbon_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE carbon_db;

-- ── USERS (no password — OTP login only) ─────────────────────
CREATE TABLE users (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    email      VARCHAR(150) UNIQUE DEFAULT NULL,
    phone      VARCHAR(20)  UNIQUE DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (email IS NOT NULL OR phone IS NOT NULL)
);

-- ── OTP TOKENS ───────────────────────────────────────────────
CREATE TABLE otp_tokens (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(150) NOT NULL,   -- email or phone
    otp_code   VARCHAR(6)   NOT NULL,
    expires_at DATETIME     NOT NULL,
    used       TINYINT(1)   DEFAULT 0,
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ident  (identifier),
    INDEX idx_expire (expires_at)
);

-- ── EMISSION CATEGORIES ───────────────────────────────────────
CREATE TABLE categories (
    id    INT AUTO_INCREMENT PRIMARY KEY,
    name  VARCHAR(50) NOT NULL,
    icon  VARCHAR(50),
    color VARCHAR(20)
);

INSERT INTO categories (id, name, icon, color) VALUES
(1, 'Transport', 'directions_car', '#4ade80'),
(2, 'Energy',    'bolt',           '#facc15'),
(3, 'Food',      'restaurant',     '#f472b6'),
(4, 'Shopping',  'shopping_bag',   '#a78bfa'),
(5, 'Waste',     'delete_sweep',   '#60a5fa');

-- ── EMISSION LOGS ─────────────────────────────────────────────
CREATE TABLE emission_logs (
    id          INT AUTO_INCREMENT PRIMARY KEY,
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
CREATE TABLE goals (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    user_id        INT           NOT NULL UNIQUE,
    monthly_target DECIMAL(10,3) NOT NULL DEFAULT 100.000,
    created_at     TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
