"""CLI entry point for the public fund stock-flow stock selection system."""
from __future__ import annotations
import argparse, logging
from fund_analysis import config
from fund_analysis.analysis.backtest import analyze_signal_returns
from fund_analysis.analysis.score import calculate_scores
from fund_analysis.analysis.sql_change import build_change
from fund_analysis.analysis.sql_summary import build_summary
from fund_analysis.database.sqlite import get_connection, init_db
from fund_analysis.report.generator import generate_report


def configure_logging() -> None:
    logging.basicConfig(level=getattr(logging, config.LOG_LEVEL), format="%(asctime)s %(levelname)s %(name)s - %(message)s")


def run_pipeline(current_period: str, previous_period: str) -> None:
    init_db(config.DB_PATH)
    with get_connection(config.DB_PATH) as conn:
        build_summary(conn, current_period)
        build_change(conn, current_period, previous_period)
        calculate_scores(conn, current_period)
        analyze_signal_returns(conn, current_period)
        report = generate_report(conn, current_period, config.REPORT_DIR)
        print(f"Report generated: {report}")


def main() -> None:
    parser = argparse.ArgumentParser(description="公募基金资金趋势选股系统")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db")
    pipe = sub.add_parser("run")
    pipe.add_argument("--current-period", required=True, help="Current report date, e.g. 2025-09-30")
    pipe.add_argument("--previous-period", required=True, help="Previous report date, e.g. 2025-06-30")
    args = parser.parse_args()
    configure_logging()
    if args.cmd == "init-db":
        init_db(config.DB_PATH)
    elif args.cmd == "run":
        run_pipeline(args.current_period, args.previous_period)


if __name__ == "__main__":
    main()
