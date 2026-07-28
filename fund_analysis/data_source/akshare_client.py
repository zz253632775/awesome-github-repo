"""AKShare data adapter.

All methods return plain dictionaries to keep the analysis layer independent from
pandas. AKShare itself may return DataFrames; conversion is isolated here.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable

LOGGER = logging.getLogger(__name__)


def _records(frame) -> list[dict]:
    if frame is None:
        return []
    if hasattr(frame, "to_dict"):
        return frame.to_dict("records")
    return list(frame)


class AKShareClient:
    def __init__(self) -> None:
        import akshare as ak  # optional runtime dependency
        self.ak = ak

    def fetch_stock_basic(self) -> list[dict]:
        rows = _records(self.ak.stock_info_a_code_name())
        now = datetime.utcnow().isoformat(timespec="seconds")
        result = []
        for row in rows:
            code = str(row.get("code") or row.get("证券代码") or "").zfill(6)
            if code:
                result.append({"stock_code": code, "stock_name": row.get("name") or row.get("证券简称"), "update_time": now})
        return result

    def fetch_fund_positions(self, report_date: str) -> list[dict]:
        """Fetch fund stock holdings for a report date when supported by AKShare.

        AKShare endpoint names change occasionally. This adapter tries common public
        endpoints and normalizes fields. If no endpoint is available, it raises a
        RuntimeError so callers can switch to another free data source adapter.
        """
        candidates = ["fund_portfolio_hold_em", "fund_stock_position_lg"]
        last_error: Exception | None = None
        for name in candidates:
            if not hasattr(self.ak, name):
                continue
            try:
                frame = getattr(self.ak, name)(date=report_date.replace("-", ""))
                rows = _records(frame)
                if rows:
                    return [self._normalize_position(row, report_date) for row in rows]
            except Exception as exc:  # adapter boundary: log and try next public endpoint
                last_error = exc
                LOGGER.warning("AKShare endpoint %s failed: %s", name, exc)
        raise RuntimeError(f"No usable AKShare fund position endpoint for {report_date}: {last_error}")

    def _normalize_position(self, row: dict, report_date: str) -> dict:
        return {
            "fund_code": str(row.get("基金代码") or row.get("fund_code") or "").zfill(6),
            "stock_code": str(row.get("股票代码") or row.get("stock_code") or "").zfill(6),
            "report_date": report_date,
            "hold_shares": float(row.get("持股数") or row.get("hold_shares") or 0),
            "market_value": float(row.get("持仓市值") or row.get("market_value") or 0),
            "fund_nav_ratio": _to_ratio(row.get("占净值比例") or row.get("fund_nav_ratio")),
            "stock_float_ratio": _to_ratio(row.get("占流通股比例") or row.get("stock_float_ratio")),
        }

    def fetch_daily_price(self, stock_code: str, start_date: str, end_date: str) -> list[dict]:
        symbol = stock_code
        frame = self.ak.stock_zh_a_hist(symbol=symbol, start_date=start_date.replace("-", ""), end_date=end_date.replace("-", ""), adjust="qfq")
        return [{"stock_code": stock_code, "trade_date": str(r.get("日期")), "close_price": float(r.get("收盘") or 0)} for r in _records(frame)]


def _to_ratio(value) -> float | None:
    if value in (None, ""):
        return None
    text = str(value).replace("%", "")
    try:
        number = float(text)
    except ValueError:
        return None
    return number / 100 if number > 1 else number
