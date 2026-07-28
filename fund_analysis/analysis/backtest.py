"""Return verification for fund-increase signals using SQL price lookups."""
from __future__ import annotations
import sqlite3


def _future_return(conn, code: str, start: str, days: int) -> float | None:
    base = conn.execute("SELECT close_price FROM stock_daily_price WHERE stock_code=? AND trade_date>=? ORDER BY trade_date LIMIT 1", (code, start)).fetchone()
    fut = conn.execute("SELECT close_price FROM stock_daily_price WHERE stock_code=? AND trade_date>=date(?, ?) ORDER BY trade_date LIMIT 1", (code, start, f"+{days} day")).fetchone()
    if not base or not fut or base[0] == 0:
        return None
    return fut[0] / base[0] - 1


def _max_drawdown(conn, code: str, start: str, days: int = 365) -> float | None:
    prices = [r[0] for r in conn.execute("SELECT close_price FROM stock_daily_price WHERE stock_code=? AND trade_date BETWEEN ? AND date(?, ?) ORDER BY trade_date", (code, start, start, f"+{days} day"))]
    if not prices:
        return None
    peak, mdd = prices[0], 0.0
    for p in prices:
        peak = max(peak, p)
        if peak:
            mdd = min(mdd, p / peak - 1)
    return mdd


def analyze_signal_returns(conn: sqlite3.Connection, buy_period: str, min_market_value_growth: float = 0.2) -> int:
    signals = conn.execute("SELECT stock_code FROM stock_fund_change WHERE current_period=? AND market_value_growth>=?", (buy_period, min_market_value_growth)).fetchall()
    rows = []
    for s in signals:
        code = s["stock_code"]
        rows.append((code, buy_period, _future_return(conn, code, buy_period, 90), _future_return(conn, code, buy_period, 180), _future_return(conn, code, buy_period, 365), _max_drawdown(conn, code, buy_period)))
    conn.executemany("""INSERT INTO stock_return_analysis(stock_code,buy_period,return_3_month,return_6_month,return_12_month,max_drawdown_12_month)
    VALUES (?,?,?,?,?,?) ON CONFLICT(stock_code,buy_period) DO UPDATE SET return_3_month=excluded.return_3_month,return_6_month=excluded.return_6_month,return_12_month=excluded.return_12_month,max_drawdown_12_month=excluded.max_drawdown_12_month""", rows)
    return len(rows)


def strategy_stats(conn: sqlite3.Connection, buy_period: str):
    return conn.execute("""SELECT COUNT(*) signals, AVG(return_3_month) avg_return_3m, AVG(return_6_month) avg_return_6m,
    AVG(return_12_month) avg_return_12m, AVG(CASE WHEN return_12_month>0 THEN 1.0 ELSE 0.0 END) win_rate_12m,
    MIN(max_drawdown_12_month) worst_drawdown FROM stock_return_analysis WHERE buy_period=?""", (buy_period,)).fetchone()
