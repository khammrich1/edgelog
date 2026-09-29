"""TopstepXProvider: the ExecutionProvider implementation for TopstepX,
wiring the REST client and the two real-time hubs together behind the
provider-agnostic interface in providers/base.py."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from trader_agent.providers.base import (
    Account,
    AccountUpdateHandler,
    CancelOrderResult,
    Contract,
    ExecutionProvider,
    Order,
    OrderSide,
    OrderStatus,
    PlaceOrderResult,
    Quote,
    QuoteHandler,
    TradeHandler,
)
from trader_agent.providers.topstepx.client import TopstepXRestClient
from trader_agent.providers.topstepx.errors import TopstepXError
from trader_agent.providers.topstepx.realtime import (
    MARKET_HUB_PATH,
    USER_HUB_PATH,
    RealtimeHub,
    SignalRTransport,
    Transport,
    TransportFactory,
)
from trader_agent.state import ConnectionStatus, HealthTracker

logger = logging.getLogger("trader_agent.provider.topstepx")


class NoActiveContractError(TopstepXError):
    """Raised when a symbol search returns no contract flagged active."""


# Per the reference doc's Order type/side enums (section 6). ST1 only ever
# sends type 1 (Limit) -- place_limit_order() doesn't expose a type
# parameter at all, so nothing else is reachable from this provider.
_ORDER_TYPE_LIMIT = 1
_SIDE_TO_PROVIDER = {OrderSide.BUY: 0, OrderSide.SELL: 1}
_PROVIDER_SIDE_TO_ORDER_SIDE = {0: OrderSide.BUY, 1: OrderSide.SELL}


def _default_transport_factory(url: str, token: str) -> Transport:
    return SignalRTransport(url, token)


class TopstepXProvider(ExecutionProvider):
    def __init__(
        self,
        rest_client: TopstepXRestClient,
        rtc_base_url: str,
        stale_after_seconds: float,
        transport_factory: TransportFactory = _default_transport_factory,
        practice_account_id: Optional[int] = None,
    ):
        self._rest = rest_client
        self._practice_account_id = practice_account_id

        self._user_health = HealthTracker(stale_after_seconds=stale_after_seconds)
        self._market_health = HealthTracker(stale_after_seconds=stale_after_seconds)

        self._user_hub = RealtimeHub("user", transport_factory, f"{rtc_base_url}{USER_HUB_PATH}", self._user_health)
        self._market_hub = RealtimeHub(
            "market", transport_factory, f"{rtc_base_url}{MARKET_HUB_PATH}", self._market_health
        )

        self._latest_quotes: dict[str, Quote] = {}
        # The reference doc's documented quote fields (symbol, symbolName,
        # lastPrice, bestBid, bestAsk, ...) don't include contractId --
        # unlike an order/position update, a quote payload apparently
        # doesn't self-identify which contract it's for by ID. ST0 only
        # ever subscribes to one contract at a time, so quotes are
        # attributed to whichever contract_id was last subscribed rather
        # than parsed out of the payload. Revisit if a future issue needs
        # multiple simultaneous contract subscriptions.
        self._market_contract_id: Optional[str] = None
        self._user_hub.on("GatewayUserAccount", self._make_forwarder("account"))
        self._user_hub.on("GatewayUserOrder", self._make_forwarder("order"))
        self._user_hub.on("GatewayUserPosition", self._make_forwarder("position"))
        self._user_hub.on("GatewayUserTrade", self._make_forwarder("trade"))
        self._market_hub.on("GatewayQuote", self._on_gateway_quote)
        self._market_hub.on("GatewayTrade", self._on_gateway_trade)

        self._account_update_handlers: list[AccountUpdateHandler] = []
        self._quote_handlers: list[QuoteHandler] = []
        self._trade_handlers: list[TradeHandler] = []

    # -- ExecutionProvider --

    def authenticate(self) -> None:
        self._rest.authenticate()
        self._user_health.mark_authenticated()
        self._market_health.mark_authenticated()
        logger.info("trader_agent.provider.authenticated")

    def list_accounts(self) -> list[Account]:
        accounts = self._rest.search_accounts()
        if self._practice_account_id is not None:
            accounts = [
                a if a.id != self._practice_account_id else Account(a.id, a.name, True, a.balance, a.raw)
                for a in accounts
            ]
        return accounts

    def get_practice_account(self) -> Optional[Account]:
        """Convenience for the common case: the account the agent should
        treat as Practice. Prefers the pinned TOPSTEPX_PRACTICE_ACCOUNT_ID
        override over the name/flag heuristic in client.py."""
        accounts = self.list_accounts()
        if self._practice_account_id is not None:
            return next((a for a in accounts if a.id == self._practice_account_id), None)
        return next((a for a in accounts if a.is_practice), None)

    def resolve_contract(self, symbol: str) -> Contract:
        """Lists every available contract and filters client-side for the
        requested root symbol's active month. Uses /api/Contract/available
        rather than /api/Contract/search -- the latter's request schema
        isn't documented in the API reference (flagged as a gap), while
        /available's full request/response shape is confirmed."""
        contracts = self._rest.list_available_contracts(live=False)
        symbol_upper = symbol.upper()
        matching = [
            c
            for c in contracts
            if symbol_upper in (c.symbol_id or "").upper() or symbol_upper in (c.name or "").upper()
        ]
        active = [c for c in matching if c.active]
        if not active:
            raise NoActiveContractError(f"No active contract found for symbol '{symbol}'")
        if len(active) > 1:
            logger.warning(
                "trader_agent.provider.multiple_active_contracts",
                extra={"symbol": symbol, "count": len(active)},
            )
        return active[0]

    def get_current_price(self, contract_id: str) -> Optional[Quote]:
        return self._latest_quotes.get(contract_id)

    def connect_realtime(self) -> None:
        token = self._rest.token
        if not token:
            raise TopstepXError("Cannot connect realtime before authenticate() succeeds")
        self._user_hub.connect(token)
        self._market_hub.connect(token)

    def subscribe_account_updates(self, account_id: int, on_update: AccountUpdateHandler) -> None:
        self._account_update_handlers.append(on_update)
        self._user_hub.subscribe("SubscribeAccounts", account_id)
        self._user_hub.subscribe("SubscribeOrders", account_id)
        self._user_hub.subscribe("SubscribePositions", account_id)
        self._user_hub.subscribe("SubscribeTrades", account_id)

    def subscribe_market_data(
        self,
        contract_id: str,
        on_quote: Optional[QuoteHandler] = None,
        on_trade: Optional[TradeHandler] = None,
    ) -> None:
        if on_quote is not None:
            self._quote_handlers.append(on_quote)
        if on_trade is not None:
            self._trade_handlers.append(on_trade)
        self._market_contract_id = contract_id
        self._market_hub.subscribe("SubscribeContractQuotes", contract_id)
        self._market_hub.subscribe("SubscribeContractTrades", contract_id)

    def disconnect(self) -> None:
        self._user_hub.disconnect()
        self._market_hub.disconnect()

    def place_limit_order(
        self,
        account_id: int,
        contract_id: str,
        side: OrderSide,
        size: int,
        limit_price: float,
        custom_tag: str,
    ) -> PlaceOrderResult:
        body = self._rest.place_order(
            account_id=account_id,
            contract_id=contract_id,
            order_type=_ORDER_TYPE_LIMIT,
            side=_SIDE_TO_PROVIDER[side],
            size=size,
            limit_price=limit_price,
            custom_tag=custom_tag,
        )
        order_id = body.get("orderId")
        return PlaceOrderResult(
            success=bool(body.get("success")),
            provider_order_id=str(order_id) if order_id is not None else None,
            error_code=body.get("errorCode"),
            error_message=body.get("errorMessage"),
            raw=body,
        )

    def cancel_order(self, account_id: int, provider_order_id: str) -> CancelOrderResult:
        body = self._rest.cancel_order(account_id=account_id, order_id=int(provider_order_id))
        return CancelOrderResult(
            success=bool(body.get("success")),
            error_code=body.get("errorCode"),
            error_message=body.get("errorMessage"),
            raw=body,
        )

    def search_orders(self, account_id: int, start: datetime, end: Optional[datetime] = None) -> list[Order]:
        raw_orders = self._rest.search_orders(
            account_id, start.isoformat(), end.isoformat() if end is not None else None
        )
        return [self._parse_order(account_id, item) for item in raw_orders]

    @staticmethod
    def _parse_order(account_id: int, item: dict) -> Order:
        order_id = item.get("id")
        size = item.get("size") or 0
        fill_volume = item.get("fillVolume") or 0
        return Order(
            provider_order_id=str(order_id) if order_id is not None else "",
            account_id=account_id,
            contract_id=item.get("contractId") or "",
            status=TopstepXProvider._derive_order_status(size, fill_volume),
            side=_PROVIDER_SIDE_TO_ORDER_SIDE.get(item.get("side")),
            size=size,
            limit_price=item.get("limitPrice"),
            fill_volume=fill_volume,
            filled_price=item.get("filledPrice"),
            custom_tag=item.get("customTag"),
            raw=item,
        )

    @staticmethod
    def _derive_order_status(size: int, fill_volume: int) -> OrderStatus:
        # The provider's own numeric order-status enum isn't fully
        # documented (see the reference doc's "Gaps / do not guess"
        # section) -- reconciliation derives status from fillVolume vs.
        # size instead of trusting an unverified status code. This can
        # only ever report WORKING/PARTIALLY_FILLED/FILLED; CANCELED and
        # REJECTED are set locally by OrderManager from EdgeLog's own
        # place/cancel responses, never inferred from a search result.
        if fill_volume <= 0:
            return OrderStatus.WORKING
        if fill_volume >= size:
            return OrderStatus.FILLED
        return OrderStatus.PARTIALLY_FILLED

    @property
    def connection_status(self) -> ConnectionStatus:
        statuses = {self._user_health.status, self._market_health.status}
        for status in (
            ConnectionStatus.STALE,
            ConnectionStatus.RECONNECTING,
            ConnectionStatus.CONNECTING,
            ConnectionStatus.DISCONNECTED,
        ):
            if status in statuses:
                return status
        return ConnectionStatus.CONNECTED

    @property
    def is_execution_capable(self) -> bool:
        return self._user_health.is_execution_capable and self._market_health.is_execution_capable

    # -- internal event wiring --

    def _make_forwarder(self, kind: str):
        def _forward(payload: object) -> None:
            for handler in self._account_update_handlers:
                handler({"kind": kind, "payload": payload})

        return _forward

    def _on_gateway_quote(self, payload: object) -> None:
        self._market_hub.note_market_data_received()
        quote = self._parse_quote(payload, self._market_contract_id)
        if quote is not None:
            self._latest_quotes[quote.contract_id] = quote
            for handler in self._quote_handlers:
                handler(quote)

    def _on_gateway_trade(self, payload: object) -> None:
        self._market_hub.note_market_data_received()
        for handler in self._trade_handlers:
            handler(payload if isinstance(payload, dict) else {"raw": payload})

    @staticmethod
    def _parse_quote(payload: object, contract_id: Optional[str]) -> Optional[Quote]:
        # SignalR client libraries typically deliver hub arguments as a
        # list; ProjectX's own payload is the first (and only) element.
        item = payload[0] if isinstance(payload, list) and payload else payload
        if not isinstance(item, dict) or contract_id is None:
            return None
        return Quote(
            contract_id=contract_id,
            last_price=item.get("lastPrice"),
            bid=item.get("bestBid"),
            ask=item.get("bestAsk"),
            raw=item,
        )
