"""Markdown report generation for public-fund stock-flow trends."""
from __future__ import annotations
from pathlib import Path
import sqlite3


def _table(rows, headers):
    rows = [dict(r) for r in rows]
    if not rows: return "暂无数据\n"
    out = ["|"+"|".join(headers)+"|", "|"+"|".join(["---"]*len(headers))+"|"]
    for r in rows:
        out.append("|"+"|".join(str(r.get(h, "")) for h in headers)+"|")
    return "\n".join(out)+"\n"


def generate_report(conn: sqlite3.Connection, report_date: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"fund_stock_trend_{report_date}.md"
    focus = conn.execute("SELECT stock_code,fund_count,total_market_value,float_ratio FROM stock_fund_summary WHERE report_date=? ORDER BY fund_count DESC,total_market_value DESC LIMIT 100", (report_date,)).fetchall()
    add = conn.execute("SELECT stock_code,fund_count_change,market_value_change,hold_shares_change FROM stock_fund_change WHERE current_period=? ORDER BY market_value_change DESC LIMIT 100", (report_date,)).fetchall()
    exit_rows = conn.execute("SELECT stock_code,fund_count_change,market_value_change,hold_shares_change FROM stock_fund_change WHERE current_period=? ORDER BY market_value_change ASC LIMIT 100", (report_date,)).fetchall()
    crowded = conn.execute("SELECT stock_code,fund_count,total_market_value,float_ratio FROM stock_fund_summary WHERE report_date=? AND float_ratio>0.4 ORDER BY float_ratio DESC LIMIT 100", (report_date,)).fetchall()
    score = conn.execute("SELECT stock_code,score,risk_flags FROM stock_score WHERE report_date=? ORDER BY score DESC LIMIT 100", (report_date,)).fetchall()
    stats = conn.execute("SELECT COUNT(*) signals, AVG(return_3_month) avg_return_3m, AVG(return_6_month) avg_return_6m, AVG(return_12_month) avg_return_12m FROM stock_return_analysis WHERE buy_period=?", (report_date,)).fetchone()
    body = [f"# 公募基金资金趋势选股报告（{report_date}）\n",
            "## 1. 基金当前重仓/关注 TOP100\n", _table(focus, ["stock_code","fund_count","total_market_value","float_ratio"]),
            "## 2. 最近季度基金加仓 TOP100\n", _table(add, ["stock_code","fund_count_change","market_value_change","hold_shares_change"]),
            "## 3. 机构退出 TOP100\n", _table(exit_rows, ["stock_code","fund_count_change","market_value_change","hold_shares_change"]),
            "## 4. 机构拥挤风险\n", _table(crowded, ["stock_code","fund_count","total_market_value","float_ratio"]),
            "## 5. 基金共识评分 TOP100\n", _table(score, ["stock_code","score","risk_flags"]),
            "## 6. 基金增持收益验证\n", _table([stats] if stats else [], ["signals","avg_return_3m","avg_return_6m","avg_return_12m"])]
    path.write_text("\n".join(body), encoding="utf-8")
    return path
