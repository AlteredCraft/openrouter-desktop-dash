# micro-py-sandbox — MicroPython on the Adafruit ESP32-S3 Reverse TFT Feather (5691)
#
# Everything in ./src is what lives ON the board. These targets drive it with mpremote.
# If the serial port changes, override it per-invocation:  make deploy PORT=/dev/cu.usbmodemXXXX
# Find the port with:  ls /dev/cu.usbmodem*

PORT ?= /dev/cu.usbmodem1101
MP   := mpremote connect $(PORT)

# Files copied to the board's flash root by `make deploy`. Add new device files here.
DEVICE_FILES := src/st7789py.py src/vga2_bold_16x16.py src/main.py

.PHONY: help repl run mount deploy ls reset wipe

help:  ## show this help
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  make %-8s %s\n", $$1, $$2}'

repl:  ## open the REPL (Ctrl-C breaks a running program, Ctrl-] exits)
	$(MP) repl

run:  ## run src/main.py on the board once, without installing it (needs libs already on board)
	$(MP) run src/main.py

mount:  ## mount ./src as the board filesystem + REPL — live edit, no copy, then `import main`
	$(MP) mount src repl

deploy:  ## copy all device files to the board's flash and reset
	$(MP) cp $(DEVICE_FILES) :
	$(MP) reset

ls:  ## list files currently on the board
	$(MP) ls

reset:  ## reset the board (re-runs main.py)
	$(MP) reset

wipe:  ## remove main.py from the board so it stops auto-running on boot
	$(MP) rm :main.py
