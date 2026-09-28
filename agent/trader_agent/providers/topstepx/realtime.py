"""Real-time SignalR connectivity for TopstepX/ProjectX.

Design note: the actual wire protocol (SignalR) is handled by the
`signalrcore` third-party library, which this agent was built without
live network access to verify against its own documentation in detail.
Rather than risk silently-wrong assumptions about that library's exact
API surface throughout this file, all of the logic that actually matters
for ST0's acceptance criteria -- subscribing without duplicates,
resubscribing after a reconnect, and updating connection/staleness state
-- lives in `RealtimeHub` below, written against the small `Transport`
protocol and fully unit-testable with a fake transport. `SignalRTransport`
is the thin, mostly-untestable adapter to the real library; keep it
minimal and verify it against a real connection on Windows before relying
on it (see agent/README.md).

Hub URLs, subscribe method names (SubscribeAccounts/SubscribeOrders/
SubscribePositions/SubscribeTrades on the user hub, SubscribeContractQuotes/
SubscribeContractTrades on the market hub), the GatewayUserAccount/
GatewayUserOrder/GatewayUserPosition/GatewayUserTrade and GatewayQuote/
GatewayTrade event names, and the access_token-in-query-string connection
pattern are all taken from public documentation/third-party references
for the ProjectX Gateway API, cross-referenced across independent
sources. Confirm against gateway.docs.projectx.com if TopstepX changes
these.
"""
from __future__ import annotations

import logging
from typing import Callable, Protocol

from trader_agent.state import ConnectionStatus, HealthTracker

logger = logging.getLogger("trader_agent.realtime")

USER_HUB_PATH = "/hubs/user"
MARKET_HUB_PATH = "/hubs/market"


class Transport(Protocol):
    """Whatever's underneath a hub connection. SignalRTransport is the
    real implementation; tests use a fake that implements the same shape."""

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def send(self, method: str, args: list) -> None: ...

    def on(self, event: str, handler: Callable) -> None: ...

    def on_open(self, handler: Callable[[], None]) -> None: ...

    def on_close(self, handler: Callable[[], None]) -> None: ...

    def on_error(self, handler: Callable[[object], None]) -> None: ...


class SignalRTransport:
    """Real transport, built on signalrcore. Not exercised by the unit
    test suite -- verify this against a live connection on Windows."""

    def __init__(self, url: str, token: str):
        from signalrcore.hub_connection_builder import HubConnectionBuilder

        self._connection = (
            HubConnectionBuilder()
            .with_url(f"{url}?access_token={token}", options={"skip_negotiation": True})
            .with_automatic_reconnect(
                {"type": "raw", "keep_alive_interval": 10, "reconnect_interval": 5, "max_attempts": 10}
            )
            .build()
        )

    def start(self) -> None:
        self._connection.start()

    def stop(self) -> None:
        self._connection.stop()

    def send(self, method: str, args: list) -> None:
        self._connection.send(method, args)

    def on(self, event: str, handler: Callable) -> None:
        self._connection.on(event, handler)

    def on_open(self, handler: Callable[[], None]) -> None:
        self._connection.on_open(handler)

    def on_close(self, handler: Callable[[], None]) -> None:
        self._connection.on_close(handler)

    def on_error(self, handler: Callable[[object], None]) -> None:
        self._connection.on_error(handler)


TransportFactory = Callable[[str, str], Transport]


class RealtimeHub:
    """One hub connection (user or market) plus the subscribe-on-connect
    bookkeeping that keeps a reconnect from either losing subscriptions or
    sending duplicates.

    Subscriptions are stored as a dict keyed by (method, args-tuple), so
    asking to subscribe to the same thing twice is a no-op, and every
    entry is (re-)sent exactly once each time the transport reports
    on_open -- including the very first connect and every reconnect after
    that. This is what satisfies "Disconnect/reconnect is handled without
    duplicate subscriptions": the *registry* never grows a duplicate, even
    though a genuine reconnect correctly re-issues every real Subscribe*
    call (the server has no memory of a dropped connection's subscriptions).
    """

    def __init__(self, name: str, transport_factory: TransportFactory, url: str, health: HealthTracker):
        self._name = name
        self._transport_factory = transport_factory
        self._url = url
        self._health = health
        self._transport: Transport | None = None
        self._pending_subscriptions: dict[tuple[str, tuple], None] = {}
        self._event_handlers: dict[str, Callable] = {}

    def on(self, event: str, handler: Callable) -> None:
        """Registers an event handler. Safe to call before connect(); it
        is attached to the transport as soon as one exists."""
        self._event_handlers[event] = handler
        if self._transport is not None:
            self._transport.on(event, handler)

    def subscribe(self, method: str, *args) -> None:
        key = (method, args)
        already_pending = key in self._pending_subscriptions
        self._pending_subscriptions[key] = None
        if already_pending:
            # Already subscribed (or will be, on the next open) -- a repeat
            # call must never put a second identical Subscribe* RPC on the
            # wire for an already-live subscription.
            return
        if self._transport is not None and self._health.status in (ConnectionStatus.CONNECTED, ConnectionStatus.STALE):
            self._send(method, list(args))

    def connect(self, token: str) -> None:
        self._health.mark_connecting()
        self._transport = self._transport_factory(self._url, token)
        for event, handler in self._event_handlers.items():
            self._transport.on(event, handler)
        self._transport.on_open(self._on_open)
        self._transport.on_close(self._on_close)
        self._transport.on_error(self._on_error)
        self._transport.start()

    def disconnect(self) -> None:
        if self._transport is not None:
            self._transport.stop()
        self._health.mark_disconnected()

    def note_market_data_received(self) -> None:
        self._health.mark_market_data_received()

    def _on_open(self) -> None:
        self._health.mark_connected()
        logger.info("trader_agent.realtime.hub_connected", extra={"hub": self._name})
        for method, args in list(self._pending_subscriptions.keys()):
            self._send(method, list(args))

    def _on_close(self) -> None:
        self._health.mark_disconnected()
        logger.warning("trader_agent.realtime.hub_disconnected", extra={"hub": self._name})

    def _on_error(self, error: object) -> None:
        logger.error("trader_agent.realtime.hub_error", extra={"hub": self._name, "error": str(error)})

    def _send(self, method: str, args: list) -> None:
        assert self._transport is not None
        self._transport.send(method, args)
