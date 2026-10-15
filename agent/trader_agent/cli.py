"""Command-line entrypoint: `python -m trader_agent <command>`.

start   -- authenticate, resolve the contract, connect real-time, and run
           until interrupted (Ctrl+C), printing status periodically.
status  -- one-shot authenticate + resolve + connect, print status, exit.
           Useful for verifying setup without leaving the agent running.
trades  -- read-only diagnostic: fetch execution/fill history for a date
           range and report which documented /api/Trade/search fields a
           live response actually contains. No database writes, no
           EdgeLog backend calls, no order placement -- see
           trader_agent.trade_diagnostics for the redaction rules this
           applies before printing anything (issue #80 Step 2).
"""
from __future__ import annotations

import argparse
import signal
import sys
import time
from datetime import timedelta

from trader_agent.config import ConfigError, load_config
from trader_agent.service import TraderAgentService
from trader_agent.trade_diagnostics import format_report, redact_identifier, parse_flexible_datetime, summarize_trade_records


def _print_status(service: TraderAgentService) -> None:
    status = service.status()
    account = status.practice_account
    contract = status.contract
    price = status.current_price
    print(
        "connection={} execution_capable={} account={} contract={} last_price={}".format(
            status.connection_status.value,
            status.is_execution_capable,
            account.id if account else None,
            contract.id if contract else None,
            price.last_price if price else None,
        )
    )


def cmd_status(_args: argparse.Namespace) -> int:
    service = TraderAgentService.from_local_config()
    service.start()
    _print_status(service)
    service.stop()
    return 0


def cmd_start(_args: argparse.Namespace) -> int:
    service = TraderAgentService.from_local_config()
    service.start()

    stop_requested = {"value": False}

    def _handle_signal(_signum, _frame) -> None:
        stop_requested["value"] = True

    signal.signal(signal.SIGINT, _handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_signal)

    try:
        while not stop_requested["value"]:
            _print_status(service)
            time.sleep(5)
    finally:
        service.stop()

    return 0


def cmd_trades(args: argparse.Namespace) -> int:
    try:
        start = parse_flexible_datetime(args.start)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    end = None
    if args.end:
        try:
            end = parse_flexible_datetime(args.end)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
    else:
        end = start + timedelta(days=1)

    account_id = args.account_id
    if account_id is None:
        account_id = load_config().practice_account_id
        if account_id is None:
            print(
                "Error: no --account-id given and TOPSTEPX_PRACTICE_ACCOUNT_ID is not set in .env. "
                "Run `python -m trader_agent status` first to find your account ID, or pass --account-id explicitly.",
                file=sys.stderr,
            )
            return 2

    service = TraderAgentService.from_local_config()
    trades = service.search_trades(account_id, start, end)
    report = summarize_trade_records(trades)

    print(f"Account: ...{redact_identifier(account_id)}  Range: {start.isoformat()} to {end.isoformat()}")
    print()
    print(format_report(report))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trader_agent")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("start", help="Run the agent until interrupted").set_defaults(func=cmd_start)
    subparsers.add_parser("status", help="Connect once, print status, exit").set_defaults(func=cmd_status)

    trades_parser = subparsers.add_parser(
        "trades",
        help=(
            "Read-only diagnostic: fetch execution/fill history for a date range and report "
            "which documented /api/Trade/search fields a live response actually contains. "
            "No database writes, no EdgeLog backend calls, no order placement."
        ),
    )
    trades_parser.add_argument(
        "--start", required=True, help="Start of the range: YYYY-MM-DD or a full ISO-8601 datetime"
    )
    trades_parser.add_argument("--end", default=None, help="End of the range (default: 24h after --start)")
    trades_parser.add_argument(
        "--account-id",
        type=int,
        default=None,
        help="TopstepX account ID to query (default: TOPSTEPX_PRACTICE_ACCOUNT_ID from .env)",
    )
    trades_parser.set_defaults(func=cmd_trades)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
