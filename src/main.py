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


def _degrade_account(tft, last_view, note):
    """Account-screen counterpart of _degrade: keep the last good rollup with a warning."""
    if last_view is not None:
        dash.render_account(tft, last_view, _clock(), wifi_ok=False, note=note)
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


def _poll_account(tft, ring, last_view):
    """Refresh the D0 account overview: fetch every configured key, sum their usage, and
    read the account balance once from /credits (it's account-wide, same for any key).

    A single key failing is tolerated — its usage is dropped from the rollup. Only when
    *nothing* comes back do we degrade, distinguishing a bad key (401/403) from an outage.
    On a fresh toggle pass last_view=None so a failure can't show a stale account screen.
    """
    keys_data = []
    auth_err = False
    net_err = False
    for entry in ring.entries():
        try:
            keys_data.append(openrouter.fetch_key(entry["key"]))
        except openrouter.ApiError as exc:
            print("account key error:", exc.status)
            if exc.status in (401, 403):
                auth_err = True
        except OSError as exc:
            print("account key network error:", exc)
            net_err = True

    credits = None
    try:
        credits = openrouter.fetch_credits(ring.current()["key"])
    except openrouter.ApiError as exc:
        print("account credits error:", exc.status)
        if exc.status in (401, 403):
            auth_err = True
    except OSError as exc:
        print("account credits network error:", exc)
        net_err = True

    if not keys_data and credits is None:
        note = "Check API key" if auth_err and not net_err else "API unreachable"
        _degrade_account(tft, last_view, note)
        return last_view

    view = usage_view.build_account_view(keys_data, credits, len(ring))
    dash.render_account(tft, view, _clock(), wifi_ok=net.isconnected())
    return view


def main():
    tft = init_display()

    networks = keyring.normalize_wifi(getattr(config, "WIFI_NETWORKS", None))
    if not networks:
        # Legacy fallback: a single WIFI_SSID / WIFI_PASSWORD pair.
        try:
            ssid = _require("WIFI_SSID")
            password = _require("WIFI_PASSWORD")
        except ValueError as exc:
            print("Config error: set WIFI_NETWORKS or", exc, "in src/config.py")
            dash.render_error(tft, "Setup needed", "Edit config.py")
            return
        networks = [{"ssid": ssid, "password": password}]

    # One or many keys, all from OPENROUTER_KEYS; page through them with the buttons.
    ring = keyring.normalize_keys(getattr(config, "OPENROUTER_KEYS", None))
    try:
        ring = keyring.KeyRing(ring)
    except ValueError:
        print("Config error: set OPENROUTER_KEYS in src/config.py")
        dash.render_error(tft, "Setup needed", "Add API key")
        return

    def _on_try(ssid, index, total):
        dash.render_error(
            tft, "Connecting", "Trying %s" % ssid, "%d nets to try" % total
        )
        # The ESP32 caches Wi-Fi creds and auto-connects the moment the interface comes
        # up, so connect() can return instantly — hold the "Trying <ssid>" frame long
        # enough to read it instead of flashing straight to the dash.
        time.sleep_ms(400)

    dash.render_error(tft, "Connecting", "Wi-Fi...")
    wifi_timeout = getattr(config, "WIFI_TIMEOUT_SECONDS", 20)
    try:
        wlan, ssid = net.connect_any(
            networks, timeout_s=wifi_timeout, on_try=_on_try
        )
    except OSError as exc:
        print("Wi-Fi failed for all networks:", exc)
        dash.render_error(
            tft, "No Wi-Fi", "tried %d" % len(networks), "Check config.py"
        )
        return
    net.sync_time()  # best-effort; the clock is cosmetic

    refresh = getattr(config, "REFRESH_SECONDS", 60)
    next_btn = buttons.Button(1)  # D1 -> next key
    prev_btn = buttons.Button(2)  # D2 -> previous key
    acct_btn = buttons.Button(0, active_low=True)  # D0 (BOOT) -> toggle account/key view

    show_account = False  # False = per-key dash (D1/D2 page keys); True = account rollup
    entry = ring.current()
    last_view = _poll(tft, entry, ring.position(), None)
    deadline = time.ticks_add(time.ticks_ms(), refresh * 1000)
    while True:
        # D0 flips between the per-key dash and the account overview; D1/D2 page keys
        # (only meaningful in the per-key view). Otherwise refresh when the interval
        # elapses. Polling every 50 ms keeps toggling responsive without blocking on a
        # long sleep between refreshes.
        toggled = acct_btn.fell()
        if toggled:
            show_account = not show_account

        moved = False
        if not show_account and ring.has_multiple:
            if next_btn.fell():
                entry = ring.next()
                moved = True
            elif prev_btn.fell():
                entry = ring.prev()
                moved = True

        if toggled or moved:
            # Acknowledge the press with the loading emblem before the (blocking) fetch,
            # so the switch shows instantly instead of leaving the prior screen up. Pass
            # last_view=None so a failed fetch can't show numbers from the other view.
            if show_account:
                dash.render_loading(tft, "Account")
                last_view = _poll_account(tft, ring, None)
            else:
                dash.render_loading(tft, entry["name"], ring.position())
                last_view = _poll(tft, entry, ring.position(), None)
            deadline = time.ticks_add(time.ticks_ms(), refresh * 1000)
        elif time.ticks_diff(deadline, time.ticks_ms()) <= 0:
            if show_account:
                last_view = _poll_account(tft, ring, last_view)
            else:
                last_view = _poll(tft, entry, ring.position(), last_view)
            deadline = time.ticks_add(time.ticks_ms(), refresh * 1000)

        time.sleep_ms(50)


main()
