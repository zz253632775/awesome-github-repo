"""SQL-first quarterly fund holding summaries."""
from __future__ import annotations
import sqlite3


def build_summary(conn: sqlite3.Connection, report_date: str) -> int:
    sql = """
    INSERT INTO stock_fund_summary
      (stock_code, report_date, fund_count, total_market_value, total_hold_shares, float_ratio)
    SELECT p.stock_code, p.report_date, COUNT(DISTINCT p.fund_code), SUM(p.market_value),
           SUM(p.hold_shares),
           CASE WHEN MAX(s.float_market_value) > 0 THEN SUM(p.market_value) / MAX(s.float_market_value) ELSE NULL END
    FROM fund_stock_position p
    LEFT JOIN stock s ON s.stock_code = p.stock_code
    WHERE p.report_date = ?
    GROUP BY p.stock_code, p.report_date
    ON CONFLICT(stock_code, report_date) DO UPDATE SET
      fund_count=excluded.fund_count,
      total_market_value=excluded.total_market_value,
      total_hold_shares=excluded.total_hold_shares,
      float_ratio=excluded.float_ratio
    """
    cur = conn.execute(sql, (report_date,))
    return cur.rowcount


def current_focus(conn: sqlite3.Connection, report_date: str, limit: int = 100):
    return conn.execute("""
    SELECT s.stock_code, st.stock_name, s.fund_count, s.total_market_value,
           s.total_hold_shares, s.float_ratio
    FROM stock_fund_summary s LEFT JOIN stock st ON st.stock_code=s.stock_code
    WHERE s.report_date=?
    ORDER BY s.fund_count DESC, s.total_market_value DESC
    LIMIT ?
    """, (report_date, limit))
