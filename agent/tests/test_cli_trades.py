"""Deterministic, fake-based tests for the `trades` CLI command's wiring:
default output never shows raw rows, --show-rows opts in, --account-id
and the .env-pinned fallback both work, and nothing here ever touches
the network -- TraderAgentService.from_local_config and load_config are
both monkeypatched to fakes."""
from datetime import datetime, timezone

from trader_agent import cli
from trader_agent.providers.base import TradeRecord

SAMPLE_RAW = {
    "id": 1001,
    "accountId": 222222,
    "contractId": "CON.F.US.MNQ.Z25",
    "creationTimestamp": "2026-10-16T14:30:00Z",
    "price": 21005.5,
    "profitAndLoss": 38.0,
    "fees": 2.5,
    "side": 0,
    "size": 2,
    "voided": False,
    "orderId": 5551,
}


class _FakeService:
    def __init__(self, records):
        self._records = records
        self.search_trades_calls = []

    def search_trades(self, account_id, start, end=None):
        self.search_trades_calls.append((account_id, start, end))
        return self._records


def _record(raw=None):
    raw = raw or SAMPLE_RAW
    return TradeRecord(
        id=raw.get("id"),
        account_id=raw.get("accountId"),
        contract_id=raw.get("contractId"),
        creation_timestamp=raw.get("creationTimestamp"),
        price=raw.get("price"),
        profit_and_loss=raw.get("profitAndLoss"),
        fees=raw.get("fees"),
        side=raw.get("side"),
        size=raw.get("size"),
        voided=raw.get("voided"),
        order_id=raw.get("orderId"),
        raw=raw,
    )


class _FakeConfig:
    def __init__(self, practice_account_id=None):
        self.practice_account_id = practice_account_id


def _patch_service(monkeypatch, records):
    fake = _FakeService(records)
    monkeypatch.setattr(cli.TraderAgentService, "from_local_config", staticmethod(lambda: fake))
    return fake


def test_default_run_never_prints_raw_price_or_pnl_values(monkeypatch, capsys):
    _patch_service(monkeypatch, [_record()])
    monkeypatch.setattr(cli, "load_config", lambda: _FakeConfig())

    exit_code = cli.main(["trades", "--start", "2026-10-01", "--account-id", "222222"])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "21005.5" not in out
    assert "38.0" not in out
    assert "WARNING:" not in out  # --show-rows banner only appears when requested


def test_show_rows_opts_into_real_values_and_prints_the_warning(monkeypatch, capsys):
    _patch_service(monkeypatch, [_record()])
    monkeypatch.setattr(cli, "load_config", lambda: _FakeConfig())

    exit_code = cli.main(["trades", "--start", "2026-10-01", "--account-id", "222222", "--show-rows"])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "WARNING:" in out
    assert "21005.5" in out
    assert "38.0" in out
    assert "5551" not in out  # order id still masked even with --show-rows


def test_falls_back_to_pinned_practice_account_id_when_not_given(monkeypatch, capsys):
    fake = _patch_service(monkeypatch, [_record()])
    monkeypatch.setattr(cli, "load_config", lambda: _FakeConfig(practice_account_id=999))

    exit_code = cli.main(["trades", "--start", "2026-10-01"])

    assert exit_code == 0
    assert fake.search_trades_calls[0][0] == 999


def test_errors_cleanly_when_no_account_id_available_anywhere(monkeypatch, capsys):
    fake = _patch_service(monkeypatch, [_record()])
    monkeypatch.setattr(cli, "load_config", lambda: _FakeConfig(practice_account_id=None))

    exit_code = cli.main(["trades", "--start", "2026-10-01"])

    assert exit_code == 2
    assert fake.search_trades_calls == []  # never even attempted a call
    assert "no --account-id given" in capsys.readouterr().err


def test_rejects_an_unparseable_start_date_before_touching_the_service(monkeypatch, capsys):
    fake = _patch_service(monkeypatch, [_record()])
    monkeypatch.setattr(cli, "load_config", lambda: _FakeConfig())

    exit_code = cli.main(["trades", "--start", "not-a-date", "--account-id", "222222"])

    assert exit_code == 2
    assert fake.search_trades_calls == []


def test_end_defaults_to_24h_after_start(monkeypatch, capsys):
    fake = _patch_service(monkeypatch, [_record()])
    monkeypatch.setattr(cli, "load_config", lambda: _FakeConfig())

    cli.main(["trades", "--start", "2026-10-01", "--account-id", "222222"])

    account_id, start, end = fake.search_trades_calls[0]
    assert start == datetime(2026, 10, 1, tzinfo=timezone.utc)
    assert end == datetime(2026, 10, 2, tzinfo=timezone.utc)
