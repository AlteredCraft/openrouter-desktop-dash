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
