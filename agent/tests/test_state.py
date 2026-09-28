from trader_agent.state import ConnectionStatus, HealthTracker


def _tracker(stale_after=10.0, start_time=0.0):
    clock = {"now": start_time}
    tracker = HealthTracker(stale_after_seconds=stale_after, clock=lambda: clock["now"])
    return tracker, clock


def test_starts_disconnected():
    tracker, _clock = _tracker()
    assert tracker.status == ConnectionStatus.DISCONNECTED
    assert tracker.is_execution_capable is False


def test_connecting_then_connected_transitions():
    tracker, _clock = _tracker()

    tracker.mark_connecting()
    assert tracker.status == ConnectionStatus.CONNECTING

    tracker.mark_connected()
    assert tracker.status == ConnectionStatus.CONNECTED


def test_is_execution_capable_requires_authenticated_and_connected():
    tracker, _clock = _tracker()
    tracker.mark_connected()
    assert tracker.is_execution_capable is False  # not authenticated yet

    tracker.mark_authenticated()
    assert tracker.is_execution_capable is True


def test_market_data_going_stale_marks_status_stale_and_not_execution_capable():
    tracker, clock = _tracker(stale_after=10.0)
    tracker.mark_connected()
    tracker.mark_authenticated()
    assert tracker.status == ConnectionStatus.CONNECTED
    assert tracker.is_execution_capable is True

    clock["now"] = 11.0  # 11s with no data, threshold is 10s
    assert tracker.status == ConnectionStatus.STALE
    assert tracker.is_execution_capable is False


def test_fresh_market_data_clears_staleness():
    tracker, clock = _tracker(stale_after=10.0)
    tracker.mark_connected()
    tracker.mark_authenticated()

    clock["now"] = 11.0
    assert tracker.status == ConnectionStatus.STALE

    tracker.mark_market_data_received()
    assert tracker.status == ConnectionStatus.CONNECTED
    assert tracker.is_execution_capable is True


def test_disconnect_after_being_connected_goes_to_reconnecting_not_disconnected():
    tracker, _clock = _tracker()
    tracker.mark_connected()
    tracker.mark_authenticated()

    tracker.mark_disconnected()

    assert tracker.status == ConnectionStatus.RECONNECTING
    assert tracker.is_execution_capable is False


def test_disconnect_before_ever_connecting_stays_disconnected():
    tracker, _clock = _tracker()

    tracker.mark_disconnected()

    assert tracker.status == ConnectionStatus.DISCONNECTED


def test_reconnecting_and_reauthenticating_restores_execution_capable():
    tracker, clock = _tracker()
    tracker.mark_connected()
    tracker.mark_authenticated()
    tracker.mark_disconnected()
    assert tracker.is_execution_capable is False

    tracker.mark_connecting()
    tracker.mark_connected()
    tracker.mark_authenticated()

    assert tracker.status == ConnectionStatus.CONNECTED
    assert tracker.is_execution_capable is True
