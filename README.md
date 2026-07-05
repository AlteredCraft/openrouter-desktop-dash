# micro-py-sandbox

MicroPython playground for the **Adafruit ESP32-S3 Reverse TFT Feather** (Adafruit #5691) —
the brain of the cute desktop buddy project. This repo holds the code that runs *on the
board*, plus a host-side dev environment (type stubs + `mpremote` workflow).

## Layout

```
micro-py-sandbox/
  src/                     # <- everything here lives ON the board
    main.py                #    auto-runs on boot: TFT "Hello, buddy!"
    st7789py.py            #    vendored ST7789 display driver (russhughes/st7789py_mpy)
    vga2_bold_16x16.py     #    vendored bitmap font
  .vscode/settings.json    # points Pylance at the venv + src/ for IntelliSense
  Makefile                 # mpremote workflow (see `make help`)
  pyproject.toml           # host dev deps (MicroPython stubs) — NOT installed on the board
```

`src/` mirrors the board's flash. The `pyproject.toml` / `.venv` are host-only: they exist so
your editor can autocomplete and type-check `machine`, `network`, `neopixel`, etc. via
`micropython-esp32-stubs`. None of that gets copied to the device.

## Prerequisites

- MicroPython firmware already flashed (ESP32_GENERIC_S3, **Standard** variant).
- `uv`, `mpremote`, and `make` on your PATH.
- Host dev env: `uv sync` (installs the stubs into `.venv`).

In VS Code, select the `.venv` interpreter (`Python: Select Interpreter` -> `./.venv/bin/python`).

## Workflow

Find the board's port, then use the Makefile (override `PORT=` if it differs from the default):

```bash
ls /dev/cu.usbmodem*          # e.g. /dev/cu.usbmodem1101

make deploy                   # copy src/* to the board's flash and reset (do this once for the libs)
make repl                     # REPL: Ctrl-C breaks a running program, Ctrl-] exits
make mount                    # mount ./src as the board FS + REPL — live edit, no copy
make run                      # run src/main.py once without installing (libs must already be on board)
make ls                       # list files on the board
make wipe                     # delete main.py from the board so it stops auto-running
make help                     # list all targets
```

Typical loop: `make deploy` once to put the driver + font on the board, then iterate on
`src/main.py` with `make run` (quick) or `make mount` (edit-and-`import main`, nothing copied).

## Board pin reference (5691)

| Signal | GPIO | Note |
|---|---|---|
| SPI SCK / MOSI | 36 / 35 | display bus |
| TFT CS / DC / RESET | 42 / 40 / 41 | |
| TFT backlight | 45 | HIGH = on |
| TFT + I2C power | 7 | **must be HIGH to power the display** |
| NeoPixel data / power | 33 / 21 | power HIGH to enable |
| Buttons D0 / D1 / D2 | 0 / 1 / 2 | D0 active-low; D1/D2 active-high |

Display: 240x135 ST7789, offsets 40/53 (handled by the driver at `rotation=1`).

## Credits

- Display driver + fonts: [russhughes/st7789py_mpy](https://github.com/russhughes/st7789py_mpy)
- Stubs: [Josverl/micropython-stubs](https://github.com/Josverl/micropython-stubs)
