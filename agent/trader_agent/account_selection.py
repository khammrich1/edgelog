"""Interactive, local-only TopstepX account discovery and selection
(issue #83). Builds on the already-implemented `search_accounts()`/
`list_accounts()` -- this module adds the missing piece: a friendly list,
an explicit multi-select prompt, and persistence of the choice so it's
used on every subsequent run without re-prompting.

Only non-secret fields (account id/name/balance/inferred type) are ever
persisted. No credential, token, or order/execution behavior is touched
here -- this is purely local-agent UX around an endpoint that already
exists and is already exercised by the existing test suite.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Optional

from trader_agent.providers.base import Account

STATE_DIR_NAME = ".state"
SELECTED_ACCOUNTS_FILENAME = "selected_accounts.json"


class AccountSelectionError(Exception):
    """Raised when the trader's typed selection can't be parsed as a valid
    choice from the displayed list."""


@dataclass(frozen=True)
class SelectedAccount:
    """The subset of an Account that's safe to persist to local disk --
    deliberately excludes `raw` (the verbatim provider payload), since
    there's no guarantee a future API revision never adds a sensitive
    field there."""

    id: int
    name: str
    is_practice: bool
    balance: Optional[float] = None

    @classmethod
    def from_account(cls, account: Account) -> "SelectedAccount":
        return cls(id=account.id, name=account.name, is_practice=account.is_practice, balance=account.balance)


def selected_accounts_path(agent_dir: Path) -> Path:
    return agent_dir / STATE_DIR_NAME / SELECTED_ACCOUNTS_FILENAME


def format_account_list(accounts: list[Account]) -> str:
    """One line per account, numbered from 1 for the prompt -- a friendly
    label/status/type display, not the raw provider payload."""
    lines = []
    for index, account in enumerate(accounts, start=1):
        kind = "Practice" if account.is_practice else "Live/Other"
        balance = f"${account.balance:,.2f}" if account.balance is not None else "balance unknown"
        lines.append(f"  {index}. [{account.id}] {account.name} -- {kind}, {balance}")
    return "\n".join(lines)


def parse_selection(raw_input: str, accounts: list[Account]) -> list[Account]:
    """Parses what the trader typed in response to the account list prompt.

    Accepts "all", or a comma/space-separated list of the 1-based numbers
    shown by format_account_list (e.g. "1,3" or "2"). Never accepts an
    account ID directly -- the numbers are positions in the displayed
    list, so a typo can't silently select an unintended, unlisted account.
    """
    cleaned = raw_input.strip()
    if not cleaned:
        raise AccountSelectionError("No selection entered -- type one or more numbers, or 'all'.")
    if cleaned.lower() == "all":
        return list(accounts)

    tokens = [t for t in cleaned.replace(",", " ").split() if t]
    selected: list[Account] = []
    seen_indices: set[int] = set()
    for token in tokens:
        if not token.isdigit():
            raise AccountSelectionError(f"'{token}' isn't a number from the list or 'all'.")
        position = int(token)
        if position < 1 or position > len(accounts):
            raise AccountSelectionError(
                f"{position} is out of range -- choose between 1 and {len(accounts)}."
            )
        if position not in seen_indices:
            seen_indices.add(position)
            selected.append(accounts[position - 1])

    if not selected:
        raise AccountSelectionError("No valid selection entered -- type one or more numbers, or 'all'.")
    return selected


def save_selected_accounts(agent_dir: Path, accounts: list[Account]) -> Path:
    """Persists the trader's chosen accounts (non-secret fields only) to
    `.state/selected_accounts.json`, gitignored and local to this machine.
    Overwrites any previous selection -- there is exactly one current
    selection, not an accumulating history."""
    path = selected_accounts_path(agent_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(SelectedAccount.from_account(a)) for a in accounts]
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path


def load_selected_accounts(agent_dir: Path) -> list[SelectedAccount]:
    """Returns the previously persisted selection, or an empty list if
    none has been made yet (first run, or the state file was removed)."""
    path = selected_accounts_path(agent_dir)
    if not path.exists():
        return []
    raw = json.loads(path.read_text())
    return [SelectedAccount(**item) for item in raw]


ReadLine = Callable[[str], str]


def run_interactive_selection(
    accounts: list[Account], agent_dir: Path, read_line: ReadLine = input, write: Callable[[str], None] = print
) -> list[SelectedAccount]:
    """Drives the full list -> prompt -> parse -> persist flow. `read_line`
    and `write` are injectable so this is fully testable without a real
    terminal; the CLI command below is the only caller that passes the
    real `input`/`print`."""
    if not accounts:
        raise AccountSelectionError("No accounts were returned for this login -- nothing to select.")

    write("Accounts available to this login:")
    write(format_account_list(accounts))
    write("")

    raw_input_value = read_line(
        "Select one or more accounts (e.g. '1,3'), or 'all': "
    )
    selected = parse_selection(raw_input_value, accounts)
    save_selected_accounts(agent_dir, selected)

    write("")
    write(f"Saved {len(selected)} selected account(s) to {selected_accounts_path(agent_dir)}:")
    for account in selected:
        write(f"  - [{account.id}] {account.name}")
    return [SelectedAccount.from_account(a) for a in selected]
