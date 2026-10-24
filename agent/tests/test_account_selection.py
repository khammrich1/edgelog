import json

import pytest

from trader_agent.account_selection import (
    AccountSelectionError,
    format_account_list,
    load_selected_accounts,
    parse_selection,
    run_interactive_selection,
    save_selected_accounts,
    selected_accounts_path,
)
from trader_agent.providers.base import Account


def _accounts():
    return [
        Account(id=111, name="Practice 50K", is_practice=True, balance=50000.0),
        Account(id=222, name="Practice 100K", is_practice=True, balance=100000.0),
        Account(id=333, name="Live Funded", is_practice=False, balance=25000.0),
    ]


def test_format_account_list_shows_id_name_type_and_balance():
    rendered = format_account_list(_accounts())

    assert "1. [111] Practice 50K -- Practice, $50,000.00" in rendered
    assert "2. [222] Practice 100K -- Practice, $100,000.00" in rendered
    assert "3. [333] Live Funded -- Live/Other, $25,000.00" in rendered


def test_format_account_list_handles_unknown_balance():
    accounts = [Account(id=1, name="No Balance", is_practice=True, balance=None)]
    rendered = format_account_list(accounts)
    assert "balance unknown" in rendered


def test_parse_selection_single_number():
    accounts = _accounts()
    assert parse_selection("2", accounts) == [accounts[1]]


def test_parse_selection_multiple_comma_separated():
    accounts = _accounts()
    assert parse_selection("1,3", accounts) == [accounts[0], accounts[2]]


def test_parse_selection_multiple_space_separated():
    accounts = _accounts()
    assert parse_selection("1 3", accounts) == [accounts[0], accounts[2]]


def test_parse_selection_all():
    accounts = _accounts()
    assert parse_selection("all", accounts) == accounts
    assert parse_selection("ALL", accounts) == accounts


def test_parse_selection_deduplicates_repeated_numbers():
    accounts = _accounts()
    assert parse_selection("1,1,2", accounts) == [accounts[0], accounts[1]]


def test_parse_selection_rejects_empty_input():
    with pytest.raises(AccountSelectionError):
        parse_selection("", _accounts())


def test_parse_selection_rejects_out_of_range_number():
    with pytest.raises(AccountSelectionError):
        parse_selection("99", _accounts())


def test_parse_selection_rejects_non_numeric_garbage():
    with pytest.raises(AccountSelectionError):
        parse_selection("yes please", _accounts())


def test_parse_selection_never_accepts_a_raw_account_id():
    """Critical: '333' must not be interpreted as account id 333 -- it's
    out of range as a 1-based position (only 3 accounts), so it must be
    rejected rather than silently matching the account whose id happens
    to equal the typed number."""
    with pytest.raises(AccountSelectionError):
        parse_selection("333", _accounts())


def test_save_and_load_selected_accounts_round_trip(tmp_path):
    accounts = _accounts()[:2]

    saved_path = save_selected_accounts(tmp_path, accounts)

    assert saved_path == selected_accounts_path(tmp_path)
    assert saved_path.exists()

    loaded = load_selected_accounts(tmp_path)
    assert [a.id for a in loaded] == [111, 222]
    assert [a.name for a in loaded] == ["Practice 50K", "Practice 100K"]
    assert loaded[0].is_practice is True


def test_save_selected_accounts_never_persists_raw_payload(tmp_path):
    account = Account(
        id=1,
        name="Has Secrets Maybe",
        is_practice=True,
        balance=1000.0,
        raw={"hypothetical_future_field": "should-never-be-written"},
    )

    path = save_selected_accounts(tmp_path, [account])
    on_disk = json.loads(path.read_text())

    assert "raw" not in on_disk[0]
    assert "hypothetical_future_field" not in json.dumps(on_disk)


def test_load_selected_accounts_returns_empty_list_when_never_selected(tmp_path):
    assert load_selected_accounts(tmp_path) == []


def test_save_selected_accounts_overwrites_previous_selection(tmp_path):
    accounts = _accounts()
    save_selected_accounts(tmp_path, [accounts[0]])
    save_selected_accounts(tmp_path, [accounts[1], accounts[2]])

    loaded = load_selected_accounts(tmp_path)
    assert [a.id for a in loaded] == [222, 333]


def test_run_interactive_selection_full_flow(tmp_path):
    accounts = _accounts()
    written_lines = []

    selected = run_interactive_selection(
        accounts,
        agent_dir=tmp_path,
        read_line=lambda _prompt: "1,2",
        write=written_lines.append,
    )

    assert [a.id for a in selected] == [111, 222]
    assert load_selected_accounts(tmp_path) != []
    assert any("Practice 50K" in line for line in written_lines)
    assert any(str(selected_accounts_path(tmp_path)) in line for line in written_lines)


def test_run_interactive_selection_raises_on_invalid_input_without_persisting(tmp_path):
    with pytest.raises(AccountSelectionError):
        run_interactive_selection(
            _accounts(),
            agent_dir=tmp_path,
            read_line=lambda _prompt: "not a number",
            write=lambda _line: None,
        )

    assert load_selected_accounts(tmp_path) == []


def test_run_interactive_selection_raises_when_no_accounts_available(tmp_path):
    with pytest.raises(AccountSelectionError):
        run_interactive_selection([], agent_dir=tmp_path, read_line=lambda _p: "all", write=lambda _l: None)
