"""Python scoring model for institutional fund consensus."""
from __future__ import annotations
import json, sqlite3
from datetime import datetime
from fund_analysis import config


def _cap(value: float | None, scale: float) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(1.0, value / scale))


def calculate_scores(conn: sqlite3.Connection, report_date: str) -> int:
    rows = conn.execute("""
    SELECT c.stock_code, c.fund_count_growth, c.market_value_growth, s.fund_count, s.float_ratio,
           (SELECT COUNT(*) FROM stock_fund_change x WHERE x.stock_code=c.stock_code
            AND x.current_period<=c.current_period AND x.fund_count_change>0 AND x.market_value_change>0) AS positive_quarters
    FROM stock_fund_change c JOIN stock_fund_summary s ON s.stock_code=c.stock_code AND s.report_date=c.current_period
    WHERE c.current_period=?
    """, (report_date,)).fetchall()
    now = datetime.utcnow().isoformat(timespec="seconds")
    payload = []
    for r in rows:
        score = 30*_cap(r["fund_count_growth"], 0.5) + 25*_cap(r["market_value_growth"], 0.5)
        score += 20*min(1.0, (r["positive_quarters"] or 0)/4) + 15*min(1.0, (r["fund_count"] or 0)/500)
        float_ratio = r["float_ratio"]
        reasonable = 1.0 if float_ratio is None or float_ratio <= config.CROWDED_FLOAT_RATIO else 0.2
        score += 10*reasonable
        flags = []
        if float_ratio is not None and float_ratio > config.CROWDED_FLOAT_RATIO:
            flags.append("机构拥挤风险")
        if r["fund_count_growth"] is not None and r["fund_count_growth"] < config.FAST_EXIT_FUND_COUNT_DROP:
            flags.append("机构快速撤退")
        payload.append((r["stock_code"], report_date, round(score, 2), json.dumps(flags, ensure_ascii=False), now))
    conn.executemany("""INSERT INTO stock_score(stock_code,report_date,score,risk_flags,created_at)
    VALUES (?,?,?,?,?) ON CONFLICT(stock_code,report_date) DO UPDATE SET score=excluded.score,risk_flags=excluded.risk_flags,created_at=excluded.created_at""", payload)
    return len(payload)
