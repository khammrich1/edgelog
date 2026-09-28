"""Local, restart-safe trading-safety controls: the kill switch and the
AUTO TRADING flag.

Both exist so every order-placing path -- ST1's manual flow today, ST3's
automated flow later -- checks the same source of truth before ever
touching the network, rather than each inventing its own notion of "is it
safe to trade right now." See
docs/integrations/projectx/PROJECTX_API_REFERENCE.md section 10:

- Rule 12: AUTO TRADING defaults OFF after restart, strategy-version
  change, credential change, or unresolved reconciliation fault. ST1 has
  no automated execution path, so nothing in this codebase can currently
  set this True -- it's built now so ST3's risk engine has one settled
  flag to read rather than inventing its own later.
- The kill switch is EdgeLog's own addition, not something ProjectX
  documents: a local, network-independent emergency stop. It can be
  engaged without any connection to TopstepX (it's a plain local file),
  which matters -- a kill switch that itself depends on network access to
  engage is not a real kill switch.

Cancelling an existing order is never blocked by the kill switch (see
order_manager.py) -- only *new* order submission is. A kill switch should
make it easier, never harder, to reduce risk that's already on.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from trader_agent.logging_setup import audit

AGENT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_STATE_PATH = AGENT_DIR / ".state" / "trading_control.json"

_KNOWN_FIELDS = {"kill_switch_engaged", "kill_switch_reason", "kill_switch_engaged_at", "auto_trading_enabled"}


@dataclass
class TradingControlState:
    kill_switch_engaged: bool = False
    kill_switch_reason: Optional[str] = None
    kill_switch_engaged_at: Optional[str] = None
    auto_trading_enabled: bool = False


class TradingControl:
    def __init__(self, state_path: Optional[Path] = None):
        self._path = state_path or DEFAULT_STATE_PATH
        self._logger = logging.getLogger("trader_agent.trading_control")
        self._state = self._load()

    def _load(self) -> TradingControlState:
        state = TradingControlState()
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text())
                state = TradingControlState(**{k: v for k, v in data.items() if k in _KNOWN_FIELDS})
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                audit(
                    self._logger,
                    "trading_control.state_file_unreadable",
                    level=logging.WARNING,
                    path=str(self._path),
                    error=str(exc),
                )
                state = TradingControlState()

        # Rule 12: AUTO TRADING always starts OFF on load, regardless of
        # what was persisted -- a restart must never silently resume
        # automated trading.
        if state.auto_trading_enabled:
            audit(self._logger, "trading_control.auto_trading_forced_off_on_load", level=logging.WARNING)
        state.auto_trading_enabled = False
        self._save(state)
        return state

    def _save(self, state: Optional[TradingControlState] = None) -> None:
        state = state or self._state
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(asdict(state), indent=2))

    @property
    def kill_switch_engaged(self) -> bool:
        return self._state.kill_switch_engaged

    @property
    def auto_trading_enabled(self) -> bool:
        return self._state.auto_trading_enabled

    def engage_kill_switch(self, reason: str) -> None:
        self._state.kill_switch_engaged = True
        self._state.kill_switch_reason = reason
        self._state.kill_switch_engaged_at = datetime.now(timezone.utc).isoformat()
        self._save()
        audit(self._logger, "trading_control.kill_switch_engaged", level=logging.WARNING, reason=reason)

    def clear_kill_switch(self) -> None:
        self._state.kill_switch_engaged = False
        self._state.kill_switch_reason = None
        self._state.kill_switch_engaged_at = None
        self._save()
        audit(self._logger, "trading_control.kill_switch_cleared")

    def block_reason(self) -> Optional[str]:
        """None if new order submission may proceed as far as trading
        control is concerned; otherwise a human-readable reason it may
        not. Does not gate cancellation -- see order_manager.py."""
        if self._state.kill_switch_engaged:
            return f"Kill switch engaged: {self._state.kill_switch_reason or 'no reason given'}"
        return None
