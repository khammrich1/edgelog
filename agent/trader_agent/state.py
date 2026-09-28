"""Connection/data-health state machine, shared by every provider.

ST0 never places an order, but the acceptance criteria explicitly require
that stale market data "prevents execution-capable state" -- so this
tracks the concept now, ready for ST1 to gate order placement on it,
rather than being invented later as an afterthought.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


class ConnectionStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    STALE = "stale"


Clock = Callable[[], float]


@dataclass
class HealthTracker:
    """Tracks connection status plus market-data freshness for one
    provider connection. `clock` defaults to time.monotonic but is
    injectable so tests never depend on real wall-clock timing."""

    stale_after_seconds: float
    clock: Clock = field(default=None)  # type: ignore[assignment]
    _status: ConnectionStatus = field(default=ConnectionStatus.DISCONNECTED, init=False)
    _last_market_data_at: Optional[float] = field(default=None, init=False)
    _authenticated: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if self.clock is None:
            import time

            self.clock = time.monotonic

    @property
    def status(self) -> ConnectionStatus:
        if self._status == ConnectionStatus.CONNECTED and self._is_market_data_stale():
            return ConnectionStatus.STALE
        return self._status

    def mark_connecting(self) -> None:
        self._status = ConnectionStatus.CONNECTING

    def mark_connected(self) -> None:
        self._status = ConnectionStatus.CONNECTED
        # A fresh connection has no data yet; treat "just connected" as not
        # stale until the first market data tick actually fails to arrive.
        self._last_market_data_at = self.clock()

    def mark_authenticated(self) -> None:
        self._authenticated = True

    def mark_disconnected(self) -> None:
        was_connected = self._status in (ConnectionStatus.CONNECTED, ConnectionStatus.STALE)
        self._status = ConnectionStatus.RECONNECTING if was_connected else ConnectionStatus.DISCONNECTED
        self._authenticated = False

    def mark_market_data_received(self) -> None:
        self._last_market_data_at = self.clock()

    def _is_market_data_stale(self) -> bool:
        if self._last_market_data_at is None:
            return False
        return (self.clock() - self._last_market_data_at) > self.stale_after_seconds

    @property
    def is_execution_capable(self) -> bool:
        """True only when authenticated, connected, and market data is
        fresh. ST0 never acts on this (no order placement exists yet), but
        ST1's risk/order gating should read this rather than re-deriving
        its own notion of "healthy"."""
        return self._authenticated and self.status == ConnectionStatus.CONNECTED
