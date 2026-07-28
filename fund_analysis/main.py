"""CLI entry point for the public fund stock-flow stock selection system."""
from __future__ import annotations
import argparse, logging
from datetime import date
from fund_analysis import config
from fund_analysis.analysis.backtest import analyze_signal_returns
from fund_analysis.analysis.score import calculate_scores
from fund_analysis.analysis.sql_change import build_change
from fund_analysis.analysis.sql_summary import build_summary
from fund_analysis.data_source.akshare_client import AKShareClient
from fund_analysis.data_source.data_update import update_all_fund_positions, update_stock_basic
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


def run_update_data(
    start_year: int,
    end_year: int,
    sleep_seconds: float,
    max_funds: int | None,
    skip_stock_basic: bool,
    no_retry_failed: bool,
) -> None:
    init_db(config.DB_PATH)
    client = AKShareClient()
    with get_connection(config.DB_PATH) as conn:
        if not skip_stock_basic:
            stock_count = update_stock_basic(conn, client)
            print(f"Stock basic rows updated: {stock_count}")
        result = update_all_fund_positions(
            conn,
            client,
            start_year=start_year,
            end_year=end_year,
            sleep_seconds=sleep_seconds,
            max_funds=max_funds,
            retry_failed=not no_retry_failed,
        )
        print(
            "Fund position update finished: "
            f"funds_seen={result.funds_seen}, success={result.tasks_success}, "
            f"failed={result.tasks_failed}, rows_saved={result.rows_saved}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="公募基金资金趋势选股系统")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db")

    update = sub.add_parser("update-data", help="自动拉取全部公募基金股票持仓并写入 SQLite")
    update.add_argument("--start-year", type=int, default=date.today().year - config.DEFAULT_LOOKBACK_YEARS + 1)
    update.add_argument("--end-year", type=int, default=date.today().year)
    update.add_argument("--sleep-seconds", type=float, default=0.2, help="每个基金季度任务之间的休眠秒数，降低公开接口限流风险")
    update.add_argument("--max-funds", type=int, default=None, help="调试用：只采集前 N 只基金")
    update.add_argument("--skip-stock-basic", action="store_true", help="跳过股票基础信息更新")
    update.add_argument("--no-retry-failed", action="store_true", help="不重试之前失败的采集任务")

    pipe = sub.add_parser("run")
    pipe.add_argument("--current-period", required=True, help="Current report date, e.g. 2025-09-30")
    pipe.add_argument("--previous-period", required=True, help="Previous report date, e.g. 2025-06-30")
    args = parser.parse_args()
    configure_logging()
    if args.cmd == "init-db":
        init_db(config.DB_PATH)
    elif args.cmd == "update-data":
        run_update_data(args.start_year, args.end_year, args.sleep_seconds, args.max_funds, args.skip_stock_basic, args.no_retry_failed)
    elif args.cmd == "run":
        run_pipeline(args.current_period, args.previous_period)


if __name__ == "__main__":
    main()
