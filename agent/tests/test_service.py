from trader_agent.config import AgentConfig
from trader_agent.providers.base import Account, Contract, ExecutionProvider, Quote
from trader_agent.service import TraderAgentService
from trader_agent.state import ConnectionStatus


class _FakeProvider(ExecutionProvider):
    def __init__(self, accounts=None, contract=None, quote=None, raise_on_resolve_contract=False):
        self.calls = []
        self._accounts = accounts or []
        self._contract = contract
        self._quote = quote
        self._raise_on_resolve_contract = raise_on_resolve_contract
        self._connected = False
        self._authenticated = False

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

    @property
    def connection_status(self):
        return ConnectionStatus.CONNECTED if self._connected else ConnectionStatus.DISCONNECTED

    @property
    def is_execution_capable(self):
        return self._authenticated and self._connected


def _config():
    return AgentConfig(
        username="trader1",
        api_key="secret",
        symbol="MNQ",
        api_base_url="https://api.topstepx.com",
        rtc_base_url="https://rtc.topstepx.com",
        stale_after_seconds=10.0,
    )


def test_start_authenticates_resolves_contract_and_connects_realtime_in_order():
    account = Account(id=1, name="Practice", is_practice=True)
    contract = Contract(id="CON.F.US.MNQ.Z25", name="MNQZ5", description="", symbol_id="F.US.MNQ", active=True)
    provider = _FakeProvider(accounts=[account], contract=contract)
    service = TraderAgentService(_config(), provider)

    service.start()

    assert provider.calls[:4] == [
        "authenticate",
        "get_practice_account",
        ("resolve_contract", "MNQ"),
        "connect_realtime",
    ]
    assert ("subscribe_account_updates", 1) in provider.calls
    assert ("subscribe_market_data", "CON.F.US.MNQ.Z25") in provider.calls


def test_start_without_a_practice_account_still_resolves_contract_and_subscribes_market_data():
    contract = Contract(id="CON.F.US.MNQ.Z25", name="MNQZ5", description="", symbol_id="F.US.MNQ", active=True)
    provider = _FakeProvider(accounts=[], contract=contract)
    service = TraderAgentService(_config(), provider)

    service.start()

    assert ("subscribe_market_data", "CON.F.US.MNQ.Z25") in provider.calls
    assert not any(call[0] == "subscribe_account_updates" for call in provider.calls if isinstance(call, tuple))


def test_status_reports_account_contract_and_current_price():
    account = Account(id=1, name="Practice", is_practice=True)
    contract = Contract(id="CON.F.US.MNQ.Z25", name="MNQZ5", description="", symbol_id="F.US.MNQ", active=True)
    quote = Quote(contract_id="CON.F.US.MNQ.Z25", last_price=21005.5)
    provider = _FakeProvider(accounts=[account], contract=contract, quote=quote)
    service = TraderAgentService(_config(), provider)
    service.start()

    status = service.status()

    assert status.practice_account.id == 1
    assert status.contract.id == "CON.F.US.MNQ.Z25"
    assert status.current_price.last_price == 21005.5
    assert status.connection_status == ConnectionStatus.CONNECTED
    assert status.is_execution_capable is True


def test_stop_disconnects_the_provider():
    contract = Contract(id="CON.F.US.MNQ.Z25", name="MNQZ5", description="", symbol_id="F.US.MNQ", active=True)
    provider = _FakeProvider(accounts=[], contract=contract)
    service = TraderAgentService(_config(), provider)
    service.start()

    service.stop()

    assert provider.calls[-1] == "disconnect"
    assert service.status().connection_status == ConnectionStatus.DISCONNECTED
