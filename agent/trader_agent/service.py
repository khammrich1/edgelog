"""Agent orchestration: wires config, logging, and a provider together,
and exposes the start/stop/status surface the CLI (and, eventually, a
local status file EdgeLog cloud can read) drives."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from trader_agent.config import AgentConfig, load_config
from trader_agent.logging_setup import audit, setup_logging
from trader_agent.order_manager import OrderManager, OrderRecord, OrderRejected
from trader_agent.providers.base import Account, Contract, ExecutionProvider, OrderSide, Quote
from trader_agent.providers.topstepx.client import TopstepXRestClient
from trader_agent.providers.topstepx.provider import TopstepXProvider
from trader_agent.state import ConnectionStatus
from trader_agent.trading_control import TradingControl

# How far back to pull provider order history for reconciliation on
# startup. ST1 orders are short-lived POC tickets, not multi-day swings --
# a generous-but-bounded window is enough to catch anything this agent
# might have submitted in a prior run.
RECONCILE_LOOKBACK = timedelta(hours=24)


@dataclass(frozen=True)
class AgentStatus:
    connection_status: ConnectionStatus
    is_execution_capable: bool
    practice_account: Optional[Account]
    contract: Optional[Contract]
    current_price: Optional[Quote]
    trading_blocked_reason: Optional[str] = None


class TraderAgentService:
    """Not a Windows Service (yet) -- a long-running foreground process
    for ST0. Wrapping it as an actual Windows Service is a documented
    follow-up, not required for this issue's acceptance criteria."""

    def __init__(
        self,
        config: AgentConfig,
        provider: ExecutionProvider,
        trading_control: Optional[TradingControl] = None,
        order_manager: Optional[OrderManager] = None,
    ):
        self._config = config
        self._provider = provider
        self._practice_account: Optional[Account] = None
        self._contract: Optional[Contract] = None
        self.logger = logging.getLogger("trader_agent.service")
        self._trading_control = trading_control or TradingControl()
        self._order_manager = order_manager or OrderManager(
            provider, trading_control=self._trading_control, max_quantity=config.max_order_quantity
        )

    @classmethod
    def from_local_config(cls, provider_factory=None) -> "TraderAgentService":
        config = load_config()
        setup_logging(secrets_provider=lambda: [config.api_key])
        logger = logging.getLogger("trader_agent.service")
        audit(logger, "config.loaded", masked_api_key=config.masked_api_key(), symbol=config.symbol)

        rest_client = TopstepXRestClient(config.api_base_url, config.username, config.api_key)
        provider = (provider_factory or TopstepXProvider)(
            rest_client=rest_client,
            rtc_base_url=config.rtc_base_url,
            stale_after_seconds=config.stale_after_seconds,
            practice_account_id=config.practice_account_id,
        )
        return cls(config, provider)

    @property
    def order_manager(self) -> OrderManager:
        return self._order_manager

    @property
    def trading_control(self) -> TradingControl:
        return self._trading_control

    def start(self) -> None:
        audit(self.logger, "agent.starting")
        self._provider.authenticate()
        audit(self.logger, "agent.authenticated")

        if hasattr(self._provider, "get_practice_account"):
            self._practice_account = self._provider.get_practice_account()  # type: ignore[attr-defined]
        if self._practice_account is None:
            audit(self.logger, "agent.no_practice_account_found", level=logging.WARNING)
        else:
            audit(self.logger, "agent.practice_account_selected", account_id=self._practice_account.id)

        self._contract = self._provider.resolve_contract(self._config.symbol)
        audit(self.logger, "agent.contract_resolved", contract_id=self._contract.id, symbol=self._config.symbol)

        # Rule 8: reconcile provider order state before enabling execution
        # -- a prior run's orders should never be re-discovered as
        # surprises after a restart.
        if self._practice_account is not None:
            since = datetime.now(timezone.utc) - RECONCILE_LOOKBACK
            self._order_manager.reconcile(self._practice_account, since=since)
            audit(self.logger, "agent.orders_reconciled", open_order_count=len(self._order_manager.open_orders()))

        self._provider.connect_realtime()
        if self._practice_account is not None:
            self._provider.subscribe_account_updates(self._practice_account.id, self._on_account_update)
        self._provider.subscribe_market_data(self._contract.id, on_quote=self._on_quote, on_trade=self._on_trade)
        audit(self.logger, "agent.started")

    def stop(self) -> None:
        self._provider.disconnect()
        audit(self.logger, "agent.stopped")

    def status(self) -> AgentStatus:
        current_price = self._provider.get_current_price(self._contract.id) if self._contract else None
        return AgentStatus(
            connection_status=self._provider.connection_status,
            is_execution_capable=self._provider.is_execution_capable,
            practice_account=self._practice_account,
            contract=self._contract,
            current_price=current_price,
            trading_blocked_reason=self._trading_control.block_reason(),
        )

    def place_limit_order(self, side: OrderSide, size: int, limit_price: float) -> OrderRecord:
        """The only order-submission entry point CLI/future callers should
        use -- delegates every safety check to OrderManager. Raises
        OrderRejected (not caught here) if the agent hasn't fully started
        (no account/contract resolved yet)."""
        if self._practice_account is None or self._contract is None:
            raise OrderRejected("Agent is not fully started -- no Practice account/contract resolved yet")
        return self._order_manager.submit_limit_order(self._practice_account, self._contract, side, size, limit_price)

    def cancel_order(self, custom_tag: str) -> OrderRecord:
        if self._practice_account is None:
            raise OrderRejected("Agent is not fully started -- no Practice account resolved yet")
        return self._order_manager.cancel(custom_tag, self._practice_account)

    def _on_account_update(self, event: dict) -> None:
        audit(self.logger, "agent.account_update", kind=event.get("kind"))
        if event.get("kind") == "order":
            self._order_manager.apply_realtime_update(event.get("payload"))

    def _on_quote(self, quote: Quote) -> None:
        audit(self.logger, "agent.quote", contract_id=quote.contract_id, last_price=quote.last_price)

    def _on_trade(self, trade: dict) -> None:
        audit(self.logger, "agent.market_trade")
