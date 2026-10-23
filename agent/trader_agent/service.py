"""Agent orchestration: wires config, logging, and a provider together,
and exposes the start/stop/status surface the CLI (and, eventually, a
local status file EdgeLog cloud can read) drives."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from trader_agent.config import AgentConfig, load_config
from trader_agent.logging_setup import audit, setup_logging
from trader_agent.providers.base import Account, Contract, ExecutionProvider, Quote, TradeRecord
from trader_agent.providers.topstepx.client import TopstepXRestClient
from trader_agent.providers.topstepx.provider import TopstepXProvider
from trader_agent.state import ConnectionStatus
from trader_agent.trade_diagnostics import redact_identifier, to_utc_iso


@dataclass(frozen=True)
class AgentStatus:
    connection_status: ConnectionStatus
    is_execution_capable: bool
    practice_account: Optional[Account]
    contract: Optional[Contract]
    current_price: Optional[Quote]


class TraderAgentService:
    """Not a Windows Service (yet) -- a long-running foreground process
    for ST0. Wrapping it as an actual Windows Service is a documented
    follow-up, not required for this issue's acceptance criteria."""

    def __init__(self, config: AgentConfig, provider: ExecutionProvider):
        self._config = config
        self._provider = provider
        self._practice_account: Optional[Account] = None
        self._contract: Optional[Contract] = None
        self.logger = logging.getLogger("trader_agent.service")

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

        self._provider.connect_realtime()
        if self._practice_account is not None:
            self._provider.subscribe_account_updates(self._practice_account.id, self._on_account_update)
        self._provider.subscribe_market_data(self._contract.id, on_quote=self._on_quote, on_trade=self._on_trade)
        audit(self.logger, "agent.started")

    def stop(self) -> None:
        self._provider.disconnect()
        audit(self.logger, "agent.stopped")

    def search_trades(self, account_id: int, start: datetime, end: Optional[datetime] = None) -> list[TradeRecord]:
        """Authenticates only -- no contract resolution, no realtime
        connection -- then pulls read-only execution/fill history for one
        account over [start, end). Backs the `trades` CLI diagnostic
        (issue #80 Step 2's real-account verification spike). Never
        writes anywhere, EdgeLog cloud or otherwise; the account ID is
        redacted before it ever reaches a log line."""
        masked_account = redact_identifier(account_id)
        audit(self.logger, "agent.trade_search.starting", account_id=masked_account)
        self._provider.authenticate()

        start_iso = to_utc_iso(start)
        end_iso = to_utc_iso(end) if end is not None else None
        trades = self._provider.search_trades(account_id, start_iso, end_iso)

        audit(self.logger, "agent.trade_search.completed", account_id=masked_account, record_count=len(trades))
        return trades

    def status(self) -> AgentStatus:
        current_price = self._provider.get_current_price(self._contract.id) if self._contract else None
        return AgentStatus(
            connection_status=self._provider.connection_status,
            is_execution_capable=self._provider.is_execution_capable,
            practice_account=self._practice_account,
            contract=self._contract,
            current_price=current_price,
        )

    def _on_account_update(self, event: dict) -> None:
        audit(self.logger, "agent.account_update", kind=event.get("kind"))

    def _on_quote(self, quote: Quote) -> None:
        audit(self.logger, "agent.quote", contract_id=quote.contract_id, last_price=quote.last_price)

    def _on_trade(self, trade: dict) -> None:
        audit(self.logger, "agent.market_trade")
