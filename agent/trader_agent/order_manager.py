"""Local order lifecycle management for ST1.

This is the one place a manually-approved order ticket turns into a
provider call. Every safety gate the issue requires -- kill switch, max
quantity, Practice-account-only, execution-capable (not disconnected/not
stale) -- is enforced here, in one spot, so the CLI layer can't
accidentally bypass one of them by calling the provider directly. It also
owns the local, restart-safe order store used for duplicate-submission
protection and reconciliation.

See docs/integrations/projectx/PROJECTX_API_REFERENCE.md section 10,
rules 7-9: every provider request needs idempotency protection (customTag
alone isn't enough -- local state reconciliation matters too), reconcile
before enabling execution, and never treat presence of an orderId as
proof of success.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from trader_agent.logging_setup import audit
from trader_agent.providers.base import Account, Contract, ExecutionProvider, OrderSide, OrderStatus
from trader_agent.trading_control import TradingControl

AGENT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_STORE_PATH = AGENT_DIR / ".state" / "orders.json"

logger = logging.getLogger("trader_agent.order_manager")

_OPEN_STATUSES = (OrderStatus.PENDING_SUBMIT.value, OrderStatus.WORKING.value, OrderStatus.PARTIALLY_FILLED.value)
_TERMINAL_STATUSES = (OrderStatus.CANCELED.value, OrderStatus.REJECTED.value, OrderStatus.FILLED.value)


class OrderRejected(Exception):
    """Raised when an order ticket is refused before it ever reaches the
    provider: kill switch engaged, non-Practice account, quantity over the
    configured POC maximum, not execution-capable, or a duplicate of an
    already-open order. Never wraps a provider-side rejection -- that
    comes back as a PlaceOrderResult with success=False and is recorded,
    not raised."""


@dataclass
class OrderRecord:
    """EdgeLog's own local record of one order attempt. This is what
    survives a restart and what duplicate-submission protection checks
    against -- provider state alone isn't enough, since a crash between
    "request sent" and "response received" would otherwise be
    indistinguishable from "never sent"."""

    custom_tag: str
    account_id: int
    contract_id: str
    side: str
    size: int
    limit_price: float
    status: str
    provider_order_id: Optional[str] = None
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class OrderManager:
    def __init__(
        self,
        provider: ExecutionProvider,
        trading_control: Optional[TradingControl] = None,
        store_path: Optional[Path] = None,
        max_quantity: int = 1,
    ):
        self._provider = provider
        self._trading_control = trading_control or TradingControl()
        self._store_path = store_path or DEFAULT_STORE_PATH
        self._max_quantity = max_quantity
        self._orders: dict[str, OrderRecord] = self._load()

    @property
    def max_quantity(self) -> int:
        return self._max_quantity

    # -- persistence --

    def _load(self) -> dict[str, OrderRecord]:
        if not self._store_path.exists():
            return {}
        try:
            raw = json.loads(self._store_path.read_text())
        except json.JSONDecodeError:
            audit(logger, "order_manager.store_unreadable", level=logging.WARNING, path=str(self._store_path))
            return {}
        valid_fields = {f.name for f in OrderRecord.__dataclass_fields__.values()}
        return {
            tag: OrderRecord(**{k: v for k, v in fields.items() if k in valid_fields}) for tag, fields in raw.items()
        }

    def _save(self) -> None:
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._store_path.write_text(json.dumps({tag: asdict(rec) for tag, rec in self._orders.items()}, indent=2))

    # -- queries --

    def open_orders(self) -> list[OrderRecord]:
        return [o for o in self._orders.values() if o.status in _OPEN_STATUSES]

    def all_orders(self) -> list[OrderRecord]:
        return sorted(self._orders.values(), key=lambda o: o.created_at)

    def get(self, custom_tag: str) -> Optional[OrderRecord]:
        return self._orders.get(custom_tag)

    # -- submission --

    def submit_limit_order(
        self, account: Account, contract: Contract, side: OrderSide, size: int, limit_price: float
    ) -> OrderRecord:
        self._guard_submission(account, size)

        duplicate = self._find_duplicate(account.id, contract.id, side, size, limit_price)
        if duplicate is not None:
            raise OrderRejected(
                f"An order with the same account/contract/side/size/price is already "
                f"{duplicate.status} (tag={duplicate.custom_tag}, "
                f"provider_order_id={duplicate.provider_order_id}). Cancel it first if you intended a new order."
            )

        custom_tag = f"edgelog-{uuid.uuid4().hex[:16]}"
        record = OrderRecord(
            custom_tag=custom_tag,
            account_id=account.id,
            contract_id=contract.id,
            side=side.value,
            size=size,
            limit_price=limit_price,
            status=OrderStatus.PENDING_SUBMIT.value,
        )
        self._orders[custom_tag] = record
        self._save()
        audit(
            logger,
            "order.submitting",
            custom_tag=custom_tag,
            account_id=account.id,
            contract_id=contract.id,
            side=side.value,
            size=size,
            limit_price=limit_price,
        )

        result = self._provider.place_limit_order(
            account_id=account.id,
            contract_id=contract.id,
            side=side,
            size=size,
            limit_price=limit_price,
            custom_tag=custom_tag,
        )

        # Reference doc rule 9: presence of orderId never proves success --
        # status is driven by result.success, not by whether
        # provider_order_id came back set.
        record.provider_order_id = result.provider_order_id
        record.error_code = result.error_code
        record.error_message = result.error_message
        record.status = (OrderStatus.WORKING if result.success else OrderStatus.REJECTED).value
        record.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()

        audit(
            logger,
            "order.submit_result",
            level=logging.INFO if result.success else logging.WARNING,
            custom_tag=custom_tag,
            success=result.success,
            provider_order_id=result.provider_order_id,
            error_code=result.error_code,
            error_message=result.error_message,
        )
        return record

    def cancel(self, custom_tag: str, account: Account) -> OrderRecord:
        record = self._orders.get(custom_tag)
        if record is None:
            raise OrderRejected(f"No local order record for tag {custom_tag}")
        if record.status not in (OrderStatus.WORKING.value, OrderStatus.PARTIALLY_FILLED.value):
            raise OrderRejected(f"Order {custom_tag} is {record.status}, not cancelable")
        if record.provider_order_id is None:
            raise OrderRejected(f"Order {custom_tag} has no provider order id yet -- cannot cancel")

        # Deliberately not gated on the kill switch -- see module docstring.
        audit(
            logger,
            "order.canceling",
            custom_tag=custom_tag,
            provider_order_id=record.provider_order_id,
            kill_switch_engaged=self._trading_control.kill_switch_engaged,
        )

        result = self._provider.cancel_order(account_id=account.id, provider_order_id=record.provider_order_id)
        if result.success:
            record.status = OrderStatus.CANCELED.value
        record.error_code = result.error_code
        record.error_message = result.error_message
        record.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()

        audit(
            logger,
            "order.cancel_result",
            level=logging.INFO if result.success else logging.WARNING,
            custom_tag=custom_tag,
            success=result.success,
            error_code=result.error_code,
            error_message=result.error_message,
        )
        return record

    # -- reconciliation --

    def reconcile(self, account: Account, since: datetime) -> None:
        """Pulls the provider's own order history for the account and
        overlays fill/size information onto local records that are still
        tracked as open. Read-only with respect to submission decisions --
        never places or cancels anything on its own (rule 8: reconcile
        before enabling execution, don't act on it blindly)."""
        try:
            provider_orders = self._provider.search_orders(account.id, since)
        except Exception as exc:  # noqa: BLE001 -- reconciliation must never crash agent startup
            audit(logger, "order_manager.reconcile_failed", level=logging.WARNING, error=str(exc))
            return

        by_provider_id = {o.provider_order_id: o for o in provider_orders if o.provider_order_id}
        changed = False
        for record in self._orders.values():
            if record.provider_order_id is None or record.status in _TERMINAL_STATUSES:
                continue
            live = by_provider_id.get(record.provider_order_id)
            if live is None:
                continue
            if live.status.value != record.status:
                audit(
                    logger,
                    "order.reconciled_status_change",
                    custom_tag=record.custom_tag,
                    old_status=record.status,
                    new_status=live.status.value,
                )
                record.status = live.status.value
                record.updated_at = datetime.now(timezone.utc).isoformat()
                changed = True
        if changed:
            self._save()

    def apply_realtime_update(self, payload: object) -> None:
        """Feeds a GatewayUserOrder realtime event into local order state.
        Best-effort: the exact realtime order payload shape is
        cross-referenced, not independently verified (see the reference
        doc's "Gaps" section) -- this only ever updates a record it can
        positively match by customTag, and never raises."""
        item = payload[0] if isinstance(payload, list) and payload else payload
        if not isinstance(item, dict):
            return
        custom_tag = item.get("customTag")
        record = self._orders.get(custom_tag) if custom_tag else None
        if record is None or record.status in _TERMINAL_STATUSES:
            return

        size = item.get("size") if item.get("size") is not None else record.size
        fill_volume = item.get("fillVolume") or 0
        if fill_volume >= size and size > 0:
            new_status = OrderStatus.FILLED
        elif fill_volume > 0:
            new_status = OrderStatus.PARTIALLY_FILLED
        else:
            new_status = OrderStatus.WORKING

        if new_status.value != record.status:
            audit(
                logger,
                "order.realtime_status_change",
                custom_tag=custom_tag,
                old_status=record.status,
                new_status=new_status.value,
            )
            record.status = new_status.value
            record.updated_at = datetime.now(timezone.utc).isoformat()
            self._save()

    # -- guards --

    def _guard_submission(self, account: Account, size: int) -> None:
        if not account.is_practice:
            raise OrderRejected(f"Refusing to trade non-Practice account {account.id} ({account.name})")
        if size <= 0:
            raise OrderRejected("Order size must be positive")
        if size > self._max_quantity:
            raise OrderRejected(f"Order size {size} exceeds the configured POC maximum of {self._max_quantity}")
        if not self._provider.is_execution_capable:
            raise OrderRejected(
                f"Not execution-capable (connection={self._provider.connection_status.value}) -- "
                "refusing to submit an order while disconnected or market data is stale"
            )
        block_reason = self._trading_control.block_reason()
        if block_reason:
            raise OrderRejected(block_reason)

    def _find_duplicate(
        self, account_id: int, contract_id: str, side: OrderSide, size: int, limit_price: float
    ) -> Optional[OrderRecord]:
        for record in self._orders.values():
            if record.status not in _OPEN_STATUSES:
                continue
            if (record.account_id, record.contract_id, record.side, record.size, record.limit_price) == (
                account_id,
                contract_id,
                side.value,
                size,
                limit_price,
            ):
                return record
        return None
