"""SQLite schema for fund stock analysis.

The schema is intentionally source-agnostic: raw fund positions, stock master data,
prices, aggregates, changes, scores, and signal return checks are separated so data
providers can be replaced without rewriting analysis code.
"""

CREATE_TABLES_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL UNIQUE,
    stock_name TEXT,
    market TEXT,
    industry TEXT,
    sector TEXT,
    concept TEXT,
    total_market_value REAL,
    float_market_value REAL,
    update_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fund_stock_position (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code TEXT NOT NULL,
    stock_code TEXT NOT NULL,
    report_date TEXT NOT NULL,
    hold_shares REAL DEFAULT 0,
    market_value REAL DEFAULT 0,
    fund_nav_ratio REAL,
    stock_float_ratio REAL,
    UNIQUE(fund_code, stock_code, report_date)
);

CREATE INDEX IF NOT EXISTS idx_fund_position_stock ON fund_stock_position(stock_code);
CREATE INDEX IF NOT EXISTS idx_fund_position_fund ON fund_stock_position(fund_code);
CREATE INDEX IF NOT EXISTS idx_fund_position_report ON fund_stock_position(report_date);
CREATE INDEX IF NOT EXISTS idx_fund_position_stock_report ON fund_stock_position(stock_code, report_date);

CREATE TABLE IF NOT EXISTS stock_fund_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    report_date TEXT NOT NULL,
    fund_count INTEGER NOT NULL DEFAULT 0,
    total_market_value REAL NOT NULL DEFAULT 0,
    total_hold_shares REAL NOT NULL DEFAULT 0,
    float_ratio REAL,
    UNIQUE(stock_code, report_date)
);

CREATE INDEX IF NOT EXISTS idx_summary_report ON stock_fund_summary(report_date);
CREATE INDEX IF NOT EXISTS idx_summary_stock_report ON stock_fund_summary(stock_code, report_date);

CREATE TABLE IF NOT EXISTS stock_fund_change (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    current_period TEXT NOT NULL,
    previous_period TEXT NOT NULL,
    fund_count_change INTEGER,
    fund_count_growth REAL,
    market_value_change REAL,
    market_value_growth REAL,
    hold_shares_change REAL,
    hold_shares_growth REAL,
    UNIQUE(stock_code, current_period, previous_period)
);

CREATE INDEX IF NOT EXISTS idx_change_current ON stock_fund_change(current_period);
CREATE INDEX IF NOT EXISTS idx_change_stock_period ON stock_fund_change(stock_code, current_period);

CREATE TABLE IF NOT EXISTS stock_daily_price (
    stock_code TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    close_price REAL NOT NULL,
    PRIMARY KEY(stock_code, trade_date)
);

CREATE INDEX IF NOT EXISTS idx_price_stock_date ON stock_daily_price(stock_code, trade_date);

CREATE TABLE IF NOT EXISTS stock_return_analysis (
    stock_code TEXT NOT NULL,
    buy_period TEXT NOT NULL,
    return_3_month REAL,
    return_6_month REAL,
    return_12_month REAL,
    max_drawdown_12_month REAL,
    PRIMARY KEY(stock_code, buy_period)
);

CREATE TABLE IF NOT EXISTS stock_score (
    stock_code TEXT NOT NULL,
    report_date TEXT NOT NULL,
    score REAL NOT NULL,
    risk_flags TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY(stock_code, report_date)
);
"""
