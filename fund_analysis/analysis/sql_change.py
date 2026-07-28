"""SQL calculation for quarter-over-quarter stock fund-flow changes."""
from __future__ import annotations
import sqlite3


def build_change(conn: sqlite3.Connection, current_period: str, previous_period: str) -> int:
    sql = """
    INSERT INTO stock_fund_change
      (stock_code,current_period,previous_period,fund_count_change,fund_count_growth,
       market_value_change,market_value_growth,hold_shares_change,hold_shares_growth)
    SELECT c.stock_code, c.report_date, ?,
           c.fund_count - COALESCE(p.fund_count,0),
           CASE WHEN COALESCE(p.fund_count,0)>0 THEN 1.0*(c.fund_count-p.fund_count)/p.fund_count ELSE NULL END,
           c.total_market_value - COALESCE(p.total_market_value,0),
           CASE WHEN COALESCE(p.total_market_value,0)>0 THEN 1.0*(c.total_market_value-p.total_market_value)/p.total_market_value ELSE NULL END,
           c.total_hold_shares - COALESCE(p.total_hold_shares,0),
           CASE WHEN COALESCE(p.total_hold_shares,0)>0 THEN 1.0*(c.total_hold_shares-p.total_hold_shares)/p.total_hold_shares ELSE NULL END
    FROM stock_fund_summary c
    LEFT JOIN stock_fund_summary p ON p.stock_code=c.stock_code AND p.report_date=?
    WHERE c.report_date=?
    ON CONFLICT(stock_code,current_period,previous_period) DO UPDATE SET
      fund_count_change=excluded.fund_count_change,
      fund_count_growth=excluded.fund_count_growth,
      market_value_change=excluded.market_value_change,
      market_value_growth=excluded.market_value_growth,
      hold_shares_change=excluded.hold_shares_change,
      hold_shares_growth=excluded.hold_shares_growth
    """
    return conn.execute(sql, (previous_period, previous_period, current_period)).rowcount


def ranked_changes(conn: sqlite3.Connection, current_period: str, metric: str, limit: int = 100, ascending: bool = False):
    allowed = {"fund_count_change", "fund_count_growth", "market_value_change", "market_value_growth", "hold_shares_change", "hold_shares_growth"}
    if metric not in allowed:
        raise ValueError(f"Unsupported metric: {metric}")
    direction = "ASC" if ascending else "DESC"
    return conn.execute(f"""
    SELECT c.*, s.stock_name FROM stock_fund_change c LEFT JOIN stock s ON s.stock_code=c.stock_code
    WHERE c.current_period=? ORDER BY {metric} {direction} LIMIT ?
    """, (current_period, limit))


def industry_flow(conn: sqlite3.Connection, current_period: str, limit: int = 50):
    return conn.execute("""
    SELECT COALESCE(st.industry,'未分类') AS industry,
           SUM(c.fund_count_change) AS fund_count_change,
           SUM(c.market_value_change) AS market_value_change
    FROM stock_fund_change c LEFT JOIN stock st ON st.stock_code=c.stock_code
    WHERE c.current_period=?
    GROUP BY COALESCE(st.industry,'未分类')
    ORDER BY market_value_change DESC LIMIT ?
    """, (current_period, limit))
