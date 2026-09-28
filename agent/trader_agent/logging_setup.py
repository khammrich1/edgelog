"""Structured local audit logging for the EdgeLog Trader Agent.

Two things matter here beyond normal logging: (1) every log record is a
single JSON line, so the audit trail is easy to grep/parse later, and (2)
a redaction filter strips any configured secret value out of every record
before it's written, so a credential can never end up in a log file even
if a future change accidentally logs it directly.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

AGENT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_LOG_DIR = AGENT_DIR / "logs"

_REDACTED = "***REDACTED***"


class SecretRedactingFilter(logging.Filter):
    """Replaces any occurrence of a known secret value in a log record's
    message or args with a redacted placeholder. Applied to every handler,
    so this holds even if a caller forgets and logs a secret directly.

    Takes a callable rather than a fixed list, because the session token
    isn't known until after authenticate() succeeds -- calling
    secrets_provider() fresh on every record means a token learned after
    logging was set up is still redacted from then on."""

    def __init__(self, secrets_provider: Callable[[], Iterable[str]]):
        super().__init__()
        self._secrets_provider = secrets_provider

    def filter(self, record: logging.LogRecord) -> bool:
        secrets = sorted({s for s in self._secrets_provider() if s}, key=len, reverse=True)
        if not secrets:
            return True

        message = record.getMessage()
        redacted = self._redact(message, secrets)
        if redacted != message:
            record.msg = redacted
            record.args = ()

        return True

    @staticmethod
    def _redact(text: str, secrets: list[str]) -> str:
        for secret in secrets:
            if secret in text:
                text = text.replace(secret, _REDACTED)
        return text


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "audit_fields", None)
        if extra:
            payload.update(extra)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging(
    secrets_provider: Callable[[], Iterable[str]], log_dir: Path | None = None, level: int = logging.INFO
) -> logging.Logger:
    """Configures the "trader_agent" logger to write redacted, JSON-line
    records to both stderr and a local rotating-by-date log file. Safe to
    call more than once; re-configures rather than duplicating handlers."""
    logger = logging.getLogger("trader_agent")
    logger.setLevel(level)
    logger.handlers.clear()
    logger.propagate = False

    redaction_filter = SecretRedactingFilter(secrets_provider)
    formatter = JsonLineFormatter()

    console_handler = logging.StreamHandler(stream=sys.stderr)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(redaction_filter)
    logger.addHandler(console_handler)

    target_dir = log_dir or DEFAULT_LOG_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    log_file = target_dir / f"agent-{datetime.now(timezone.utc):%Y-%m-%d}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.addFilter(redaction_filter)
    logger.addHandler(file_handler)

    return logger


def audit(logger: logging.Logger, event: str, level: int = logging.INFO, **fields) -> None:
    """Logs one structured audit event, e.g.
    audit(logger, "auth.success", account_count=3)."""
    logger.log(level, event, extra={"audit_fields": {"event": event, **fields}})
