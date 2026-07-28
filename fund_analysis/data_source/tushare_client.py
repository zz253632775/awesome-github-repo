"""Tushare free-interface placeholder adapter.

The project is source-replaceable. Tushare free quota and endpoint availability vary,
so this adapter documents the interface used by collectors without requiring a token.
"""
from __future__ import annotations


class TushareClient:
    def fetch_stock_basic(self) -> list[dict]:
        raise NotImplementedError("Configure a free Tushare token and map stock_basic fields here.")

    def fetch_fund_positions(self, report_date: str) -> list[dict]:
        raise NotImplementedError("Map free Tushare fund holdings fields to the canonical schema here.")

    def fetch_daily_price(self, stock_code: str, start_date: str, end_date: str) -> list[dict]:
        raise NotImplementedError("Map free Tushare daily price fields to the canonical schema here.")
