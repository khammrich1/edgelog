from dataclasses import dataclass
from typing import Optional

import pytest

import trader_agent.cli as cli
from trader_agent.order_manager import OrderRecord, OrderRejected
from trader_agent.providers.base import Account, Contract, OrderSide
from trader_agent.state import ConnectionStatus


@dataclass
class _Status:
    connection_status: ConnectionStatus
    is_execution_capable: bool
    practice_account: Optional[Account]
    contract: Optional[Contract]
    current_price: object = None
    trading_blocked_reason: Optional[str] = None


class _FakeOrderManager:
    def __init__(self, max_quantity=1, records=None):
        self.max_quantity = max_quantity
        self._records = records or []

    def all_orders(self):
        return self._records


class _FakeService:
    """Stands in for TraderAgentService in CLI tests -- the CLI only ever
    talks to the service's public surface (start/stop/status/place_limit_order/
    cancel_order/order_manager), never the provider directly."""

    def __init__(self, status, order_result=None, order_error=None, cancel_result=None, cancel_error=None, max_quantity=1, records=None):
        self._status = status
        self._order_result = order_result
        self._order_error = order_error
        self._cancel_result = cancel_result
        self._cancel_error = cancel_error
        self.order_manager = _FakeOrderManager(max_quantity=max_quantity, records=records)
        self.started = False
        self.stopped = False
        self.place_calls = []
        self.cancel_calls = []

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def status(self):
        return self._status

    def place_limit_order(self, side, size, limit_price):
        self.place_calls.append((side, size, limit_price))
        if self._order_error:
            raise self._order_error
        return self._order_result

    def cancel_order(self, custom_tag):
        self.cancel_calls.append(custom_tag)
        if self._cancel_error:
            raise self._cancel_error
        return self._cancel_result


ACCOUNT = Account(id=1, name="Practice", is_practice=True)
CONTRACT = Contract(id="CON.F.US.MNQ.Z25", name="MNQZ5", description="", symbol_id="F.US.MNQ", active=True)


def _ready_status(**overrides):
    defaults = dict(
        connection_status=ConnectionStatus.CONNECTED,
        is_execution_capable=True,
        practice_account=ACCOUNT,
        contract=CONTRACT,
        trading_blocked_reason=None,
    )
    defaults.update(overrides)
    return _Status(**defaults)


def _queue_inputs(monkeypatch, *answers):
    queue = iter(answers)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(queue))


def test_cmd_order_submits_after_typed_confirmation(monkeypatch):
    record = OrderRecord(
        custom_tag="edgelog-abc", account_id=1, contract_id="CON.F.US.MNQ.Z25", side="buy", size=1,
        limit_price=21000.0, status="working", provider_order_id="9056",
    )
    service = _FakeService(_ready_status(), order_result=record)
    monkeypatch.setattr(cli.TraderAgentService, "from_local_config", staticmethod(lambda: service))
    _queue_inputs(monkeypatch, "buy", "1", "21000", "CONFIRM")

    rc = cli.cmd_order(None)

    assert rc == 0
    assert service.place_calls == [(OrderSide.BUY, 1, 21000.0)]
    assert service.started and service.stopped


def test_cmd_order_does_not_submit_without_the_exact_confirmation_text(monkeypatch):
    service = _FakeService(_ready_status())
    monkeypatch.setattr(cli.TraderAgentService, "from_local_config", staticmethod(lambda: service))
    _queue_inputs(monkeypatch, "buy", "1", "21000", "yes")

    rc = cli.cmd_order(None)

    assert rc == 0
    assert service.place_calls == []


def test_cmd_order_refuses_when_not_execution_capable(monkeypatch):
    service = _FakeService(_ready_status(is_execution_capable=False, connection_status=ConnectionStatus.STALE))
    monkeypatch.setattr(cli.TraderAgentService, "from_local_config", staticmethod(lambda: service))

    rc = cli.cmd_order(None)

    assert rc == 2
    assert service.place_calls == []
    assert service.stopped


def test_cmd_order_refuses_when_trading_is_blocked(monkeypatch):
    service = _FakeService(_ready_status(trading_blocked_reason="Kill switch engaged: testing"))
    monkeypatch.setattr(cli.TraderAgentService, "from_local_config", staticmethod(lambda: service))

    rc = cli.cmd_order(None)

    assert rc == 2
    assert service.place_calls == []


def test_cmd_order_refuses_without_a_practice_account(monkeypatch):
    service = _FakeService(_ready_status(practice_account=None))
    monkeypatch.setattr(cli.TraderAgentService, "from_local_config", staticmethod(lambda: service))

    rc = cli.cmd_order(None)

    assert rc == 2
    assert service.place_calls == []


def test_cmd_order_surfaces_a_rejected_order_ticket(monkeypatch):
    service = _FakeService(_ready_status(), order_error=OrderRejected("Order size 5 exceeds the configured POC maximum of 1"))
    monkeypatch.setattr(cli.TraderAgentService, "from_local_config", staticmethod(lambda: service))
    _queue_inputs(monkeypatch, "buy", "5", "21000", "CONFIRM")

    rc = cli.cmd_order(None)

    assert rc == 2


def test_cmd_order_reports_a_provider_rejection_with_nonzero_exit(monkeypatch):
    record = OrderRecord(
        custom_tag="edgelog-abc", account_id=1, contract_id="CON.F.US.MNQ.Z25", side="buy", size=1,
        limit_price=21000.0, status="rejected", error_message="InsufficientFunds",
    )
    service = _FakeService(_ready_status(), order_result=record)
    monkeypatch.setattr(cli.TraderAgentService, "from_local_config", staticmethod(lambda: service))
    _queue_inputs(monkeypatch, "buy", "1", "21000", "CONFIRM")

    rc = cli.cmd_order(None)

    assert rc == 1


class _Args:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_cmd_cancel_reports_the_resulting_status(monkeypatch):
    record = OrderRecord(
        custom_tag="edgelog-abc", account_id=1, contract_id="CON.F.US.MNQ.Z25", side="buy", size=1,
        limit_price=21000.0, status="canceled",
    )
    service = _FakeService(_ready_status(), cancel_result=record)
    monkeypatch.setattr(cli.TraderAgentService, "from_local_config", staticmethod(lambda: service))

    rc = cli.cmd_cancel(_Args(custom_tag="edgelog-abc"))

    assert rc == 0
    assert service.cancel_calls == ["edgelog-abc"]


def test_cmd_cancel_surfaces_a_rejection(monkeypatch):
    service = _FakeService(_ready_status(), cancel_error=OrderRejected("No local order record for tag edgelog-abc"))
    monkeypatch.setattr(cli.TraderAgentService, "from_local_config", staticmethod(lambda: service))

    rc = cli.cmd_cancel(_Args(custom_tag="edgelog-abc"))

    assert rc == 2


def test_cmd_orders_lists_local_records(monkeypatch, capsys):
    record = OrderRecord(
        custom_tag="edgelog-abc", account_id=1, contract_id="CON.F.US.MNQ.Z25", side="buy", size=1,
        limit_price=21000.0, status="working", provider_order_id="9056",
    )
    service = _FakeService(_ready_status(), records=[record])
    monkeypatch.setattr(cli.TraderAgentService, "from_local_config", staticmethod(lambda: service))

    rc = cli.cmd_orders(None)

    assert rc == 0
    assert "edgelog-abc" in capsys.readouterr().out


def test_cmd_kill_engages_and_persists(monkeypatch, tmp_path):
    from trader_agent.trading_control import TradingControl

    path = tmp_path / "control.json"
    monkeypatch.setattr(cli, "TradingControl", lambda: TradingControl(state_path=path))

    rc = cli.cmd_kill(_Args(clear=False, reason="unit test"))

    assert rc == 0
    assert TradingControl(state_path=path).kill_switch_engaged is True


def test_cmd_kill_clear(monkeypatch, tmp_path):
    from trader_agent.trading_control import TradingControl

    path = tmp_path / "control.json"
    monkeypatch.setattr(cli, "TradingControl", lambda: TradingControl(state_path=path))
    TradingControl(state_path=path).engage_kill_switch("prior")

    rc = cli.cmd_kill(_Args(clear=True, reason=None))

    assert rc == 0
    assert TradingControl(state_path=path).kill_switch_engaged is False
