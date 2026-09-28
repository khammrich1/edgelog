"""Execution-provider abstraction.

TopstepX/ProjectX is the first provider, not the only one EdgeLog will
ever support -- every provider-specific detail (REST endpoints, SignalR
hub names, payload shapes) must live behind this interface, not leak into
the agent's service/CLI layer. ST0 deliberately did not include order
placement/cancellation here. ST1 adds it now, deliberately narrow: only
`place_limit_order` exists (no generic "place_order" with a type
parameter) so the interface itself, not just a runtime check, keeps a
provider from accepting anything but a limit order in this slice.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Optional

from trader_agent.state import ConnectionStatus


@dataclass(frozen=True)
class Account:
    id: int
    name: str
    is_practice: bool
    balance: Optional[float] = None
    raw: dict = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True)
class Contract:
    id: str
    name: str
    description: str
    symbol_id: str
    tick_size: Optional[float] = None
    tick_value: Optional[float] = None
    active: bool = False
    raw: dict = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True)
class Quote:
    contract_id: str
    last_price: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    raw: dict = field(default_factory=dict, repr=False, compare=False)


AccountUpdateHandler = Callable[[dict], None]
QuoteHandler = Callable[[Quote], None]
TradeHandler = Callable[[dict], None]


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """EdgeLog's own order-lifecycle states, deliberately not a
    pass-through of the provider's numeric order-status enum -- the
    reference doc explicitly flags that enum's full values as unverified
    (see docs/integrations/projectx/PROJECTX_API_REFERENCE.md section 12).
    Status here is derived from fields EdgeLog does understand (whether
    *we* successfully submitted/canceled it, and fillVolume vs. size), not
    from guessing what an unconfirmed provider status code means."""

    PENDING_SUBMIT = "pending_submit"
    WORKING = "working"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"


@dataclass(frozen=True)
class PlaceOrderResult:
    success: bool
    provider_order_id: Optional[str]
    error_code: Optional[int]
    error_message: Optional[str]
    raw: dict = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True)
class CancelOrderResult:
    success: bool
    error_code: Optional[int]
    error_message: Optional[str]
    raw: dict = field(default_factory=dict, repr=False, compare=False)


@dataclass(frozen=True)
class Order:
    """One order as reported back by the provider (e.g. via Order/search),
    used only for reconciliation -- EdgeLog's own OrderRecord (see
    order_manager.py) is the authoritative local record of an order it
    submitted."""

    provider_order_id: str
    account_id: int
    contract_id: str
    status: OrderStatus
    side: Optional[OrderSide] = None
    size: int = 0
    limit_price: Optional[float] = None
    fill_volume: int = 0
    filled_price: Optional[float] = None
    custom_tag: Optional[str] = None
    raw: dict = field(default_factory=dict, repr=False, compare=False)


class ExecutionProvider(ABC):
    """One authenticated session against one execution provider (e.g. one
    TopstepX account). Every provider implementation must be safe to
    construct and exercise in tests without any network access."""

    @abstractmethod
    def authenticate(self) -> None:
        """Establishes a valid session. Must raise on failure -- callers
        should never treat "no exception" as ambiguous with "authenticated"."""

    @abstractmethod
    def list_accounts(self) -> list[Account]:
        """Every account visible to this credential, including which ones
        look like Practice accounts (see each provider's own heuristic)."""

    @abstractmethod
    def resolve_contract(self, symbol: str) -> Contract:
        """Finds the currently active tradable contract for a root symbol
        (e.g. "MNQ"). Raises if none can be resolved."""

    @abstractmethod
    def get_current_price(self, contract_id: str) -> Optional[Quote]:
        """The most recently observed quote for a contract, or None if no
        market data has been received yet."""

    @abstractmethod
    def connect_realtime(self) -> None:
        """Opens the real-time connection(s). Must be safe to call again
        after a disconnect -- implementations own their own reconnect
        bookkeeping so callers never accumulate duplicate subscriptions."""

    @abstractmethod
    def subscribe_account_updates(self, account_id: int, on_update: AccountUpdateHandler) -> None:
        """Registers a callback for account/order/position updates for one
        account. Safe to call before connect_realtime(); the subscription
        request is (re-)sent whenever the connection is (re-)established."""

    @abstractmethod
    def subscribe_market_data(
        self,
        contract_id: str,
        on_quote: Optional[QuoteHandler] = None,
        on_trade: Optional[TradeHandler] = None,
    ) -> None:
        """Registers callbacks for quote/trade updates for one contract.
        Same re-subscribe-on-reconnect guarantee as subscribe_account_updates."""

    @abstractmethod
    def disconnect(self) -> None:
        """Tears down the real-time connection(s). Idempotent."""

    @abstractmethod
    def place_limit_order(
        self,
        account_id: int,
        contract_id: str,
        side: OrderSide,
        size: int,
        limit_price: float,
        custom_tag: str,
    ) -> PlaceOrderResult:
        """Submits a limit order. This method performs no safety checks of
        its own (kill switch, max quantity, Practice-only, execution
        capability) -- those all live in OrderManager, the one caller this
        should ever have. Never call this directly from CLI/service code.

        Per the reference doc's implementation rules, presence of a
        provider_order_id on the result never proves success by itself --
        always check `result.success`."""

    @abstractmethod
    def cancel_order(self, account_id: int, provider_order_id: str) -> CancelOrderResult:
        """Cancels a working order. Safe to call even if the local kill
        switch is engaged -- cancels reduce risk and should never be
        blocked by a control meant to stop new risk from being taken on."""

    @abstractmethod
    def search_orders(self, account_id: int, start: datetime, end: Optional[datetime] = None) -> list[Order]:
        """Queries the provider's own order records for reconciliation.
        Read-only -- never places or cancels anything."""

    @property
    @abstractmethod
    def connection_status(self) -> ConnectionStatus:
        ...

    @property
    @abstractmethod
    def is_execution_capable(self) -> bool:
        """False whenever order placement would be unsafe: not
        authenticated, not connected, or market data is stale. ST1's order
        gating should read this rather than re-deriving its own notion of
        "healthy"."""
