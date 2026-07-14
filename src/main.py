"""OpenRouter usage dash — runs on boot.

Powers the TFT, joins Wi-Fi, then polls OpenRouter every REFRESH_SECONDS and paints
today/week/month spend plus usage against the key's credit limit. Short, actionable
messages go to the screen; full error detail is printed to the serial REPL (`make repl`).

Deploy with `make deploy` (create src/config.py from config.example.py first).
"""
from machine import Pin, SPI
import time

import st7789py as st7789

import config
import net
import openrouter
import usage_view
import dash
import keyring
import buttons


def init_display():
    """Power the Reverse TFT rail (GPIO7) and return an initialized ST7789."""
    Pin(7, Pin.OUT, value=1)
    spi = SPI(1, baudrate=40_000_000, sck=Pin(36), mosi=Pin(35))
    return st7789.ST7789(
        spi,
        135,
        240,
        reset=Pin(41, Pin.OUT),
        dc=Pin(40, Pin.OUT),
        cs=Pin(42, Pin.OUT),
        backlight=Pin(45, Pin.OUT),
        rotation=1,  # 240x135 landscape
    )


def _require(name):
    """Return a non-empty, non-placeholder config value or raise ValueError(name)."""
    value = getattr(config, name, "")
    if not value or (isinstance(value, str) and value.startswith("your-")):
        raise ValueError(name)
    return value


def _clock():
    """HH:MM for the on-screen 'updated' stamp, shifted by config.TZ_OFFSET_HOURS."""
    offset = getattr(config, "TZ_OFFSET_HOURS", 0) * 3600
    t = time.localtime(time.time() + offset)
    return "%02d:%02d" % (t[3], t[4])


def _degrade(tft, last_view, note, page):
    """Keep the last good numbers on screen with a warning; if none yet, show the error."""
    if last_view is not None:
        dash.render(tft, last_view, _clock(), wifi_ok=False, note=note, page=page)
    else:
        dash.render_error(tft, "Can't update", note)


def _poll(tft, entry, page, last_view):
    """Refresh one key's usage. `entry` is a {"key","name"} ring entry, `page` its
    (current, total) position for the pager. Returns the newest view (or the prior one
    on error). On a key switch pass last_view=None so a failure can't show stale numbers
    from the previously selected key."""
    api_key = entry["key"]
    key_name = entry["name"]
    try:
        key = openrouter.fetch_key(api_key)
        credits = None
        try:
            credits = openrouter.fetch_credits(api_key)
        except Exception as exc:  # /credits is a bonus; /key alone is enough to render
            print("credits fetch failed:", exc)
        view = usage_view.build_view(key, credits, key_name)
        dash.render(tft, view, _clock(), wifi_ok=net.isconnected(), page=page)
        return view
    except openrouter.ApiError as exc:
        print("API error:", exc.status)
        note = "Check API key" if exc.status in (401, 403) else "API error"
        _degrade(tft, last_view, note, page)
        return last_view
    except OSError as exc:
        print("Network error:", exc)
        _degrade(tft, last_view, "API unreachable", page)
        return last_view


def main():
    tft = init_display()

    try:
        ssid = _require("WIFI_SSID")
        password = _require("WIFI_PASSWORD")
    except ValueError as exc:
        print("Config error: set", exc, "in src/config.py")
        dash.render_error(tft, "Setup needed", "Edit config.py")
        return

    # One or many keys, all from OPENROUTER_KEYS; page through them with the buttons.
    ring = keyring.normalize_keys(getattr(config, "OPENROUTER_KEYS", None))
    try:
        ring = keyring.KeyRing(ring)
    except ValueError:
        print("Config error: set OPENROUTER_KEYS in src/config.py")
        dash.render_error(tft, "Setup needed", "Add API key")
        return

    dash.render_error(tft, "Connecting", "Wi-Fi...")
    try:
        net.connect(ssid, password)
    except OSError as exc:
        print("Wi-Fi failed:", exc)
        dash.render_error(tft, "No Wi-Fi", "Check config.py")
        return
    net.sync_time()  # best-effort; the clock is cosmetic

    refresh = getattr(config, "REFRESH_SECONDS", 60)
    next_btn = buttons.Button(1)  # D1 -> next key
    prev_btn = buttons.Button(2)  # D2 -> previous key

    entry = ring.current()
    last_view = _poll(tft, entry, ring.position(), None)
    deadline = time.ticks_add(time.ticks_ms(), refresh * 1000)
    while True:
        # Page through keys on a button press, otherwise refresh when the interval
        # elapses. Polling buttons every 50 ms keeps toggling responsive without
        # blocking on a long sleep between refreshes.
        moved = False
        if ring.has_multiple:
            if next_btn.fell():
                entry = ring.next()
                moved = True
            elif prev_btn.fell():
                entry = ring.prev()
                moved = True

        if moved:
            # Acknowledge the press before the (blocking) fetch, so the switch shows
            # instantly instead of leaving the prior key's dash up during the fetch.
            dash.render_loading(tft, entry["name"], ring.position())
            last_view = _poll(tft, entry, ring.position(), None)
            deadline = time.ticks_add(time.ticks_ms(), refresh * 1000)
        elif time.ticks_diff(deadline, time.ticks_ms()) <= 0:
            last_view = _poll(tft, entry, ring.position(), last_view)
            deadline = time.ticks_add(time.ticks_ms(), refresh * 1000)

        time.sleep_ms(50)


main()
