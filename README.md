# micro-py-sandbox

A beginner-friendly MicroPython playground for the **Adafruit ESP32-S3 Reverse TFT Feather**
(Adafruit #5691). It boots up and paints "Hello, buddy!" on the little TFT screen, and gives
you a clean workflow to grow from there. This repo is the *code*; the roadmap for the wider
"cute desktop buddy" appliance lives in the Obsidian vault.

If you know Python but are new to microcontrollers, start with **[Mental model](#mental-model)**,
then **[Setup](#setup)**.

## What's here

```
micro-py-sandbox/
  src/                       # <- everything here is copied ONTO the board
    main.py                  #    auto-runs on boot: TFT "Hello, buddy!"
    st7789py.py              #    ST7789 display driver (vendored, MIT)
    vga2_bold_16x16.py       #    bitmap font (vendored, MIT)
    config.example.py        #    secrets template; copy to config.py in Phase 3
  .vscode/settings.json      # points the editor at the venv + src/ for autocomplete
  Makefile                   # the everyday workflow (run `make help`)
  pyproject.toml + .venv/    # HOST-only dev tools (type stubs); never touch the board
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

### 3. Set up the editor + run the demo

```bash
uv sync                                    # installs the type stubs into .venv
```

In VS Code: `Python: Select Interpreter` -> `./.venv/bin/python` (gives you autocomplete).
VS Code will also offer this repo's recommended extensions (Python, Ruff, TOML) from
`.vscode/extensions.json`; accept them for linting and formatting.

Then push the code to the board and watch it run:

```bash
make deploy                                # copies src/ files to the board and resets
```

The screen should show **Hello, buddy!** in white on blue. If it does not, see
[Troubleshooting](#troubleshooting).

## Everyday workflow

All targets take an optional `PORT=` override (default `/dev/cu.usbmodem1101`):

```bash
make deploy    # copy src/* to the board's flash and reset (do this once for the libs)
make repl      # open the REPL (Ctrl-C stops a program, Ctrl-] exits)
make mount     # mount ./src as the board's filesystem + REPL: live edit, no copy, then `import main`
make run       # run src/main.py once without installing it (libs must already be on the board)
make ls        # list the files currently on the board
make wipe      # delete main.py from the board so it stops auto-running on boot
make help      # list every target
```

**Typical loop:** `make deploy` once to put the driver + font on the board, then iterate on
`src/main.py` with `make run` (quick one-shot) or `make mount` (edit locally, `import main`,
nothing copied).

## Troubleshooting

| Symptom | Fix |
|---|---|
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
- Type stubs: [Josverl/micropython-stubs](https://github.com/Josverl/micropython-stubs)
