"""Execution-provider abstraction.

TopstepX/ProjectX is the first provider, not the only one EdgeLog will
ever support -- every provider-specific detail (REST endpoints, SignalR
hub names, payload shapes) must live behind this interface, not leak into
the agent's service/CLI layer. ST0 deliberately does not include order
placement/cancellation here: that's ST1's job to add, once the risk/kill
controls that should gate it exist.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
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
