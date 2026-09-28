import pytest

from trader_agent.config import ConfigError, load_config


def _clear_env(monkeypatch):
    for key in [
        "TOPSTEPX_USERNAME",
        "TOPSTEPX_API_KEY",
        "TOPSTEPX_PRACTICE_ACCOUNT_ID",
        "TOPSTEPX_SYMBOL",
        "TOPSTEPX_API_BASE_URL",
        "TOPSTEPX_RTC_BASE_URL",
        "TOPSTEPX_STALE_AFTER_SECONDS",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_load_config_raises_when_username_and_api_key_missing(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    missing_env_file = tmp_path / "does-not-exist.env"

    with pytest.raises(ConfigError) as exc_info:
        load_config(env_file=missing_env_file)

    assert "TOPSTEPX_USERNAME" in str(exc_info.value)
    assert "TOPSTEPX_API_KEY" in str(exc_info.value)


def test_load_config_reads_required_fields_from_environment(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setenv("TOPSTEPX_USERNAME", "trader1")
    monkeypatch.setenv("TOPSTEPX_API_KEY", "super-secret-key")

    config = load_config(env_file=tmp_path / "does-not-exist.env")

    assert config.username == "trader1"
    assert config.api_key == "super-secret-key"
    assert config.symbol == "MNQ"
    assert config.api_base_url == "https://api.topstepx.com"
    assert config.rtc_base_url == "https://rtc.topstepx.com"
    assert config.stale_after_seconds == 15.0
    assert config.practice_account_id is None


def test_load_config_reads_optional_overrides(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setenv("TOPSTEPX_USERNAME", "trader1")
    monkeypatch.setenv("TOPSTEPX_API_KEY", "super-secret-key")
    monkeypatch.setenv("TOPSTEPX_SYMBOL", "MES")
    monkeypatch.setenv("TOPSTEPX_PRACTICE_ACCOUNT_ID", "42")
    monkeypatch.setenv("TOPSTEPX_STALE_AFTER_SECONDS", "30")

    config = load_config(env_file=tmp_path / "does-not-exist.env")

    assert config.symbol == "MES"
    assert config.practice_account_id == 42
    assert config.stale_after_seconds == 30.0


def test_load_config_reads_from_env_file(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text("TOPSTEPX_USERNAME=filetrader\nTOPSTEPX_API_KEY=file-secret\n")

    config = load_config(env_file=env_file)

    assert config.username == "filetrader"
    assert config.api_key == "file-secret"


def test_masked_api_key_never_reveals_the_real_value(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setenv("TOPSTEPX_USERNAME", "trader1")
    monkeypatch.setenv("TOPSTEPX_API_KEY", "abcdefghijklmnop")

    config = load_config(env_file=tmp_path / "does-not-exist.env")
    masked = config.masked_api_key()

    assert "abcdefghijklmnop" not in masked
    assert masked.endswith("mnop")
    assert masked != config.api_key
