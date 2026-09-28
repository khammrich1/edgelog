import json
import logging

from trader_agent.logging_setup import JsonLineFormatter, SecretRedactingFilter, audit


def _make_record(message: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="trader_agent.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )


def test_secret_redacting_filter_strips_the_secret_from_the_message():
    record = _make_record("Authenticated with token abc123secret")
    filt = SecretRedactingFilter(lambda: ["abc123secret"])

    filt.filter(record)

    assert "abc123secret" not in record.getMessage()
    assert "REDACTED" in record.getMessage()


def test_secret_redacting_filter_is_a_noop_when_no_secret_present():
    record = _make_record("Just a normal log line")
    filt = SecretRedactingFilter(lambda: ["some-secret"])

    filt.filter(record)

    assert record.getMessage() == "Just a normal log line"


def test_secret_redacting_filter_picks_up_a_secret_learned_after_setup():
    known_secrets = []
    record = _make_record("token=late-secret-value")
    filt = SecretRedactingFilter(lambda: known_secrets)

    filt.filter(record)
    assert "late-secret-value" in record.getMessage()

    known_secrets.append("late-secret-value")
    record2 = _make_record("token=late-secret-value")
    filt.filter(record2)
    assert "late-secret-value" not in record2.getMessage()


def test_json_line_formatter_produces_valid_json_with_expected_fields():
    record = _make_record("hello world")
    formatted = JsonLineFormatter().format(record)

    payload = json.loads(formatted)
    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert "timestamp" in payload


def test_audit_helper_attaches_event_and_extra_fields_for_the_formatter():
    logger = logging.getLogger("trader_agent.test.audit")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()

    captured: list[str] = []

    class _CaptureHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(JsonLineFormatter().format(record))

    logger.addHandler(_CaptureHandler())

    audit(logger, "agent.started", contract_id="CON.F.US.MNQ.Z25")

    payload = json.loads(captured[0])
    assert payload["event"] == "agent.started"
    assert payload["contract_id"] == "CON.F.US.MNQ.Z25"
