"""Command-line entrypoint: `python -m trader_agent <command>`.

start   -- authenticate, resolve the contract, connect real-time, and run
           until interrupted (Ctrl+C), printing status periodically.
status  -- one-shot authenticate + resolve + connect, print status, exit.
           Useful for verifying setup without leaving the agent running.
"""
from __future__ import annotations

import argparse
import signal
import sys
import time

from trader_agent.config import ConfigError
from trader_agent.service import TraderAgentService


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trader_agent")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("start", help="Run the agent until interrupted").set_defaults(func=cmd_start)
    subparsers.add_parser("status", help="Connect once, print status, exit").set_defaults(func=cmd_status)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
