"""Local configuration loading for the EdgeLog Trader Agent.

Everything here is read from a local .env file (see .env.example) or the
process environment. Nothing in this module ever talks to the network or
to EdgeLog cloud -- credentials loaded here stay on this machine.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

AGENT_DIR = Path(__file__).resolve().parent.parent


class ConfigError(Exception):
    """Raised when required local configuration is missing or invalid."""


@dataclass(frozen=True)
class AgentConfig:
    username: str
    api_key: str
    symbol: str
    api_base_url: str
    rtc_base_url: str
    stale_after_seconds: float
    practice_account_id: Optional[int] = None

    def masked_api_key(self) -> str:
        """Safe-to-log representation: never the real value, only enough to
        confirm which key is loaded (e.g. when comparing against a
        previously rotated one)."""
        if len(self.api_key) <= 4:
            return "*" * len(self.api_key)
        return f"{'*' * (len(self.api_key) - 4)}{self.api_key[-4:]}"


def load_config(env_file: Optional[Path] = None) -> AgentConfig:
    """Loads configuration from a local .env file plus the process
    environment (the environment always wins, matching python-dotenv's
    default behavior). Raises ConfigError with a clear, secret-free message
    if anything required is missing."""
    dotenv_path = env_file or (AGENT_DIR / ".env")
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path, override=False)

    username = os.environ.get("TOPSTEPX_USERNAME", "").strip()
    api_key = os.environ.get("TOPSTEPX_API_KEY", "").strip()

    missing = [name for name, value in [("TOPSTEPX_USERNAME", username), ("TOPSTEPX_API_KEY", api_key)] if not value]
    if missing:
        raise ConfigError(
            "Missing required configuration: "
            + ", ".join(missing)
            + f". Copy {AGENT_DIR / '.env.example'} to {dotenv_path} and fill it in."
        )

    practice_account_id_raw = os.environ.get("TOPSTEPX_PRACTICE_ACCOUNT_ID", "").strip()
    practice_account_id = int(practice_account_id_raw) if practice_account_id_raw else None

    return AgentConfig(
        username=username,
        api_key=api_key,
        symbol=os.environ.get("TOPSTEPX_SYMBOL", "MNQ").strip() or "MNQ",
        api_base_url=os.environ.get("TOPSTEPX_API_BASE_URL", "https://api.topstepx.com").rstrip("/"),
        rtc_base_url=os.environ.get("TOPSTEPX_RTC_BASE_URL", "https://rtc.topstepx.com").rstrip("/"),
        stale_after_seconds=float(os.environ.get("TOPSTEPX_STALE_AFTER_SECONDS", "15")),
        practice_account_id=practice_account_id,
    )
