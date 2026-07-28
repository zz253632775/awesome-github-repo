"""Batch collection for all public-fund stock holdings.

The collector persists task status in SQLite so long-running free public-interface
jobs can be safely resumed after network failures or rate limits.
"""
from __future__ import annotations

import logging
import sqlite3
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from fund_analysis.collector.fund_position_collector import save_positions

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class BatchCollectResult:
    funds_seen: int
    tasks_success: int
    tasks_failed: int
    rows_saved: int


def quarter_report_dates(start_year: int, end_year: int) -> list[str]:
    periods = []
    for year in range(start_year, end_year + 1):
        periods.extend([f"{year}-03-31", f"{year}-06-30", f"{year}-09-30", f"{year}-12-31"])
    return periods


def collect_all_fund_positions(
    conn: sqlite3.Connection,
    client,
    start_year: int,
    end_year: int,
    sleep_seconds: float = 0.2,
    max_funds: int | None = None,
    retry_failed: bool = True,
) -> BatchCollectResult:
    """Collect every fund's yearly holding page and persist rows by quarter.

    AKShare's Eastmoney holding endpoint returns all quarters in one year for a
    given fund. The collector therefore calls the provider once per fund-year,
    then marks the four quarter tasks from that year according to returned rows.
    """
    funds = client.fetch_fund_list()
    if max_funds:
        funds = funds[:max_funds]
    tasks_success = tasks_failed = rows_saved = 0
    for fund in funds:
        fund_code = fund["fund_code"]
        for year in range(start_year, end_year + 1):
            periods = quarter_report_dates(year, year)
            pending = [period for period in periods if not _should_skip(conn, fund_code, period, retry_failed)]
            if not pending:
                continue
            for period in pending:
                _mark_task(conn, fund_code, period, "running")
            try:
                rows = client.fetch_fund_stock_holdings(fund_code, year)
                saved = save_positions(conn, rows)
                conn.commit()
                rows_saved += saved
                counts = Counter(row["report_date"] for row in rows)
                for period in pending:
                    tasks_success += 1
                    _mark_task(conn, fund_code, period, "success", row_count=counts.get(period, 0))
            except Exception as exc:
                conn.rollback()
                LOGGER.warning("Collect failed fund=%s year=%s: %s", fund_code, year, exc)
                for period in pending:
                    tasks_failed += 1
                    _mark_task(conn, fund_code, period, "failed", error_message=str(exc))
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
    return BatchCollectResult(len(funds), tasks_success, tasks_failed, rows_saved)


def _should_skip(conn: sqlite3.Connection, fund_code: str, report_date: str, retry_failed: bool) -> bool:
    row = conn.execute("""
    SELECT status FROM data_update_log
    WHERE source='akshare' AND task_type='fund_position' AND fund_code=? AND stock_code='' AND report_date=?
    """, (fund_code, report_date)).fetchone()
    if not row:
        return False
    if row["status"] == "success":
        return True
    return row["status"] == "failed" and not retry_failed


def _mark_task(
    conn: sqlite3.Connection,
    fund_code: str,
    report_date: str,
    status: str,
    row_count: int = 0,
    error_message: str | None = None,
) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    conn.execute("""
    INSERT INTO data_update_log
      (source, task_type, fund_code, stock_code, report_date, start_time, end_time, status, row_count, error_message, retry_count)
    VALUES ('akshare', 'fund_position', ?, '', ?, ?, ?, ?, ?, ?, CASE WHEN ?='failed' THEN 1 ELSE 0 END)
    ON CONFLICT(source, task_type, fund_code, stock_code, report_date) DO UPDATE SET
      start_time=CASE WHEN excluded.status='running' THEN excluded.start_time ELSE data_update_log.start_time END,
      end_time=excluded.end_time,
      status=excluded.status,
      row_count=excluded.row_count,
      error_message=excluded.error_message,
      retry_count=data_update_log.retry_count + CASE WHEN excluded.status='failed' THEN 1 ELSE 0 END
    """, (fund_code, report_date, now, now, status, row_count, error_message, status))
    conn.commit()
