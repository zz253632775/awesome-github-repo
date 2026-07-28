"""AKShare data adapter.

All methods return plain dictionaries to keep the analysis layer independent from
pandas. AKShare itself may return DataFrames; conversion is isolated here.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Iterable

LOGGER = logging.getLogger(__name__)


def _records(frame) -> list[dict]:
    if frame is None:
        return []
    if hasattr(frame, "to_dict"):
        return frame.to_dict("records")
    return list(frame)


def _first(row: dict, names: Iterable[str], default=None):
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return value
    return default


def _to_float(value, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    try:
        return float(str(value).replace(",", "").replace("%", ""))
    except ValueError:
        return default


class AKShareClient:
    def __init__(self) -> None:
        import akshare as ak  # optional runtime dependency
        self.ak = ak

    def fetch_fund_list(self) -> list[dict]:
        """Return all public funds from Eastmoney via AKShare fund_name_em."""
        rows = _records(self.ak.fund_name_em())
        result = []
        for row in rows:
            code = str(_first(row, ["基金代码", "fund_code", "代码"], "")).strip().zfill(6)
            if code and code != "000000":
                result.append({
                    "fund_code": code,
                    "fund_name": _first(row, ["基金简称", "fund_name", "名称"], ""),
                    "fund_type": _first(row, ["基金类型", "fund_type"], ""),
                })
        return result

    def fetch_stock_basic(self) -> list[dict]:
        rows = _records(self.ak.stock_info_a_code_name())
        now = datetime.utcnow().isoformat(timespec="seconds")
        result = []
        for row in rows:
            code = str(row.get("code") or row.get("证券代码") or "").zfill(6)
            if code:
                result.append({"stock_code": code, "stock_name": row.get("name") or row.get("证券简称"), "update_time": now})
        return result

    def fetch_fund_stock_holdings(self, fund_code: str, year: int, report_date: str | None = None) -> list[dict]:
        """Fetch one fund's stock holdings for a year, optionally filtering a quarter."""
        frame = self.ak.fund_portfolio_hold_em(symbol=str(fund_code).zfill(6), date=str(year))
        rows = []
        for row in _records(frame):
            normalized = self._normalize_position(row, str(fund_code).zfill(6))
            if not normalized:
                continue
            if report_date and normalized["report_date"] != report_date:
                continue
            rows.append(normalized)
        return rows

    def fetch_fund_positions(self, report_date: str) -> list[dict]:
        """Fetch all funds' holdings for one report date by iterating fund_name_em."""
        year = int(report_date[:4])
        rows: list[dict] = []
        for fund in self.fetch_fund_list():
            try:
                rows.extend(self.fetch_fund_stock_holdings(fund["fund_code"], year, report_date))
            except Exception as exc:
                LOGGER.warning("fund_portfolio_hold_em failed for %s %s: %s", fund["fund_code"], report_date, exc)
        return rows

    def _normalize_position(self, row: dict, fund_code: str) -> dict | None:
        stock_code = str(_first(row, ["股票代码", "stock_code", "代码"], "")).strip().zfill(6)
        report_date = _quarter_to_report_date(str(_first(row, ["季度", "report_date"], "")))
        if not stock_code or stock_code == "000000" or not report_date:
            return None
        return {
            "fund_code": fund_code,
            "stock_code": stock_code,
            "report_date": report_date,
            # AKShare documents 持股数 as 万股 and 持仓市值 as 万元.
            "hold_shares": _to_float(_first(row, ["持股数", "hold_shares"])) * 10000,
            "market_value": _to_float(_first(row, ["持仓市值", "market_value"])) * 10000,
            "fund_nav_ratio": _to_ratio(_first(row, ["占净值比例", "fund_nav_ratio"])),
            "stock_float_ratio": _to_ratio(_first(row, ["占流通股比例", "stock_float_ratio"])),
        }

    def fetch_daily_price(self, stock_code: str, start_date: str, end_date: str) -> list[dict]:
        frame = self.ak.stock_zh_a_hist(symbol=stock_code, start_date=start_date.replace("-", ""), end_date=end_date.replace("-", ""), adjust="qfq")
        return [{"stock_code": stock_code, "trade_date": str(r.get("日期")), "close_price": float(r.get("收盘") or 0)} for r in _records(frame)]


def _quarter_to_report_date(text: str) -> str | None:
    match = re.search(r"(20\d{2})年([1-4])季度", text)
    if not match:
        return text[:10] if re.match(r"20\d{2}-\d{2}-\d{2}", text) else None
    year, quarter = int(match.group(1)), int(match.group(2))
    return {1: f"{year}-03-31", 2: f"{year}-06-30", 3: f"{year}-09-30", 4: f"{year}-12-31"}[quarter]


def _to_ratio(value) -> float | None:
    if value in (None, ""):
        return None
    number = _to_float(value, default=-1.0)
    if number < 0:
        return None
    return number / 100 if number > 1 else number
