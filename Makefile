# openrouter-desktop-dash — MicroPython on the Adafruit ESP32-S3 Reverse TFT Feather (5691)
#
# Everything in ./src is what lives ON the board. These targets drive it with mpremote.
# PORT auto-detects the first /dev/cu.usbmodem* device (the macOS suffix shifts between
# reboots/ports, e.g. 101 vs 1101). Override it if you have several boards attached:
#   make deploy PORT=/dev/cu.usbmodemXXXX      # find candidates with: ls /dev/cu.usbmodem*

PORT ?= $(shell ls /dev/cu.usbmodem* 2>/dev/null | head -n1)
MP   := mpremote connect $(PORT)

# Files copied to the board's flash root by `make deploy`. Add new device files here.
# config.py holds your secrets and is copied separately (it's gitignored and optional).
DEVICE_FILES := src/st7789py.py src/vga2_bold_16x16.py src/urequests.py \
                src/net.py src/openrouter.py src/usage_view.py src/keyring.py \
                src/buttons.py src/dash.py src/main.py

.PHONY: help repl run mount deploy ls reset wipe confirm-port test

help:  ## show this help
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  make %-8s %s\n", $$1, $$2}'

# Prerequisite for board-changing targets: fail fast if no board is attached,
# otherwise show the detected port and require a y/N confirmation before touching it.
confirm-port:
	@test -n "$(PORT)" || { echo "No board found at /dev/cu.usbmodem* — plug one in, or pass PORT=/dev/cu.usbmodemXXXX"; exit 1; }
	@printf "Using board at %s — continue? [y/N] " "$(PORT)"; \
		read ans; case "$$ans" in [yY]*) ;; *) echo "Aborted."; exit 1 ;; esac

repl:  ## open the REPL (Ctrl-C breaks a running program, Ctrl-] exits)
	$(MP) repl

run:  ## run src/main.py on the board once, without installing it (needs libs already on board)
	$(MP) run src/main.py

mount:  ## mount ./src as the board filesystem + REPL — live edit, no copy, then `import main`
	$(MP) mount src repl

deploy: confirm-port  ## copy all device files (+ config.py) to the board's flash and reset
	$(MP) cp $(DEVICE_FILES) :
	@if [ -f src/config.py ]; then \
		$(MP) cp src/config.py : ; \
	else \
		echo "WARNING: src/config.py not found — copy config.example.py to config.py and fill it in"; \
	fi
	$(MP) reset

ls:  ## list files currently on the board
	$(MP) ls

reset: confirm-port  ## reset the board (re-runs main.py)
	$(MP) reset

wipe: confirm-port  ## remove main.py from the board so it stops auto-running on boot
	$(MP) rm :main.py

test:  ## run host-side unit tests for the pure logic (no board needed)
	uv run pytest -q
