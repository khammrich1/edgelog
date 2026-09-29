import json

from trader_agent.trading_control import TradingControl


def test_starts_with_kill_switch_disengaged_and_auto_trading_off(tmp_path):
    control = TradingControl(state_path=tmp_path / "state.json")

    assert control.kill_switch_engaged is False
    assert control.auto_trading_enabled is False
    assert control.block_reason() is None


def test_engage_kill_switch_persists_reason_and_blocks(tmp_path):
    control = TradingControl(state_path=tmp_path / "state.json")

    control.engage_kill_switch("testing the stop")

    assert control.kill_switch_engaged is True
    assert control.block_reason() == "Kill switch engaged: testing the stop"


def test_kill_switch_survives_reload_from_disk(tmp_path):
    path = tmp_path / "state.json"
    TradingControl(state_path=path).engage_kill_switch("network looked wrong")

    reloaded = TradingControl(state_path=path)

    assert reloaded.kill_switch_engaged is True
    assert reloaded.block_reason() == "Kill switch engaged: network looked wrong"


def test_clear_kill_switch_unblocks_and_persists(tmp_path):
    path = tmp_path / "state.json"
    control = TradingControl(state_path=path)
    control.engage_kill_switch("temporary")

    control.clear_kill_switch()

    assert control.kill_switch_engaged is False
    assert control.block_reason() is None
    assert TradingControl(state_path=path).kill_switch_engaged is False


def test_auto_trading_is_forced_off_on_load_even_if_the_state_file_says_otherwise(tmp_path):
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"auto_trading_enabled": True}))

    control = TradingControl(state_path=path)

    assert control.auto_trading_enabled is False
    # And the file itself is corrected back to False, not left lying.
    assert json.loads(path.read_text())["auto_trading_enabled"] is False


def test_unreadable_state_file_falls_back_to_safe_defaults_instead_of_raising(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{not valid json")

    control = TradingControl(state_path=path)

    assert control.kill_switch_engaged is False
    assert control.auto_trading_enabled is False
