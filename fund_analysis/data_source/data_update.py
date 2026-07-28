"""Incremental data update orchestration."""
from __future__ import annotations
import logging, sqlite3
from datetime import datetime
from fund_analysis.collector.fund_position_collector import collect_period
from fund_analysis.database.sqlite import upsert_many

LOGGER = logging.getLogger(__name__)


def update_stock_basic(conn: sqlite3.Connection, client) -> int:
    rows = client.fetch_stock_basic()
    sql = """INSERT INTO stock(stock_code,stock_name,update_time) VALUES (:stock_code,:stock_name,:update_time)
    ON CONFLICT(stock_code) DO UPDATE SET stock_name=excluded.stock_name, update_time=excluded.update_time"""
    return upsert_many(conn, sql, rows)


def update_fund_positions(conn: sqlite3.Connection, client, report_date: str) -> int:
    return collect_period(conn, client, report_date)


def update_daily_prices(conn: sqlite3.Connection, client, stock_codes: list[str], start_date: str, end_date: str) -> int:
    rows = []
    for code in stock_codes:
        try:
            rows.extend(client.fetch_daily_price(code, start_date, end_date))
        except Exception as exc:
            LOGGER.warning("Price update failed for %s: %s", code, exc)
    sql = "INSERT OR REPLACE INTO stock_daily_price(stock_code,trade_date,close_price) VALUES (:stock_code,:trade_date,:close_price)"
    return upsert_many(conn, sql, rows)
