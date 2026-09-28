from trader_agent.providers.topstepx.realtime import RealtimeHub
from trader_agent.state import ConnectionStatus, HealthTracker


class _FakeTransport:
    """Records everything sent/registered and lets tests drive
    on_open/on_close/on_error/incoming events directly -- no real
    network, no dependency on signalrcore's actual behavior."""

    def __init__(self, url, token):
        self.url = url
        self.token = token
        self.sent = []
        self.event_handlers = {}
        self._open_handler = None
        self._close_handler = None
        self._error_handler = None
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def send(self, method, args):
        self.sent.append((method, tuple(args)))

    def on(self, event, handler):
        self.event_handlers[event] = handler

    def on_open(self, handler):
        self._open_handler = handler

    def on_close(self, handler):
        self._close_handler = handler

    def on_error(self, handler):
        self._error_handler = handler

    # Test helpers, not part of the Transport protocol.
    def simulate_open(self):
        self._open_handler()

    def simulate_close(self):
        self._close_handler()

    def emit(self, event, payload):
        self.event_handlers[event](payload)


def _hub():
    transports = []

    def factory(url, token):
        t = _FakeTransport(url, token)
        transports.append(t)
        return t

    health = HealthTracker(stale_after_seconds=10.0, clock=lambda: 0.0)
    hub = RealtimeHub("market", factory, "wss://example/hubs/market", health)
    return hub, transports, health


def test_subscribing_before_connect_is_sent_once_the_connection_opens():
    hub, transports, _health = _hub()
    hub.subscribe("SubscribeContractQuotes", "CON.F.US.MNQ.Z25")

    hub.connect(token="jwt")
    assert transports[0].sent == []  # not yet open

    transports[0].simulate_open()
    assert transports[0].sent == [("SubscribeContractQuotes", ("CON.F.US.MNQ.Z25",))]


def test_subscribing_while_already_connected_sends_immediately():
    hub, transports, _health = _hub()
    hub.connect(token="jwt")
    transports[0].simulate_open()

    hub.subscribe("SubscribeContractQuotes", "CON.F.US.MNQ.Z25")

    assert transports[0].sent == [("SubscribeContractQuotes", ("CON.F.US.MNQ.Z25",))]


def test_subscribing_to_the_same_thing_twice_never_sends_a_duplicate_rpc():
    hub, transports, _health = _hub()
    hub.connect(token="jwt")
    transports[0].simulate_open()

    hub.subscribe("SubscribeContractQuotes", "CON.F.US.MNQ.Z25")
    hub.subscribe("SubscribeContractQuotes", "CON.F.US.MNQ.Z25")

    assert transports[0].sent == [("SubscribeContractQuotes", ("CON.F.US.MNQ.Z25",))]


def test_reconnect_resends_every_pending_subscription_exactly_once():
    hub, transports, _health = _hub()
    hub.subscribe("SubscribeContractQuotes", "CON.F.US.MNQ.Z25")
    hub.subscribe("SubscribeContractTrades", "CON.F.US.MNQ.Z25")
    hub.connect(token="jwt")
    transports[0].simulate_open()
    assert len(transports[0].sent) == 2

    transports[0].simulate_close()
    transports[0].simulate_open()  # signalrcore's own automatic reconnect firing on_open again

    assert transports[0].sent.count(("SubscribeContractQuotes", ("CON.F.US.MNQ.Z25",))) == 2
    assert transports[0].sent.count(("SubscribeContractTrades", ("CON.F.US.MNQ.Z25",))) == 2
    assert len(transports[0].sent) == 4  # 2 subscriptions x (initial + after reconnect), no extras


def test_connect_updates_health_tracker_to_connected():
    hub, transports, health = _hub()
    hub.connect(token="jwt")
    assert health.status == ConnectionStatus.CONNECTING

    transports[0].simulate_open()
    assert health.status == ConnectionStatus.CONNECTED


def test_close_moves_health_tracker_to_reconnecting():
    hub, transports, health = _hub()
    hub.connect(token="jwt")
    transports[0].simulate_open()

    transports[0].simulate_close()

    assert health.status == ConnectionStatus.RECONNECTING


def test_incoming_event_is_delivered_to_the_registered_handler():
    hub, transports, _health = _hub()
    received = []
    hub.on("GatewayQuote", lambda payload: received.append(payload))

    hub.connect(token="jwt")
    transports[0].emit("GatewayQuote", {"contractId": "CON.F.US.MNQ.Z25", "lastPrice": 21000.25})

    assert received == [{"contractId": "CON.F.US.MNQ.Z25", "lastPrice": 21000.25}]


def test_note_market_data_received_clears_staleness():
    hub, _transports, health = _hub()
    health.mark_connected()
    health.mark_authenticated()

    hub.note_market_data_received()

    assert health.status == ConnectionStatus.CONNECTED


def test_disconnect_stops_the_transport_and_updates_health():
    hub, transports, health = _hub()
    hub.connect(token="jwt")
    transports[0].simulate_open()

    hub.disconnect()

    assert transports[0].stopped is True
    assert health.status == ConnectionStatus.RECONNECTING
