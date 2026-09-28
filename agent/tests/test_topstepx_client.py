import pytest
import requests

from trader_agent.providers.topstepx.client import TopstepXRestClient
from trader_agent.providers.topstepx.errors import (
    AuthenticationError,
    ProviderConnectionError,
    ProviderResponseError,
    RateLimitError,
)


class _FakeResponse:
    def __init__(self, status_code=200, json_body=None, text="", ok=None):
        self.status_code = status_code
        self._json_body = json_body if json_body is not None else {}
        self.text = text
        self.ok = ok if ok is not None else 200 <= status_code < 300

    def json(self):
        return self._json_body


class _FakeSession:
    def __init__(self, responses=None, raise_exc=None):
        self._responses = responses or []
        self._raise_exc = raise_exc
        self.calls = []

    def post(self, url, json, headers, timeout):
        self.calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        if self._raise_exc:
            raise self._raise_exc
        return self._responses.pop(0)


def _client(session):
    return TopstepXRestClient(
        base_url="https://api.topstepx.com", username="trader1", api_key="secret-key", session=session
    )


def test_authenticate_success_caches_token_and_sends_expected_payload():
    session = _FakeSession(responses=[_FakeResponse(json_body={"success": True, "token": "jwt-token"})])
    client = _client(session)

    token = client.authenticate()

    assert token == "jwt-token"
    assert client.token == "jwt-token"
    assert client.is_authenticated is True
    call = session.calls[0]
    assert call["url"] == "https://api.topstepx.com/api/Auth/loginKey"
    assert call["json"] == {"userName": "trader1", "apiKey": "secret-key"}
    assert "Authorization" not in call["headers"]  # login itself is unauthenticated


def test_authenticate_failure_raises_without_leaking_the_api_key():
    session = _FakeSession(
        responses=[_FakeResponse(json_body={"success": False, "errorCode": 3, "errorMessage": "Bad credentials"})]
    )
    client = _client(session)

    with pytest.raises(AuthenticationError) as exc_info:
        client.authenticate()

    assert "secret-key" not in str(exc_info.value)
    assert "Bad credentials" in str(exc_info.value)


def test_search_accounts_requires_prior_authentication():
    client = _client(_FakeSession())

    with pytest.raises(AuthenticationError):
        client.search_accounts()


def test_search_accounts_sends_only_active_accounts_by_default():
    session = _FakeSession(
        responses=[
            _FakeResponse(json_body={"success": True, "token": "jwt-token"}),
            _FakeResponse(json_body={"accounts": []}),
        ]
    )
    client = _client(session)
    client.authenticate()

    client.search_accounts()

    search_call = session.calls[1]
    assert search_call["url"] == "https://api.topstepx.com/api/Account/search"
    assert search_call["json"] == {"onlyActiveAccounts": True}


def test_search_accounts_parses_accounts_and_infers_practice_by_flag():
    session = _FakeSession(
        responses=[
            _FakeResponse(json_body={"success": True, "token": "jwt-token"}),
            _FakeResponse(
                json_body={
                    "accounts": [
                        {"id": 1, "name": "Main Account", "balance": 50000, "canTrade": True, "simulated": False},
                        {"id": 2, "name": "Practice Account", "balance": 150000, "canTrade": True, "simulated": True},
                    ]
                }
            ),
        ]
    )
    client = _client(session)
    client.authenticate()

    accounts = client.search_accounts()

    assert len(accounts) == 2
    assert accounts[0].is_practice is False
    assert accounts[1].is_practice is True
    assert accounts[1].balance == 150000
    auth_call = session.calls[1]
    assert auth_call["headers"]["Authorization"] == "Bearer jwt-token"


def test_search_accounts_falls_back_to_name_based_practice_detection():
    session = _FakeSession(
        responses=[
            _FakeResponse(json_body={"success": True, "token": "jwt-token"}),
            _FakeResponse(json_body={"accounts": [{"id": 7, "name": "TopstepX Practice"}]}),
        ]
    )
    client = _client(session)
    client.authenticate()

    accounts = client.search_accounts()

    assert accounts[0].is_practice is True


def test_list_available_contracts_parses_active_flag_and_tick_fields():
    session = _FakeSession(
        responses=[
            _FakeResponse(json_body={"success": True, "token": "jwt-token"}),
            _FakeResponse(
                json_body={
                    "contracts": [
                        {
                            "id": "CON.F.US.MNQ.Z25",
                            "name": "MNQZ5",
                            "description": "Micro E-mini Nasdaq-100: December 2025",
                            "tickSize": 0.25,
                            "tickValue": 0.5,
                            "activeContract": True,
                            "symbolId": "F.US.MNQ",
                        }
                    ]
                }
            ),
        ]
    )
    client = _client(session)
    client.authenticate()

    contracts = client.list_available_contracts()

    assert len(contracts) == 1
    contract = contracts[0]
    assert contract.id == "CON.F.US.MNQ.Z25"
    assert contract.active is True
    assert contract.tick_size == 0.25
    assert contract.tick_value == 0.5
    search_call = session.calls[1]
    assert search_call["url"] == "https://api.topstepx.com/api/Contract/available"
    assert search_call["json"] == {"live": False}


def test_validate_session_replaces_the_cached_token():
    session = _FakeSession(
        responses=[
            _FakeResponse(json_body={"success": True, "token": "jwt-token"}),
            _FakeResponse(json_body={"success": True, "newToken": "refreshed-token"}),
        ]
    )
    client = _client(session)
    client.authenticate()

    new_token = client.validate_session()

    assert new_token == "refreshed-token"
    assert client.token == "refreshed-token"


def test_validate_session_failure_raises_authentication_error():
    session = _FakeSession(
        responses=[
            _FakeResponse(json_body={"success": True, "token": "jwt-token"}),
            _FakeResponse(json_body={"success": False, "errorCode": 1, "errorMessage": "Session expired"}),
        ]
    )
    client = _client(session)
    client.authenticate()

    with pytest.raises(AuthenticationError):
        client.validate_session()


def test_rate_limited_response_raises_rate_limit_error():
    session = _FakeSession(
        responses=[
            _FakeResponse(json_body={"success": True, "token": "jwt-token"}),
            _FakeResponse(status_code=429, ok=False, text="Too Many Requests"),
        ]
    )
    client = _client(session)
    client.authenticate()

    with pytest.raises(RateLimitError):
        client.search_accounts()


def test_unauthorized_response_raises_authentication_error():
    session = _FakeSession(
        responses=[
            _FakeResponse(json_body={"success": True, "token": "jwt-token"}),
            _FakeResponse(status_code=401, ok=False, text="Unauthorized"),
        ]
    )
    client = _client(session)
    client.authenticate()

    with pytest.raises(AuthenticationError):
        client.search_accounts()


def test_non_2xx_response_raises_provider_response_error():
    session = _FakeSession(
        responses=[
            _FakeResponse(json_body={"success": True, "token": "jwt-token"}),
            _FakeResponse(status_code=500, ok=False, text="Server error"),
        ]
    )
    client = _client(session)
    client.authenticate()

    with pytest.raises(ProviderResponseError):
        client.search_accounts()


def test_place_order_sends_the_documented_request_shape():
    session = _FakeSession(
        responses=[
            _FakeResponse(json_body={"success": True, "token": "jwt-token"}),
            _FakeResponse(json_body={"orderId": 9056, "success": True, "errorCode": 0, "errorMessage": None}),
        ]
    )
    client = _client(session)
    client.authenticate()

    body = client.place_order(
        account_id=123,
        contract_id="CON.F.US.MNQ.Z25",
        order_type=1,
        side=0,
        size=1,
        limit_price=25000.0,
        custom_tag="edgelog-abc123",
    )

    assert body == {"orderId": 9056, "success": True, "errorCode": 0, "errorMessage": None}
    place_call = session.calls[1]
    assert place_call["url"] == "https://api.topstepx.com/api/Order/place"
    assert place_call["json"] == {
        "accountId": 123,
        "contractId": "CON.F.US.MNQ.Z25",
        "type": 1,
        "side": 0,
        "size": 1,
        "limitPrice": 25000.0,
        "stopPrice": None,
        "trailPrice": None,
        "customTag": "edgelog-abc123",
        "stopLossBracket": None,
        "takeProfitBracket": None,
    }


def test_place_order_response_with_success_false_is_returned_not_raised():
    # A rejected order can still be a normal 200 response -- the caller
    # (TopstepXProvider) is responsible for checking `success`, not this
    # client method.
    session = _FakeSession(
        responses=[
            _FakeResponse(json_body={"success": True, "token": "jwt-token"}),
            _FakeResponse(
                json_body={"orderId": 9057, "success": False, "errorCode": 3, "errorMessage": "InsufficientFunds"}
            ),
        ]
    )
    client = _client(session)
    client.authenticate()

    body = client.place_order(account_id=123, contract_id="CON.F.US.MNQ.Z25", order_type=1, side=0, size=1)

    assert body["success"] is False
    assert body["errorMessage"] == "InsufficientFunds"


def test_cancel_order_sends_account_and_order_id():
    session = _FakeSession(
        responses=[
            _FakeResponse(json_body={"success": True, "token": "jwt-token"}),
            _FakeResponse(json_body={"success": True, "errorCode": 0, "errorMessage": None}),
        ]
    )
    client = _client(session)
    client.authenticate()

    body = client.cancel_order(account_id=123, order_id=9056)

    assert body["success"] is True
    cancel_call = session.calls[1]
    assert cancel_call["url"] == "https://api.topstepx.com/api/Order/cancel"
    assert cancel_call["json"] == {"accountId": 123, "orderId": 9056}


def test_search_orders_sends_account_and_time_range_and_parses_list():
    session = _FakeSession(
        responses=[
            _FakeResponse(json_body={"success": True, "token": "jwt-token"}),
            _FakeResponse(json_body={"orders": [{"id": 9056, "accountId": 123, "size": 1, "fillVolume": 0}]}),
        ]
    )
    client = _client(session)
    client.authenticate()

    orders = client.search_orders(account_id=123, start_timestamp="2026-09-01T00:00:00+00:00", end_timestamp=None)

    assert orders == [{"id": 9056, "accountId": 123, "size": 1, "fillVolume": 0}]
    search_call = session.calls[1]
    assert search_call["url"] == "https://api.topstepx.com/api/Order/search"
    assert search_call["json"] == {
        "accountId": 123,
        "startTimestamp": "2026-09-01T00:00:00+00:00",
        "endTimestamp": None,
    }


def test_network_error_raises_provider_connection_error():
    session = _FakeSession(raise_exc=requests.ConnectionError("connection refused"))
    client = _client(session)

    with pytest.raises(ProviderConnectionError):
        client.authenticate()
