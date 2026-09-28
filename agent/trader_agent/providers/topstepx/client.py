"""REST client for the ProjectX Gateway API (TopstepX).

Endpoint paths and payload shapes below are taken from the publicly
documented ProjectX Gateway API (gateway.docs.projectx.com) and
cross-referenced against independent third-party client implementations,
since this agent was built without live network access to the primary
docs site. The auth endpoint and its request/response shape, and the
contract-search response shape, were confirmed from multiple independent
sources. Account-search response field names beyond `id`/`name` were not
independently confirmed -- `_parse_account` below reads several plausible
field names defensively and falls back to `None`/a name-based guess
rather than raising, and `TOPSTEPX_PRACTICE_ACCOUNT_ID` (see config.py)
exists specifically so a trader can pin the correct account once they've
seen their own real account list rather than trust the heuristic blindly.
Verify against your own account's actual response before relying on
Practice-account auto-detection.
"""
from __future__ import annotations

from typing import Optional

import requests

from trader_agent.providers.base import Account, Contract
from trader_agent.providers.topstepx.errors import (
    AuthenticationError,
    ProviderConnectionError,
    ProviderResponseError,
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
        caches the session token (valid ~24h per ProjectX docs). Never
        logs the API key or the token."""
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

    def search_accounts(self) -> list[Account]:
        body = self._post("/api/Account/search", json={})
        raw_accounts = body.get("accounts") if isinstance(body.get("accounts"), list) else body.get("data") or []
        return [self._parse_account(item) for item in raw_accounts]

    def search_contracts(self, search_text: str, live: bool = False) -> list[Contract]:
        body = self._post("/api/Contract/search", json={"searchText": search_text, "live": live})
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
        if not response.ok:
            raise ProviderResponseError(f"TopstepX returned {response.status_code} for {path}: {response.text[:500]}")

        try:
            return response.json()
        except ValueError as exc:
            raise ProviderResponseError(f"TopstepX returned a non-JSON response for {path}") from exc

    @staticmethod
    def _parse_account(item: dict) -> Account:
        account_id = item.get("id")
        name = item.get("name") or item.get("accountName") or f"account-{account_id}"
        balance = item.get("balance")
        if balance is None:
            balance = item.get("startingBalance")

        is_practice = TopstepXRestClient._infer_is_practice(item, name)

        return Account(id=account_id, name=name, is_practice=is_practice, balance=balance, raw=item)

    @staticmethod
    def _infer_is_practice(item: dict, name: str) -> bool:
        for flag_field in ("simulated", "isDemo", "isPractice", "practice"):
            value = item.get(flag_field)
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
