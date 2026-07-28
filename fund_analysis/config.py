"""Configuration for the public fund stock-flow analysis system."""
from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "fund_stock_analysis.db"
REPORT_DIR = BASE_DIR / "reports"
LOG_LEVEL = "INFO"

# Keep at least five years of quarterly reports. Increase if local storage allows.
DEFAULT_LOOKBACK_YEARS = 5

# Risk and signal thresholds.
CROWDED_FLOAT_RATIO = 0.40
FAST_EXIT_FUND_COUNT_DROP = -0.20
LOW_POSITIONING_HOLDING_GROWTH = 0.20
LOW_POSITIONING_MAX_PRICE_RETURN = 0.05
