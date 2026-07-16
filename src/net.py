"""Wi-Fi + clock helpers (hardware-only I/O; runs on the board).

Kept deliberately thin — connection/timeout mechanics live here so main.py can stay
readable and openrouter.py can assume the network is already up.
"""
import network
import time


def connect(ssid, password, timeout_s=20):
    """Bring up station mode and connect to Wi-Fi.

    Returns the WLAN object on success. Raises OSError on timeout so the caller can
    show a short 'No WiFi' screen while logging the detail to the serial REPL.
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(ssid, password)
        deadline = time.ticks_add(time.ticks_ms(), timeout_s * 1000)
        while not wlan.isconnected():
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                raise OSError("wifi connect timeout")
            time.sleep_ms(200)
    return wlan


def isconnected():
    """True if the station interface currently has a Wi-Fi link."""
    return network.WLAN(network.STA_IF).isconnected()


def connect_any(networks, timeout_s=20, on_try=None):
    """Try each {ssid,password} in `networks` in order until one connects.

    Returns (wlan, ssid) for the first network that comes up. If every network
    fails (or none were given), raises OSError naming how many were tried, so the
    caller can show a short 'No WiFi' screen. Each attempt is independent: a failed
    connect is torn down (disconnect + deactivate) before the next begins, so a
    half-open link can't poison the following try.

    `on_try(ssid, index, total)`, if given, is called right before each attempt so
    the caller can paint a live "Trying <ssid> (n/total)" screen.
    """
    total = len(networks)
    tried = 0
    last_err = None
    for net in networks:
        ssid = net["ssid"]
        password = net.get("password", "")
        tried += 1
        if on_try:
            on_try(ssid, tried, total)
        try:
            wlan = connect(ssid, password, timeout_s=timeout_s)
            return wlan, ssid
        except OSError as exc:
            last_err = exc
            print("Wi-Fi failed for", repr(ssid) + ":", exc)
            # Tear down the half-open link so the next attempt starts clean.
            try:
                wlan = network.WLAN(network.STA_IF)
                wlan.disconnect()
                wlan.active(False)
            except Exception:
                pass
    raise OSError("wifi connect failed for all %d networks" % tried)


def sync_time():
    """Best-effort NTP sync (sets the RTC to UTC). Returns True on success.

    Non-fatal: if it fails, the dash still works — only the on-screen clock is off.
    """
    try:
        import ntptime

        ntptime.settime()
        return True
    except Exception:
        return False
