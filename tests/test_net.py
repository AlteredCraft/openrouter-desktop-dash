"""Host-side unit tests for the Wi-Fi connect logic (run with `make test`).

net.py imports the MicroPython-only `network` module, so we stub it before import and
drive the fake WLAN through success/failure scenarios to verify connect_any tries
networks in order, stops at the first that links up, and tears down failed attempts.
"""
import sys
import types

import pytest

# --- stub the MicroPython `network` module so net.py imports on the host --------------
_network = types.ModuleType("network")
_network.STA_IF = 1


class FakeWLAN:
    # `scenario` is a per-attempt list of bools: True = the link comes up immediately.
    scenario = []
    _history = []
    _connected = False
    _last_ssid = None

    def __init__(self, iface):
        pass

    def active(self, val=None):
        FakeWLAN._history.append(("active", val))
        return True

    def isconnected(self):
        return FakeWLAN._connected

    def connect(self, ssid, password):
        FakeWLAN._history.append(("connect", ssid))
        FakeWLAN._last_ssid = ssid
        # Consume the next scenario step; default to "never connects" if exhausted.
        connects = FakeWLAN.scenario.pop(0) if FakeWLAN.scenario else False
        FakeWLAN._connected = bool(connects)

    def disconnect(self):
        FakeWLAN._history.append(("disconnect",))
        FakeWLAN._connected = False


_network.WLAN = FakeWLAN
sys.modules.setdefault("network", _network)

# Stub the MicroPython-only `time` helpers (ticks_*) that net.py relies on.
import time as _realtime  # noqa: E402

_fake_time = types.SimpleNamespace(
    ticks_ms=lambda: int(_realtime.monotonic() * 1000),
    ticks_add=lambda a, b: a + b,
    ticks_diff=lambda a, b: a - b,
    sleep_ms=lambda ms: None,
)
sys.modules["time"] = _fake_time

import net  # noqa: E402


@pytest.fixture(autouse=True)
def reset():
    FakeWLAN.scenario = []
    FakeWLAN._history = []
    FakeWLAN._connected = False
    FakeWLAN._last_ssid = None
    yield


def _connects():
    return [c for c in FakeWLAN._history if c[0] == "connect"]


def test_connect_any_returns_first_success():
    FakeWLAN.scenario = [True]
    wlan, ssid = net.connect_any([{"ssid": "home", "password": "pw"}], timeout_s=1)
    assert ssid == "home"
    assert _connects() == [("connect", "home")]


def test_connect_any_tries_networks_in_order():
    FakeWLAN.scenario = [False, False]
    with pytest.raises(OSError):
        net.connect_any([{"ssid": "a"}, {"ssid": "b"}], timeout_s=0)
    assert _connects() == [("connect", "a"), ("connect", "b")]


def test_connect_any_stops_at_first_working_network():
    FakeWLAN.scenario = [False, True]
    wlan, ssid = net.connect_any([{"ssid": "a"}, {"ssid": "b"}], timeout_s=0)
    assert ssid == "b"
    assert _connects() == [("connect", "a"), ("connect", "b")]


def test_connect_any_tears_down_failed_attempt():
    FakeWLAN.scenario = [False, True]
    net.connect_any([{"ssid": "a"}, {"ssid": "b"}], timeout_s=0)
    # The first (failed) attempt must be torn down before the second begins.
    assert ("disconnect",) in FakeWLAN._history


def test_connect_any_raises_on_empty_list():
    with pytest.raises(OSError):
        net.connect_any([], timeout_s=0)


def test_connect_any_reports_each_attempt_via_on_try():
    FakeWLAN.scenario = [False, True]
    calls = []
    net.connect_any(
        [{"ssid": "a"}, {"ssid": "b"}],
        timeout_s=0,
        on_try=lambda s, i, n: calls.append((s, i, n)),
    )
    assert calls == [("a", 1, 2), ("b", 2, 2)]


def test_connect_any_on_try_sees_total_count():
    FakeWLAN.scenario = [False, False, False]
    seen = []
    with pytest.raises(OSError):
        net.connect_any(
            [{"ssid": "a"}, {"ssid": "b"}, {"ssid": "c"}],
            timeout_s=0,
            on_try=lambda s, i, n: seen.append(n),
        )
    assert seen == [3, 3, 3]


def test_connect_any_forwards_timeout_s_to_connect():
    captured = {}

    def fake_connect(ssid, password, timeout_s=20):
        captured["timeout_s"] = timeout_s
        raise OSError("no link")

    original = net.connect
    net.connect = fake_connect
    try:
        with pytest.raises(OSError):
            net.connect_any(
                [{"ssid": "a"}], timeout_s=7, on_try=lambda *a: None
            )
    finally:
        net.connect = original
    assert captured["timeout_s"] == 7

