from datetime import datetime, timezone

import pytest

from trader_agent.order_manager import OrderManager, OrderRejected
from trader_agent.providers.base import (
    Account,
    CancelOrderResult,
    Contract,
    ExecutionProvider,
    Order,
    OrderSide,
    OrderStatus,
    PlaceOrderResult,
)
from trader_agent.state import ConnectionStatus
from trader_agent.trading_control import TradingControl


class _FakeProvider(ExecutionProvider):
    def __init__(self, execution_capable=True, place_results=None, cancel_result=None, search_result=None):
        self.execution_capable = execution_capable
        self._place_results = list(place_results or [])
        self._cancel_result = cancel_result or CancelOrderResult(success=True, error_code=0, error_message=None)
        self._search_result = search_result if search_result is not None else []
        self.place_calls = []
        self.cancel_calls = []
        self.search_calls = []

    def authenticate(self):
        pass

    def list_accounts(self):
        return []

    def resolve_contract(self, symbol):
        raise NotImplementedError

    def get_current_price(self, contract_id):
        return None

    def connect_realtime(self):
        pass

    def subscribe_account_updates(self, account_id, on_update):
        pass

    def subscribe_market_data(self, contract_id, on_quote=None, on_trade=None):
        pass

    def disconnect(self):
        pass

    def place_limit_order(self, account_id, contract_id, side, size, limit_price, custom_tag):
        self.place_calls.append((account_id, contract_id, side, size, limit_price, custom_tag))
        if self._place_results:
            return self._place_results.pop(0)
        return PlaceOrderResult(success=True, provider_order_id="9056", error_code=0, error_message=None)

    def cancel_order(self, account_id, provider_order_id):
        self.cancel_calls.append((account_id, provider_order_id))
        return self._cancel_result

    def search_orders(self, account_id, start, end=None):
        self.search_calls.append(account_id)
        return self._search_result

    @property
    def connection_status(self):
        return ConnectionStatus.CONNECTED

    @property
    def is_execution_capable(self):
        return self.execution_capable


PRACTICE_ACCOUNT = Account(id=1, name="Practice", is_practice=True)
LIVE_ACCOUNT = Account(id=2, name="Main", is_practice=False)
CONTRACT = Contract(id="CON.F.US.MNQ.Z25", name="MNQZ5", description="", symbol_id="F.US.MNQ", active=True)


def _manager(tmp_path, provider=None, max_quantity=1, control=None):
    provider = provider or _FakeProvider()
    control = control or TradingControl(state_path=tmp_path / "control.json")
    return OrderManager(provider, trading_control=control, store_path=tmp_path / "orders.json", max_quantity=max_quantity), provider, control


def test_submit_limit_order_succeeds_and_records_working_status(tmp_path):
    manager, provider, _ = _manager(tmp_path)

    record = manager.submit_limit_order(PRACTICE_ACCOUNT, CONTRACT, OrderSide.BUY, 1, 21000.0)

    assert record.status == OrderStatus.WORKING.value
    assert record.provider_order_id == "9056"
    assert provider.place_calls[0][:5] == (1, "CON.F.US.MNQ.Z25", OrderSide.BUY, 1, 21000.0)
    assert record.custom_tag.startswith("edgelog-")


def test_submit_limit_order_refuses_a_non_practice_account(tmp_path):
    manager, provider, _ = _manager(tmp_path)

    with pytest.raises(OrderRejected, match="non-Practice"):
        manager.submit_limit_order(LIVE_ACCOUNT, CONTRACT, OrderSide.BUY, 1, 21000.0)
    assert provider.place_calls == []


def test_submit_limit_order_refuses_over_the_configured_max_quantity(tmp_path):
    manager, provider, _ = _manager(tmp_path, max_quantity=1)

    with pytest.raises(OrderRejected, match="exceeds the configured POC maximum"):
        manager.submit_limit_order(PRACTICE_ACCOUNT, CONTRACT, OrderSide.BUY, 2, 21000.0)
    assert provider.place_calls == []


def test_submit_limit_order_refuses_a_non_positive_size(tmp_path):
    manager, provider, _ = _manager(tmp_path)

    with pytest.raises(OrderRejected, match="must be positive"):
        manager.submit_limit_order(PRACTICE_ACCOUNT, CONTRACT, OrderSide.BUY, 0, 21000.0)
    assert provider.place_calls == []


def test_submit_limit_order_refuses_when_not_execution_capable(tmp_path):
    provider = _FakeProvider(execution_capable=False)
    manager, _, _ = _manager(tmp_path, provider=provider)

    with pytest.raises(OrderRejected, match="Not execution-capable"):
        manager.submit_limit_order(PRACTICE_ACCOUNT, CONTRACT, OrderSide.BUY, 1, 21000.0)


def test_submit_limit_order_refuses_when_kill_switch_engaged(tmp_path):
    control = TradingControl(state_path=tmp_path / "control.json")
    control.engage_kill_switch("testing")
    manager, provider, _ = _manager(tmp_path, control=control)

    with pytest.raises(OrderRejected, match="Kill switch engaged"):
        manager.submit_limit_order(PRACTICE_ACCOUNT, CONTRACT, OrderSide.BUY, 1, 21000.0)
    assert provider.place_calls == []


def test_submit_limit_order_records_provider_rejection_without_raising(tmp_path):
    provider = _FakeProvider(
        place_results=[PlaceOrderResult(success=False, provider_order_id=None, error_code=3, error_message="InsufficientFunds")]
    )
    manager, _, _ = _manager(tmp_path, provider=provider)

    record = manager.submit_limit_order(PRACTICE_ACCOUNT, CONTRACT, OrderSide.BUY, 1, 21000.0)

    assert record.status == OrderStatus.REJECTED.value
    assert record.error_message == "InsufficientFunds"


def test_submit_limit_order_still_rejects_locally_even_if_provider_returns_an_order_id_on_failure(tmp_path):
    # Reference doc rule 9: a rejected order can still come back with an
    # orderId -- status must be driven by `success`, never by orderId presence.
    provider = _FakeProvider(
        place_results=[PlaceOrderResult(success=False, provider_order_id="1234", error_code=2, error_message="OrderRejected")]
    )
    manager, _, _ = _manager(tmp_path, provider=provider)

    record = manager.submit_limit_order(PRACTICE_ACCOUNT, CONTRACT, OrderSide.BUY, 1, 21000.0)

    assert record.status == OrderStatus.REJECTED.value
    assert record.provider_order_id == "1234"


def test_duplicate_submission_of_an_identical_open_order_is_refused(tmp_path):
    manager, provider, _ = _manager(tmp_path)
    manager.submit_limit_order(PRACTICE_ACCOUNT, CONTRACT, OrderSide.BUY, 1, 21000.0)

    with pytest.raises(OrderRejected, match="already"):
        manager.submit_limit_order(PRACTICE_ACCOUNT, CONTRACT, OrderSide.BUY, 1, 21000.0)
    assert len(provider.place_calls) == 1


def test_a_different_order_after_the_first_is_canceled_is_not_treated_as_a_duplicate(tmp_path):
    manager, provider, _ = _manager(tmp_path)
    first = manager.submit_limit_order(PRACTICE_ACCOUNT, CONTRACT, OrderSide.BUY, 1, 21000.0)
    manager.cancel(first.custom_tag, PRACTICE_ACCOUNT)

    second = manager.submit_limit_order(PRACTICE_ACCOUNT, CONTRACT, OrderSide.BUY, 1, 21000.0)

    assert second.status == OrderStatus.WORKING.value
    assert len(provider.place_calls) == 2


def test_cancel_marks_the_order_canceled_on_success(tmp_path):
    manager, provider, _ = _manager(tmp_path)
    record = manager.submit_limit_order(PRACTICE_ACCOUNT, CONTRACT, OrderSide.BUY, 1, 21000.0)

    canceled = manager.cancel(record.custom_tag, PRACTICE_ACCOUNT)

    assert canceled.status == OrderStatus.CANCELED.value
    assert provider.cancel_calls == [(1, "9056")]


def test_cancel_is_not_blocked_by_an_engaged_kill_switch(tmp_path):
    control = TradingControl(state_path=tmp_path / "control.json")
    manager, provider, _ = _manager(tmp_path, control=control)
    record = manager.submit_limit_order(PRACTICE_ACCOUNT, CONTRACT, OrderSide.BUY, 1, 21000.0)
    control.engage_kill_switch("stop trading, but let me flatten")

    canceled = manager.cancel(record.custom_tag, PRACTICE_ACCOUNT)

    assert canceled.status == OrderStatus.CANCELED.value


def test_cancel_refuses_an_unknown_tag(tmp_path):
    manager, _, _ = _manager(tmp_path)

    with pytest.raises(OrderRejected, match="No local order record"):
        manager.cancel("edgelog-does-not-exist", PRACTICE_ACCOUNT)


def test_cancel_refuses_an_already_terminal_order(tmp_path):
    manager, _, _ = _manager(tmp_path)
    record = manager.submit_limit_order(PRACTICE_ACCOUNT, CONTRACT, OrderSide.BUY, 1, 21000.0)
    manager.cancel(record.custom_tag, PRACTICE_ACCOUNT)

    with pytest.raises(OrderRejected, match="not cancelable"):
        manager.cancel(record.custom_tag, PRACTICE_ACCOUNT)


def test_orders_survive_reload_from_disk(tmp_path):
    control = TradingControl(state_path=tmp_path / "control.json")
    provider = _FakeProvider()
    store_path = tmp_path / "orders.json"
    manager = OrderManager(provider, trading_control=control, store_path=store_path, max_quantity=1)
    record = manager.submit_limit_order(PRACTICE_ACCOUNT, CONTRACT, OrderSide.BUY, 1, 21000.0)

    reloaded = OrderManager(provider, trading_control=control, store_path=store_path, max_quantity=1)

    assert reloaded.get(record.custom_tag).status == OrderStatus.WORKING.value


def test_reconcile_updates_status_from_provider_fill_information(tmp_path):
    manager, provider, _ = _manager(tmp_path)
    record = manager.submit_limit_order(PRACTICE_ACCOUNT, CONTRACT, OrderSide.BUY, 1, 21000.0)
    provider._search_result = [
        Order(
            provider_order_id="9056",
            account_id=1,
            contract_id="CON.F.US.MNQ.Z25",
            status=OrderStatus.FILLED,
            size=1,
            fill_volume=1,
        )
    ]

    manager.reconcile(PRACTICE_ACCOUNT, since=datetime.now(timezone.utc))

    assert manager.get(record.custom_tag).status == OrderStatus.FILLED.value


def test_reconcile_never_raises_when_the_provider_call_fails(tmp_path):
    class _RaisingProvider(_FakeProvider):
        def search_orders(self, account_id, start, end=None):
            raise RuntimeError("network down")

    manager, _, _ = _manager(tmp_path, provider=_RaisingProvider())

    manager.reconcile(PRACTICE_ACCOUNT, since=datetime.now(timezone.utc))  # must not raise


def test_apply_realtime_update_marks_filled_when_fill_volume_reaches_size(tmp_path):
    manager, _, _ = _manager(tmp_path)
    record = manager.submit_limit_order(PRACTICE_ACCOUNT, CONTRACT, OrderSide.BUY, 1, 21000.0)

    manager.apply_realtime_update({"customTag": record.custom_tag, "size": 1, "fillVolume": 1})

    assert manager.get(record.custom_tag).status == OrderStatus.FILLED.value


def test_apply_realtime_update_marks_partially_filled(tmp_path):
    manager, _, _ = _manager(tmp_path, max_quantity=2)
    record = manager.submit_limit_order(PRACTICE_ACCOUNT, CONTRACT, OrderSide.BUY, 2, 21000.0)

    manager.apply_realtime_update({"customTag": record.custom_tag, "size": 2, "fillVolume": 1})

    assert manager.get(record.custom_tag).status == OrderStatus.PARTIALLY_FILLED.value


def test_apply_realtime_update_ignores_unknown_tags_without_raising(tmp_path):
    manager, _, _ = _manager(tmp_path)

    manager.apply_realtime_update({"customTag": "not-tracked", "size": 1, "fillVolume": 1})  # must not raise


def test_apply_realtime_update_handles_signalr_list_wrapped_payload(tmp_path):
    manager, _, _ = _manager(tmp_path)
    record = manager.submit_limit_order(PRACTICE_ACCOUNT, CONTRACT, OrderSide.BUY, 1, 21000.0)

    manager.apply_realtime_update([{"customTag": record.custom_tag, "size": 1, "fillVolume": 1}])

    assert manager.get(record.custom_tag).status == OrderStatus.FILLED.value


def test_apply_realtime_update_does_not_resurrect_a_canceled_order(tmp_path):
    manager, _, _ = _manager(tmp_path)
    record = manager.submit_limit_order(PRACTICE_ACCOUNT, CONTRACT, OrderSide.BUY, 1, 21000.0)
    manager.cancel(record.custom_tag, PRACTICE_ACCOUNT)

    manager.apply_realtime_update({"customTag": record.custom_tag, "size": 1, "fillVolume": 1})

    assert manager.get(record.custom_tag).status == OrderStatus.CANCELED.value
