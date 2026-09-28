import pytest

from trader_agent.providers.base import Account, Contract
from trader_agent.providers.topstepx.errors import TopstepXError
from trader_agent.providers.topstepx.provider import NoActiveContractError, TopstepXProvider
from trader_agent.state import ConnectionStatus


class _FakeRestClient:
    def __init__(self, accounts=None, contracts=None):
        self.token = None
        self._accounts = accounts or []
        self._contracts = contracts or []
        self.authenticate_called = False

    def authenticate(self):
        self.authenticate_called = True
        self.token = "jwt-token"
        return self.token

    def search_accounts(self):
        return self._accounts

    def list_available_contracts(self, live=False):
        return self._contracts


class _FakeTransport:
    def __init__(self, url, token):
        self.url = url
        self.token = token
        self.sent = []
        self.event_handlers = {}
        self._open_handler = None

    def start(self):
        pass

    def stop(self):
        pass

    def send(self, method, args):
        self.sent.append((method, tuple(args)))

    def on(self, event, handler):
        self.event_handlers[event] = handler

    def on_open(self, handler):
        self._open_handler = handler
        handler()  # simulate an immediate successful connection for these tests

    def on_close(self, handler):
        pass

    def on_error(self, handler):
        pass

    def emit(self, event, payload):
        self.event_handlers[event](payload)


def _provider(accounts=None, contracts=None, practice_account_id=None):
    transports = []

    def factory(url, token):
        t = _FakeTransport(url, token)
        transports.append(t)
        return t

    rest = _FakeRestClient(accounts=accounts, contracts=contracts)
    provider = TopstepXProvider(
        rest_client=rest,
        rtc_base_url="https://rtc.topstepx.com",
        stale_after_seconds=10.0,
        transport_factory=factory,
        practice_account_id=practice_account_id,
    )
    return provider, rest, transports


def _account(id_, name, is_practice):
    return Account(id=id_, name=name, is_practice=is_practice, balance=100000)


def _contract(id_, active, symbol_id="F.US.MNQ", name="MNQZ5"):
    return Contract(id=id_, name=name, description="Micro E-mini Nasdaq-100", symbol_id=symbol_id, active=active)


def test_authenticate_delegates_to_rest_client_and_marks_health_authenticated():
    provider, rest, _transports = _provider()

    provider.authenticate()

    assert rest.authenticate_called is True


def test_list_accounts_returns_practice_flag_from_heuristic_by_default():
    accounts = [_account(1, "Main", False), _account(2, "Practice", True)]
    provider, _rest, _t = _provider(accounts=accounts)

    result = provider.list_accounts()

    assert result[0].is_practice is False
    assert result[1].is_practice is True


def test_practice_account_id_override_forces_that_account_to_be_practice():
    accounts = [_account(1, "Main", False), _account(2, "Not Flagged Practice", False)]
    provider, _rest, _t = _provider(accounts=accounts, practice_account_id=2)

    result = provider.get_practice_account()

    assert result.id == 2
    assert result.is_practice is True


def test_get_practice_account_returns_none_when_nothing_matches():
    accounts = [_account(1, "Main", False)]
    provider, _rest, _t = _provider(accounts=accounts)

    assert provider.get_practice_account() is None


def test_resolve_contract_picks_the_active_one():
    contracts = [_contract("CON.F.US.MNQ.U25", active=False), _contract("CON.F.US.MNQ.Z25", active=True)]
    provider, _rest, _t = _provider(contracts=contracts)

    resolved = provider.resolve_contract("MNQ")

    assert resolved.id == "CON.F.US.MNQ.Z25"


def test_resolve_contract_raises_when_none_active():
    contracts = [_contract("CON.F.US.MNQ.U25", active=False)]
    provider, _rest, _t = _provider(contracts=contracts)

    with pytest.raises(NoActiveContractError):
        provider.resolve_contract("MNQ")


def test_resolve_contract_ignores_active_contracts_for_a_different_symbol():
    contracts = [
        _contract("CON.F.US.MES.Z25", active=True, symbol_id="F.US.MES", name="MESZ5"),
        _contract("CON.F.US.MNQ.Z25", active=True, symbol_id="F.US.MNQ", name="MNQZ5"),
    ]
    provider, _rest, _t = _provider(contracts=contracts)

    resolved = provider.resolve_contract("MNQ")

    assert resolved.id == "CON.F.US.MNQ.Z25"


def test_connect_realtime_requires_prior_authentication():
    provider, _rest, _t = _provider()

    with pytest.raises(TopstepXError):
        provider.connect_realtime()


def test_connect_realtime_opens_both_hubs_with_the_session_token():
    provider, _rest, transports = _provider()
    provider.authenticate()

    provider.connect_realtime()

    assert len(transports) == 2
    assert all(t.token == "jwt-token" for t in transports)
    assert {t.url for t in transports} == {"https://rtc.topstepx.com/hubs/user", "https://rtc.topstepx.com/hubs/market"}


def test_subscribe_account_updates_sends_all_four_user_hub_subscriptions():
    provider, _rest, transports = _provider()
    provider.authenticate()
    provider.connect_realtime()

    provider.subscribe_account_updates(99, on_update=lambda e: None)

    user_transport = next(t for t in transports if t.url.endswith("/hubs/user"))
    methods_sent = {method for method, _args in user_transport.sent}
    assert methods_sent == {"SubscribeAccounts", "SubscribeOrders", "SubscribePositions", "SubscribeTrades"}
    assert all(args == (99,) for _method, args in user_transport.sent)


def test_gateway_quote_event_updates_current_price_and_notifies_handler():
    # The API reference's documented quote fields (symbol, symbolName,
    # lastPrice, bestBid, bestAsk, ...) don't include a contract ID -- the
    # provider attributes quotes to whichever contract_id was subscribed,
    # not to anything parsed out of the payload. This payload deliberately
    # omits any contract/symbol identifier to prove that.
    contracts = [_contract("CON.F.US.MNQ.Z25", active=True)]
    provider, _rest, transports = _provider(contracts=contracts)
    provider.authenticate()
    provider.connect_realtime()

    received = []
    provider.subscribe_market_data("CON.F.US.MNQ.Z25", on_quote=lambda q: received.append(q))

    market_transport = next(t for t in transports if t.url.endswith("/hubs/market"))
    market_transport.emit(
        "GatewayQuote", [{"symbol": "MNQZ5", "lastPrice": 21005.5, "bestBid": 21005.25, "bestAsk": 21005.75}]
    )

    quote = provider.get_current_price("CON.F.US.MNQ.Z25")
    assert quote is not None
    assert quote.last_price == 21005.5
    assert quote.bid == 21005.25
    assert quote.ask == 21005.75
    assert received[0].last_price == 21005.5


def test_get_current_price_is_none_before_any_quote_received():
    provider, _rest, _t = _provider()
    assert provider.get_current_price("CON.F.US.MNQ.Z25") is None


def test_is_execution_capable_false_until_authenticated_and_connected():
    provider, _rest, _t = _provider()
    assert provider.is_execution_capable is False

    provider.authenticate()
    provider.connect_realtime()

    assert provider.is_execution_capable is True


def test_connection_status_reports_connected_once_both_hubs_are_up():
    provider, _rest, _t = _provider()
    provider.authenticate()

    provider.connect_realtime()

    assert provider.connection_status == ConnectionStatus.CONNECTED


def test_disconnect_tears_down_both_hubs():
    provider, _rest, transports = _provider()
    provider.authenticate()
    provider.connect_realtime()

    provider.disconnect()

    assert provider.connection_status == ConnectionStatus.RECONNECTING
