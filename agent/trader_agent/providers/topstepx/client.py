"""REST client for the ProjectX Gateway API (TopstepX).

Endpoint paths and payload shapes below follow
docs/integrations/projectx/PROJECTX_API_REFERENCE.md (an EdgeLog-owned
reference distilled from the official ProjectX Gateway docs). Where that
reference explicitly flags something as unverified (see its "Gaps / do
not guess" section), this client is written defensively rather than
guessing: `/api/Contract/search`'s schema is one such gap, which is why
contract resolution below uses `/api/Contract/available` instead -- that
one is fully documented, and it's sufficient to find MNQ's active
contract.

Account-search does not document any field that distinguishes a Practice
account from other account types (the reference explicitly says realtime
payloads *may* expose `simulated`, but the REST search response's
documented fields are just id/name/balance/canTrade/isVisible). Practice
detection here is therefore still a best-effort, name-based heuristic --
`TOPSTEPX_PRACTICE_ACCOUNT_ID` (see config.py) exists specifically so a
trader can pin the correct account once they've seen their own real
account list rather than trust the heuristic blindly.
"""
from __future__ import annotations

from typing import Optional

import requests

from trader_agent.providers.base import Account, Contract
from trader_agent.providers.topstepx.errors import (
    AuthenticationError,
    ProviderConnectionError,
    ProviderResponseError,
    RateLimitError,
)

DEFAULT_TIMEOUT_SECONDS = 10


class TopstepXRestClient:
    def __init__(self, base_url: str, username: str, api_key: str, session: Optional[requests.Session] = None):
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._api_key = api_key
        self._session = session or requests.Session()
        self._token: Optional[str] = None

    @property
    def token(self) -> Optional[str]:
        return self._token

    @property
    def is_authenticated(self) -> bool:
        return self._token is not None

    def authenticate(self) -> str:
        """POST /api/Auth/loginKey with {userName, apiKey}. Returns and
        caches the session token (valid 24h per the reference doc). Never
        logs the API key or the token. A failed login can still return
        HTTP 200 -- always check `success`, not just the status code."""
        body = self._post(
            "/api/Auth/loginKey",
            json={"userName": self._username, "apiKey": self._api_key},
            authenticated=False,
        )
        token = body.get("token")
        if not body.get("success") or not token:
            raise AuthenticationError(
                f"TopstepX login failed (errorCode={body.get('errorCode')}): {body.get('errorMessage')}"
            )
        self._token = token
        return token

    def validate_session(self) -> str:
        """POST /api/Auth/validate. Tokens last 24h; a long-running agent
        should call this well before then and adopt the returned
        `newToken`. Not yet wired into the service's run loop (ST0 is a
        short-lived foreground process today) -- see agent/README.md."""
        body = self._post("/api/Auth/validate", json={})
        new_token = body.get("newToken")
        if not body.get("success") or not new_token:
            raise AuthenticationError(
                f"TopstepX session validation failed (errorCode={body.get('errorCode')}): {body.get('errorMessage')}"
            )
        self._token = new_token
        return new_token

    def search_accounts(self, only_active: bool = True) -> list[Account]:
        body = self._post("/api/Account/search", json={"onlyActiveAccounts": only_active})
        raw_accounts = body.get("accounts") if isinstance(body.get("accounts"), list) else body.get("data") or []
        return [self._parse_account(item) for item in raw_accounts]

    def place_order(
        self,
        account_id: int,
        contract_id: str,
        order_type: int,
        side: int,
        size: int,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        trail_price: Optional[float] = None,
        custom_tag: Optional[str] = None,
    ) -> dict:
        """POST /api/Order/place. Returns the raw response body -- the
        caller (TopstepXProvider) is responsible for checking `success`
        rather than trusting the presence of `orderId` alone; a rejected
        order can still come back with one (per the reference doc)."""
        return self._post(
            "/api/Order/place",
            json={
                "accountId": account_id,
                "contractId": contract_id,
                "type": order_type,
                "side": side,
                "size": size,
                "limitPrice": limit_price,
                "stopPrice": stop_price,
                "trailPrice": trail_price,
                "customTag": custom_tag,
                "stopLossBracket": None,
                "takeProfitBracket": None,
            },
        )

    def cancel_order(self, account_id: int, order_id: int) -> dict:
        """POST /api/Order/cancel."""
        return self._post("/api/Order/cancel", json={"accountId": account_id, "orderId": order_id})

    def search_orders(self, account_id: int, start_timestamp: str, end_timestamp: Optional[str] = None) -> list[dict]:
        """POST /api/Order/search. Returns the raw order dicts; parsing
        into the provider-agnostic Order dataclass happens in
        TopstepXProvider, since the exact meaning of the provider's status
        enum isn't confirmed (see the reference doc's "Gaps" section)."""
        body = self._post(
            "/api/Order/search",
            json={"accountId": account_id, "startTimestamp": start_timestamp, "endTimestamp": end_timestamp},
        )
        return body.get("orders") if isinstance(body.get("orders"), list) else body.get("data") or []

    def list_available_contracts(self, live: bool = False) -> list[Contract]:
        """POST /api/Contract/available -- the one contract-discovery
        endpoint whose request/response shape is fully documented.
        Returns every available contract; callers filter client-side for
        the symbol/active-month they want (see
        TopstepXProvider.resolve_contract)."""
        body = self._post("/api/Contract/available", json={"live": live})
        raw_contracts = body.get("contracts") if isinstance(body.get("contracts"), list) else body.get("data") or []
        return [self._parse_contract(item) for item in raw_contracts]

    def _post(self, path: str, json: dict, authenticated: bool = True) -> dict:
        headers = {}
        if authenticated:
            if not self._token:
                raise AuthenticationError("Not authenticated -- call authenticate() first")
            headers["Authorization"] = f"Bearer {self._token}"

        try:
            response = self._session.post(
                f"{self._base_url}{path}", json=json, headers=headers, timeout=DEFAULT_TIMEOUT_SECONDS
            )
        except requests.RequestException as exc:
            raise ProviderConnectionError(f"Could not reach TopstepX at {path}: {exc}") from exc

        if response.status_code == 401:
            raise AuthenticationError(f"TopstepX rejected the request to {path} as unauthorized")
        if response.status_code == 429:
            raise RateLimitError(
                f"TopstepX rate-limited {path} (429) -- back off rather than retrying immediately"
            )
        if not response.ok:
            raise ProviderResponseError(f"TopstepX returned {response.status_code} for {path}: {response.text[:500]}")

        try:
            return response.json()
        except ValueError as exc:
            raise ProviderResponseError(f"TopstepX returned a non-JSON response for {path}") from exc

    @staticmethod
    def _parse_account(item: dict) -> Account:
        account_id = item.get("id")
        name = item.get("name") or f"account-{account_id}"
        is_practice = TopstepXRestClient._infer_is_practice(item, name)

        return Account(id=account_id, name=name, is_practice=is_practice, balance=item.get("balance"), raw=item)

    @staticmethod
    def _infer_is_practice(item: dict, name: str) -> bool:
        # `simulated` is documented as sometimes present on *realtime*
        # payloads, not the REST search response -- checked here too in
        # case a future API revision adds it, but the name-based fallback
        # is what actually carries this today. Never trust this alone;
        # see TOPSTEPX_PRACTICE_ACCOUNT_ID.
        value = item.get("simulated")
        if isinstance(value, bool):
            return value
        return "practice" in name.lower() or "demo" in name.lower() or "sim" in name.lower()

    @staticmethod
    def _parse_contract(item: dict) -> Contract:
        return Contract(
            id=item.get("id"),
            name=item.get("name") or "",
            description=item.get("description") or "",
            symbol_id=item.get("symbolId") or "",
            tick_size=item.get("tickSize"),
            tick_value=item.get("tickValue"),
            active=bool(item.get("activeContract")),
            raw=item,
        )
