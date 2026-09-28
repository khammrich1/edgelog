from trader_agent.config import AgentConfig
from trader_agent.order_manager import OrderManager
from trader_agent.providers.base import (
    Account,
    CancelOrderResult,
    Contract,
    ExecutionProvider,
    OrderSide,
    PlaceOrderResult,
    Quote,
)
from trader_agent.service import TraderAgentService
from trader_agent.state import ConnectionStatus
from trader_agent.trading_control import TradingControl


class _FakeProvider(ExecutionProvider):
    def __init__(
        self,
        accounts=None,
        contract=None,
        quote=None,
        raise_on_resolve_contract=False,
        place_order_result=None,
        cancel_order_result=None,
        search_orders_result=None,
    ):
        self.calls = []
        self._accounts = accounts or []
        self._contract = contract
        self._quote = quote
        self._raise_on_resolve_contract = raise_on_resolve_contract
        self._connected = False
        self._authenticated = False
        self._place_order_result = place_order_result or PlaceOrderResult(
            success=True, provider_order_id="9056", error_code=0, error_message=None
        )
        self._cancel_order_result = cancel_order_result or CancelOrderResult(
            success=True, error_code=0, error_message=None
        )
        self._search_orders_result = search_orders_result or []

    def authenticate(self):
        self.calls.append("authenticate")
        self._authenticated = True

    def list_accounts(self):
        self.calls.append("list_accounts")
        return self._accounts

    def get_practice_account(self):
        self.calls.append("get_practice_account")
        return next((a for a in self._accounts if a.is_practice), None)

    def resolve_contract(self, symbol):
        self.calls.append(("resolve_contract", symbol))
        if self._raise_on_resolve_contract:
            raise RuntimeError("no active contract")
        return self._contract

    def get_current_price(self, contract_id):
        self.calls.append(("get_current_price", contract_id))
        return self._quote

    def connect_realtime(self):
        self.calls.append("connect_realtime")
        self._connected = True

    def subscribe_account_updates(self, account_id, on_update):
        self.calls.append(("subscribe_account_updates", account_id))

    def subscribe_market_data(self, contract_id, on_quote=None, on_trade=None):
        self.calls.append(("subscribe_market_data", contract_id))

    def disconnect(self):
        self.calls.append("disconnect")
        self._connected = False

    def place_limit_order(self, account_id, contract_id, side, size, limit_price, custom_tag):
        self.calls.append(("place_limit_order", account_id, contract_id, side, size, limit_price, custom_tag))
        return self._place_order_result

    def cancel_order(self, account_id, provider_order_id):
        self.calls.append(("cancel_order", account_id, provider_order_id))
        return self._cancel_order_result

    def search_orders(self, account_id, start, end=None):
        self.calls.append(("search_orders", account_id))
        return self._search_orders_result

    @property
    def connection_status(self):
        return ConnectionStatus.CONNECTED if self._connected else ConnectionStatus.DISCONNECTED

    @property
    def is_execution_capable(self):
        return self._authenticated and self._connected


def _config(max_order_quantity=1):
    return AgentConfig(
        username="trader1",
        api_key="secret",
        symbol="MNQ",
        api_base_url="https://api.topstepx.com",
        rtc_base_url="https://rtc.topstepx.com",
        stale_after_seconds=10.0,
        max_order_quantity=max_order_quantity,
    )


def _service(tmp_path, provider, config=None, max_order_quantity=1):
    """Every test gets its own tmp_path-backed trading control/order store
    -- the real default paths under agent/.state/ are for actual local
    runs, not for tests to share/pollute."""
    control = TradingControl(state_path=tmp_path / "trading_control.json")
    order_manager = OrderManager(
        provider, trading_control=control, store_path=tmp_path / "orders.json", max_quantity=max_order_quantity
    )
    return TraderAgentService(config or _config(max_order_quantity), provider, trading_control=control, order_manager=order_manager)


def test_start_authenticates_resolves_contract_and_connects_realtime_in_order(tmp_path):
    account = Account(id=1, name="Practice", is_practice=True)
    contract = Contract(id="CON.F.US.MNQ.Z25", name="MNQZ5", description="", symbol_id="F.US.MNQ", active=True)
    provider = _FakeProvider(accounts=[account], contract=contract)
    service = _service(tmp_path, provider)

    service.start()

    assert provider.calls[:5] == [
        "authenticate",
        "get_practice_account",
        ("resolve_contract", "MNQ"),
        ("search_orders", 1),
        "connect_realtime",
    ]
    assert ("subscribe_account_updates", 1) in provider.calls
    assert ("subscribe_market_data", "CON.F.US.MNQ.Z25") in provider.calls


def test_start_without_a_practice_account_still_resolves_contract_and_subscribes_market_data(tmp_path):
    contract = Contract(id="CON.F.US.MNQ.Z25", name="MNQZ5", description="", symbol_id="F.US.MNQ", active=True)
    provider = _FakeProvider(accounts=[], contract=contract)
    service = _service(tmp_path, provider)

    service.start()

    assert ("subscribe_market_data", "CON.F.US.MNQ.Z25") in provider.calls
    assert not any(call[0] == "subscribe_account_updates" for call in provider.calls if isinstance(call, tuple))
    # No practice account resolved -- reconciliation has nothing to reconcile against.
    assert not any(call[0] == "search_orders" for call in provider.calls if isinstance(call, tuple))


def test_status_reports_account_contract_and_current_price(tmp_path):
    account = Account(id=1, name="Practice", is_practice=True)
    contract = Contract(id="CON.F.US.MNQ.Z25", name="MNQZ5", description="", symbol_id="F.US.MNQ", active=True)
    quote = Quote(contract_id="CON.F.US.MNQ.Z25", last_price=21005.5)
    provider = _FakeProvider(accounts=[account], contract=contract, quote=quote)
    service = _service(tmp_path, provider)
    service.start()

    status = service.status()

    assert status.practice_account.id == 1
    assert status.contract.id == "CON.F.US.MNQ.Z25"
    assert status.current_price.last_price == 21005.5
    assert status.connection_status == ConnectionStatus.CONNECTED
    assert status.is_execution_capable is True
    assert status.trading_blocked_reason is None


def test_status_reports_kill_switch_block_reason(tmp_path):
    account = Account(id=1, name="Practice", is_practice=True)
    contract = Contract(id="CON.F.US.MNQ.Z25", name="MNQZ5", description="", symbol_id="F.US.MNQ", active=True)
    provider = _FakeProvider(accounts=[account], contract=contract)
    service = _service(tmp_path, provider)
    service.start()

    service.trading_control.engage_kill_switch("testing")

    assert service.status().trading_blocked_reason == "Kill switch engaged: testing"


def test_stop_disconnects_the_provider(tmp_path):
    contract = Contract(id="CON.F.US.MNQ.Z25", name="MNQZ5", description="", symbol_id="F.US.MNQ", active=True)
    provider = _FakeProvider(accounts=[], contract=contract)
    service = _service(tmp_path, provider)
    service.start()

    service.stop()

    assert provider.calls[-1] == "disconnect"
    assert service.status().connection_status == ConnectionStatus.DISCONNECTED


def test_place_limit_order_delegates_to_order_manager_against_the_resolved_account_and_contract(tmp_path):
    account = Account(id=1, name="Practice", is_practice=True)
    contract = Contract(id="CON.F.US.MNQ.Z25", name="MNQZ5", description="", symbol_id="F.US.MNQ", active=True)
    provider = _FakeProvider(accounts=[account], contract=contract)
    service = _service(tmp_path, provider)
    service.start()

    record = service.place_limit_order(OrderSide.BUY, 1, 21000.0)

    assert record.status == "working"
    assert record.provider_order_id == "9056"
    assert any(call[0] == "place_limit_order" and call[1] == 1 and call[2] == "CON.F.US.MNQ.Z25" for call in provider.calls)


def test_cancel_order_delegates_to_order_manager(tmp_path):
    account = Account(id=1, name="Practice", is_practice=True)
    contract = Contract(id="CON.F.US.MNQ.Z25", name="MNQZ5", description="", symbol_id="F.US.MNQ", active=True)
    provider = _FakeProvider(accounts=[account], contract=contract)
    service = _service(tmp_path, provider)
    service.start()
    record = service.place_limit_order(OrderSide.BUY, 1, 21000.0)

    canceled = service.cancel_order(record.custom_tag)

    assert canceled.status == "canceled"
    assert ("cancel_order", 1, "9056") in provider.calls
