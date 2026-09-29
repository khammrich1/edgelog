"""Command-line entrypoint: `python -m trader_agent <command>`.

start   -- authenticate, resolve the contract, connect real-time, and run
           until interrupted (Ctrl+C), printing status periodically.
status  -- one-shot authenticate + resolve + connect, print status, exit.
           Useful for verifying setup without leaving the agent running.
order   -- interactively construct, review, and (after typed confirmation)
           submit a Practice-account MNQ limit order. ST1.
cancel  -- cancel a working order by its EdgeLog order tag.
orders  -- list locally tracked orders and their last known status.
kill    -- engage or clear the local emergency stop. Purely local -- does
           not authenticate or touch the network, so it works even if the
           agent/TopstepX connection is down.
"""
from __future__ import annotations

import argparse
import signal
import sys
import time

from trader_agent.config import ConfigError
from trader_agent.order_manager import OrderRejected
from trader_agent.providers.base import OrderSide
from trader_agent.service import TraderAgentService
from trader_agent.trading_control import TradingControl


def _print_status(service: TraderAgentService) -> None:
    status = service.status()
    account = status.practice_account
    contract = status.contract
    price = status.current_price
    print(
        "connection={} execution_capable={} account={} contract={} last_price={} trading_blocked={}".format(
            status.connection_status.value,
            status.is_execution_capable,
            account.id if account else None,
            contract.id if contract else None,
            price.last_price if price else None,
            status.trading_blocked_reason,
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


def cmd_order(_args: argparse.Namespace) -> int:
    """Manual order ticket: review every field, then require the trader to
    type CONFIRM verbatim before anything is sent. This is the sole
    "TAKE TRADE" authorization boundary for ST1 -- there is no other path
    in this codebase that can submit an order."""
    service = TraderAgentService.from_local_config()
    service.start()
    try:
        status = service.status()
        if status.practice_account is None:
            print("No Practice account resolved -- refusing to place an order.", file=sys.stderr)
            return 2
        if status.trading_blocked_reason:
            print(f"Blocked: {status.trading_blocked_reason}", file=sys.stderr)
            return 2
        if not status.is_execution_capable:
            print(
                f"Not execution-capable (connection={status.connection_status.value}). "
                "Refusing to place an order.",
                file=sys.stderr,
            )
            return 2

        side_raw = input("Side (buy/sell): ").strip().lower()
        if side_raw not in ("buy", "sell"):
            print("Side must be 'buy' or 'sell'.", file=sys.stderr)
            return 2
        side = OrderSide.BUY if side_raw == "buy" else OrderSide.SELL

        try:
            size = int(input(f"Quantity (max {service.order_manager.max_quantity}): ").strip())
            limit_price = float(input("Limit price: ").strip())
        except ValueError:
            print("Quantity must be a whole number and limit price a number.", file=sys.stderr)
            return 2

        print("\n--- REVIEW ORDER (Practice account only, limit order only) ---")
        print(f"Account:  {status.practice_account.id} ({status.practice_account.name})")
        print(f"Contract: {status.contract.id} ({status.contract.name})")
        print(f"Side:     {side.value}")
        print(f"Quantity: {size}")
        print(f"Limit:    {limit_price}")
        print("----------------------------------------------------------------")
        confirmation = input("Type CONFIRM to submit this order, anything else cancels: ").strip()
        if confirmation != "CONFIRM":
            print("Not confirmed -- no order sent.")
            return 0

        try:
            record = service.place_limit_order(side, size, limit_price)
        except OrderRejected as exc:
            print(f"Order refused: {exc}", file=sys.stderr)
            return 2

        print(f"Order {record.custom_tag}: status={record.status} provider_order_id={record.provider_order_id}")
        if record.error_message:
            print(f"Provider message: {record.error_message}")
        return 0 if record.status != "rejected" else 1
    finally:
        service.stop()


def cmd_cancel(args: argparse.Namespace) -> int:
    service = TraderAgentService.from_local_config()
    service.start()
    try:
        try:
            record = service.cancel_order(args.custom_tag)
        except OrderRejected as exc:
            print(f"Cancel refused: {exc}", file=sys.stderr)
            return 2
        print(f"Order {record.custom_tag}: status={record.status}")
        if record.error_message:
            print(f"Provider message: {record.error_message}")
        return 0
    finally:
        service.stop()


def cmd_orders(_args: argparse.Namespace) -> int:
    service = TraderAgentService.from_local_config()
    service.start()
    try:
        records = service.order_manager.all_orders()
        if not records:
            print("No locally tracked orders.")
            return 0
        for record in records:
            print(
                f"{record.custom_tag}  status={record.status:<16} side={record.side:<4} size={record.size} "
                f"limit={record.limit_price} provider_order_id={record.provider_order_id} "
                f"updated={record.updated_at}"
            )
        return 0
    finally:
        service.stop()


def cmd_kill(args: argparse.Namespace) -> int:
    """Purely local -- deliberately does not go through TraderAgentService,
    so this works even without a network connection or valid credentials.
    A kill switch that itself required a live connection to engage would
    not be a real kill switch."""
    control = TradingControl()
    if args.clear:
        control.clear_kill_switch()
        print("Kill switch cleared.")
    else:
        reason = args.reason or "manual CLI kill"
        control.engage_kill_switch(reason)
        print(f"Kill switch ENGAGED: {reason}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trader_agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("start", help="Run the agent until interrupted").set_defaults(func=cmd_start)
    subparsers.add_parser("status", help="Connect once, print status, exit").set_defaults(func=cmd_status)
    subparsers.add_parser(
        "order", help="Interactively construct, review, and submit a Practice limit order"
    ).set_defaults(func=cmd_order)

    cancel_parser = subparsers.add_parser("cancel", help="Cancel a working order by its EdgeLog order tag")
    cancel_parser.add_argument("custom_tag")
    cancel_parser.set_defaults(func=cmd_cancel)

    subparsers.add_parser("orders", help="List locally tracked orders and their last known status").set_defaults(
        func=cmd_orders
    )

    kill_parser = subparsers.add_parser("kill", help="Engage or clear the local emergency stop")
    kill_parser.add_argument("--clear", action="store_true", help="Clear an engaged kill switch instead of engaging it")
    kill_parser.add_argument("--reason", help="Reason to record when engaging the kill switch")
    kill_parser.set_defaults(func=cmd_kill)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
