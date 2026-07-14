"""Board button helpers (hardware-only I/O; runs on the board).

The Reverse TFT Feather's three user buttons are wired differently: D0 (GPIO0, the
BOOT button) is active-low with a pull-up, while D1/D2 (GPIO1/GPIO2) are active-high
with a pull-down. Button hides that so callers just ask "is it down?" / "was it just
pressed?". main.py uses D1 (next) and D2 (previous) to page through configured keys.
"""
from machine import Pin


class Button:
    """A debounced push-button. `fell()` fires once per press; `pressed()` is the level.

    `active_low=True` selects the D0/BOOT wiring (pull-up, pressed reads 0); the default
    active-high wiring (pull-down, pressed reads 1) matches D1/D2. Debounce is handled by
    the caller polling at a coarse interval (~50 ms), well above real contact bounce.
    """

    def __init__(self, gpio, active_low=False):
        pull = Pin.PULL_UP if active_low else Pin.PULL_DOWN
        self._pin = Pin(gpio, Pin.IN, pull)
        self._active = 0 if active_low else 1
        self._was_down = self.pressed()

    def pressed(self):
        """True while the button is physically held down."""
        return self._pin.value() == self._active

    def fell(self):
        """True exactly once on the press (down now, up on the previous check)."""
        down = self.pressed()
        edge = down and not self._was_down
        self._was_down = down
        return edge
