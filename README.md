# openrouter-desktop-dash

A complete, worked **MicroPython example** for the **Adafruit ESP32-S3 Reverse TFT Feather**
(Adafruit #5691): a tiny always-on desktop appliance that shows your **OpenRouter API spend**.
Plug it in and it joins Wi-Fi, calls a live cloud API over HTTPS, and paints today / this week /
this month of usage — plus spend against the key's credit limit — on the built-in color screen,
refreshing on its own.

It's meant to be **read and forked.** The OpenRouter dashboard is just the payload; underneath
it's a clean, end-to-end template for any "connect to an API and show it on a screen" gadget on
the ESP32-S3. Swap the `openrouter.py` client and the `dash.py` layout and you have a weather
frame, a CI monitor, a crypto ticker, a home-automation panel — same skeleton.

New to microcontrollers but know Python? The **[Mental model](#mental-model)** section is written
for you.

## What it demonstrates

The reusable ESP32-S3 + MicroPython patterns this example wires together:

- **Wi-Fi station mode** with a connect timeout and status reporting (`net.py`).
- **Authenticated HTTPS/TLS** to a real cloud API from the board, via a vendored minimal
  `requests` (`urequests.py` + `openrouter.py`) — the part that trips most ESP32 projects up.
- **JSON parsing** of the API response into a typed view-model.
- **SPI color-TFT rendering** — text, rules, a status dot, and a green→orange→red progress bar
  on the ST7789 display (`dash.py`).
- **NTP time sync** for an on-screen clock (`net.py`).
- **Testable architecture:** the parsing/formatting logic (`usage_view.py`) imports nothing
  hardware-specific, so it runs and is **unit-tested on your laptop** (`make test`, 31 cases) —
  no board required.
- **Fail-fast config + graceful degradation:** missing settings show *Setup needed*; a failed
  refresh keeps the last-good numbers on screen with a short reason instead of crashing.
- **A frictionless dev loop:** an `mpremote`-driven `Makefile` that auto-detects the serial
  port, confirms before touching the board, and gives you `deploy` / `repl` / `mount` / `run`.

## What it shows

A single screen, refreshed every `REFRESH_SECONDS` (default 60):

- **Today / Week / Month** — spend in USD-equivalent credits (`usage_daily/weekly/monthly`).
- **Used** — spend against the key's credit limit (e.g. `$0.35` of a `$20` cap, from `limit` /
  `limit_remaining`), with a color bar that fills **green** (< 50% used) → **orange** (50–75%) →
  **red** (≥ 75%). Keys with no limit fall back to your account credit balance (`/credits`).
- A header showing your key's name (from `KEY_NAME` in `config.py`, truncated to `10` chars +
  `...`; falls back to `OpenRouter` if blank — see [Header name](#header-name)), a Wi-Fi status
  dot, and a last-updated clock. If a refresh fails, the last good numbers stay on screen with a
  short reason (`Check API key`, `API unreachable`).

It reads OpenRouter's `GET /api/v1/key` and `GET /api/v1/credits` using a normal (read-only)
inference API key — **not** a management/provisioning key. See
**[Configure Wi-Fi + OpenRouter](#openrouter-setup)**.

## What's here

```
openrouter-desktop-dash/
  src/                       # <- everything here is copied ONTO the board
    main.py                  #    auto-runs on boot: connect Wi-Fi, poll, render the dash
    dash.py                  #    draws the view-model on the TFT
    usage_view.py            #    PURE logic: API payloads -> view-model (host-tested)
    openrouter.py            #    OpenRouter API client (GET /key, /credits)
    net.py                   #    Wi-Fi connect + NTP time sync
    urequests.py             #    minimal HTTP/HTTPS client (vendored, MIT)
    st7789py.py              #    ST7789 display driver (vendored, MIT)
    vga2_bold_16x16.py       #    bitmap font (vendored, MIT)
    config.example.py        #    settings + secrets template; copy to config.py
  tests/                     # HOST-only pytest for the pure logic (run: make test)
  Makefile                   # the everyday workflow (run `make help`)
  pyproject.toml + .venv/    # HOST-only dev tools (stubs + pytest); never touch the board
```

The key idea: **`src/` mirrors the board's flash.** Everything else (`pyproject.toml`, `.venv/`,
this README) stays on your laptop. The `.venv` exists only so your editor can autocomplete
`machine`, `network`, `neopixel`, etc. via `micropython-esp32-stubs`. None of it runs on the device.

## Mental model

If your background is desktop Python, these are the differences that trip people up:

- **The board has its own filesystem** (in flash). Your code runs *there*, not on your laptop.
  You edit files here, then *copy* them to the board. `.venv` and `pip`/`uv` packages do **not** go on the board.
- **`main.py` runs automatically** on every power-up or reset (after an optional `boot.py`).
  Name your always-run program `main.py`.
- **The REPL is a live Python prompt on the board**, reached over USB serial. In it:
  `Ctrl-C` interrupts a running program, `Ctrl-D` does a *soft reset* (re-runs `boot.py`/`main.py`
  without cutting power), and `Ctrl-]` exits `mpremote`.
- **Two kinds of reset:** *soft* (`Ctrl-D`, re-runs your code) vs *hard* (the RESET button or unplugging).
- **`import` searches the board's filesystem**, not your project folder. That is why the driver
  and font have to be copied to the board before `main.py` can import them.

## Setup

### 1. Install the host tools (one time)

Uses [uv](https://docs.astral.sh/uv/). `esptool` flashes firmware; `mpremote` talks to the board:

```bash
uv tool install esptool
uv tool install mpremote
```

### 2. Flash MicroPython (one time)

1. Download the firmware from <https://micropython.org/download/ESP32_GENERIC_S3/> — the latest
   **Standard** `.bin`. Do **not** grab the "Octal-SPIRAM" build; this board has quad PSRAM and
   the octal build will not boot.
2. Put the board in bootloader mode: **hold `D0`/BOOT, tap `RESET`, release `D0`** (or double-tap `RESET`).
3. Find the serial port and flash. Note the write address is **`0`** for the ESP32-S3:

   ```bash
   ls /dev/cu.usbmodem*                    # e.g. /dev/cu.usbmodem1101
   esptool.py --chip esp32s3 --port /dev/cu.usbmodem1101 erase_flash
   esptool.py --chip esp32s3 --port /dev/cu.usbmodem1101 --baud 460800 \
       write_flash 0 ESP32_GENERIC_S3-*.bin
   ```
4. Press `RESET`. You now have a MicroPython board.

### 3. Configure Wi-Fi + OpenRouter  <a id="openrouter-setup"></a>

Copy the template to a real config file — `config.py` is gitignored, so your secrets stay local:

```bash
cp src/config.example.py src/config.py
```

Then edit `src/config.py`:

```python
WIFI_SSID = "your-wifi-name"          # 2.4 GHz only — the ESP32-S3 has no 5 GHz radio
WIFI_PASSWORD = "your-wifi-password"
OPENROUTER_API_KEY = "sk-or-v1-..."   # a normal inference key from
                                      # https://openrouter.ai/settings/keys
KEY_NAME = "warp"                     # optional header label (see "Header name" below)
REFRESH_SECONDS = 60                  # optional
TZ_OFFSET_HOURS = 0                   # optional; e.g. -7 for PDT (NTP syncs UTC)
```

Any OpenRouter inference key works — the dash only *reads* usage. Don't use a
management/provisioning key here: it isn't needed, and it can create/delete keys.

#### Header name

`GET /api/v1/key` only returns the key *string* (its `label`, e.g. `sk-or-v1-…`), **not** the
human name you gave the key — that lives in a `name` field exposed only by the Management API,
which needs a provisioning key we intentionally keep off the device. So set `KEY_NAME` in
`config.py` to show a friendly header (e.g. `"warp"`); leave it blank to show `OpenRouter`.

### 4. Install deps + deploy

```bash
uv sync                                    # installs host dev tools (stubs + pytest) into .venv
make test                                  # sanity-check the pure logic on your laptop
make deploy                                # copies src/*.py (incl. config.py) to the board and resets
```

(Optional: point your editor's Python interpreter at `./.venv/bin/python` so `machine`,
`network`, etc. autocomplete from the stubs.)

On boot the board shows **Connecting… Wi-Fi**, then your usage dash. If it shows **Setup needed**
or **No Wi-Fi**, re-check `src/config.py`; for anything else see
[Troubleshooting](#troubleshooting).

## Everyday workflow

Targets auto-detect the board's serial port (the first `/dev/cu.usbmodem*`); pass an
optional `PORT=` override if you have several boards attached:

```bash
make deploy    # copy src/*.py (+ config.py) to the board's flash and reset
make repl      # open the REPL (Ctrl-C stops a program, Ctrl-] exits)
make mount     # mount ./src as the board's filesystem + REPL: live edit, no copy, then `import main`
make run       # run src/main.py once without installing it (libs must already be on the board)
make ls        # list the files currently on the board
make wipe      # delete main.py from the board so it stops auto-running on boot
make test      # run host-side unit tests for the pure logic (no board needed)
make help      # list every target
```

`deploy`, `wipe`, and `reset` show the detected port and ask for confirmation before
touching the board.

**Typical loop:** `make deploy` once to install all the modules (+ `config.py`) on the board,
then iterate with `make run` (quick one-shot) or `make mount` (edit locally, `import main`,
nothing copied). Use `make test` to check the pure logic on your laptop without the board.

## Make it your own

The skeleton is API-agnostic. To point it at something else:

1. Replace `openrouter.py` with a client for your API (keep it thin: fetch → return a dict).
2. Reshape `usage_view.build_view()` to map that payload into a view-model, and update the
   tests in `tests/` alongside it (they need no hardware).
3. Adjust the `dash.py` layout to render your fields.

`main.py`, `net.py`, the Makefile, and the config/secret handling stay as-is.

## Troubleshooting

| Symptom | Fix |
|---|---|
| **`Setup needed` on screen** | `src/config.py` is missing or still has placeholder values. Fill it in (step 3) and `make deploy`. |
| **`No Wi-Fi` on screen** | Wrong SSID/password, or a 5 GHz network — the ESP32-S3 is 2.4 GHz only. Fix `src/config.py` and redeploy. |
| **`Check API key` on screen** | OpenRouter rejected the key (401/403). Verify `OPENROUTER_API_KEY` at [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys). |
| **`API unreachable` on screen** | Transient network/OpenRouter hiccup; the dash keeps the last numbers and retries next cycle. Persistent? Check the REPL log (`make repl`). |
| **Blank screen** | GPIO7 (power) and GPIO45 (backlight) must both be HIGH; `main.py` sets them. Also confirm your USB-C cable carries *data*, not charge-only. |
| **Colors swapped** (red/blue) | Add `color_order=st7789.RGB` to the `ST7789(...)` call in `main.py`. |
| **`ImportError: no module named 'st7789py'`** | The libs are not on the board yet. Run `make deploy` (or `make mount`). |
| **Port busy / `could not enter raw repl`** | Only one thing can hold the serial port. Close Thonny or any other `mpremote`, then retry. |
| **No `/dev/cu.usbmodem*`** | Try a different USB-C cable (many are charge-only). For flashing, enter bootloader: hold `D0`, tap `RESET`. |
| **Board acting corrupted** | Re-flash firmware from scratch (`erase_flash` then `write_flash`). |

## Board pin reference (5691)

| Signal | GPIO | Note |
|---|---|---|
| SPI SCK / MOSI | 36 / 35 | display bus |
| TFT CS / DC / RESET | 42 / 40 / 41 | |
| TFT backlight | 45 | HIGH = on |
| TFT + I2C power | 7 | **must be HIGH to power the display** |
| NeoPixel data / power | 33 / 21 | power HIGH to enable |
| Buttons D0 / D1 / D2 | 0 / 1 / 2 | D0 is active-low; D1/D2 active-high |

Display: 240x135 ST7789, offsets 40/53, handled by the driver at `rotation=1`.

## Credits

Vendored under their MIT licenses (headers kept intact in each file):

- Display driver + fonts: [russhughes/st7789py_mpy](https://github.com/russhughes/st7789py_mpy)
- HTTP client (`urequests.py`): [micropython/micropython-lib](https://github.com/micropython/micropython-lib)
- Type stubs: [Josverl/micropython-stubs](https://github.com/Josverl/micropython-stubs)
