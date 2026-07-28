"""Collectors and cleaners for raw public-fund holdings."""
from __future__ import annotations

import logging
import sqlite3
from typing import Iterable

from fund_analysis.database.sqlite import upsert_many

LOGGER = logging.getLogger(__name__)


def clean_position(row: dict) -> dict | None:
    fund_code = str(row.get("fund_code") or "").strip().zfill(6)
    stock_code = str(row.get("stock_code") or "").strip().zfill(6)
    report_date = str(row.get("report_date") or "").strip()
    if not fund_code or not stock_code or not report_date or fund_code == "000000" or stock_code == "000000":
        return None
    return {
        "fund_code": fund_code,
        "stock_code": stock_code,
        "report_date": report_date,
        "hold_shares": float(row.get("hold_shares") or 0),
        "market_value": float(row.get("market_value") or 0),
        "fund_nav_ratio": row.get("fund_nav_ratio"),
        "stock_float_ratio": row.get("stock_float_ratio"),
    }


def save_positions(conn: sqlite3.Connection, rows: Iterable[dict]) -> int:
    cleaned = [r for r in (clean_position(row) for row in rows) if r]
    sql = """
    INSERT INTO fund_stock_position
      (fund_code, stock_code, report_date, hold_shares, market_value, fund_nav_ratio, stock_float_ratio)
    VALUES
      (:fund_code, :stock_code, :report_date, :hold_shares, :market_value, :fund_nav_ratio, :stock_float_ratio)
    ON CONFLICT(fund_code, stock_code, report_date) DO UPDATE SET
      hold_shares=excluded.hold_shares,
      market_value=excluded.market_value,
      fund_nav_ratio=excluded.fund_nav_ratio,
      stock_float_ratio=excluded.stock_float_ratio
    """
    count = upsert_many(conn, sql, cleaned)
    LOGGER.info("Saved %s cleaned fund position rows", count)
    return count


def collect_period(conn: sqlite3.Connection, client, report_date: str) -> int:
    return save_positions(conn, client.fetch_fund_positions(report_date))
