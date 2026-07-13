# micro-py-sandbox

An **OpenRouter usage dashboard** on the **Adafruit ESP32-S3 Reverse TFT Feather**
(Adafruit #5691). It joins Wi-Fi and shows your OpenRouter spend — today / this week /
this month — plus spend against the key's credit limit with a gauge, refreshing on its own.
This repo is the *code*; the roadmap for the wider "cute desktop buddy" appliance lives in
the Obsidian vault.

It doubles as a beginner-friendly MicroPython playground. If you know Python but are new to
microcontrollers, start with **[Mental model](#mental-model)**, then **[Setup](#setup)**.

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
micro-py-sandbox/
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
  .vscode/settings.json      # points the editor at the venv + src/ for autocomplete
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

### 4. Set up the editor + deploy

```bash
uv sync                                    # installs host dev tools (stubs + pytest) into .venv
make test                                  # sanity-check the pure logic on your laptop
```

In VS Code: `Python: Select Interpreter` -> `./.venv/bin/python` (gives you autocomplete).
VS Code will also offer this repo's recommended extensions (Python, Ruff, TOML) from
`.vscode/extensions.json`; accept them for linting and formatting.

Then push everything to the board and watch it run:

```bash
make deploy                                # copies src/*.py (incl. config.py) and resets
```

On boot it shows **Connecting… Wi-Fi**, then your usage dash. If it shows **Setup needed**
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

> **Prefer buttons over the terminal?** The **MicroPico** extension (`paulober.pico-w-go`) adds
> in-editor Run / Upload / REPL for MicroPython and works with this ESP32-S3 board despite the
> "Pico" name. It is an all-in-one *alternative* to the `mpremote` + `make` workflow above, so
> pick one or the other: MicroPico ships its own stubs and file transfer, which double up with
> this repo's `.venv` stubs if you run both. That is why it is left out of
> `.vscode/extensions.json`.

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
