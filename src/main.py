"""TFT hello world for the Adafruit ESP32-S3 Reverse TFT Feather (#5691).

Runs on boot: powers the display, then paints "Hello, buddy!" in white on blue.
Deploy it with `make deploy`; open a live prompt with `make repl` (Ctrl-C stops it).

The GPIO numbers below are the verified pins for this board (see the README pin table).
"""
from machine import Pin, SPI
import st7789py as st7789
import vga2_bold_16x16 as font

# The Reverse TFT gates the display + STEMMA I2C rail on GPIO7 — drive HIGH to power the screen.
Pin(7, Pin.OUT, value=1)

spi = SPI(1, baudrate=40_000_000, sck=Pin(36), mosi=Pin(35))

tft = st7789.ST7789(
    spi,
    135, 240,                 # native panel size; rotation reorients it
    reset=Pin(41, Pin.OUT),
    dc=Pin(40, Pin.OUT),
    cs=Pin(42, Pin.OUT),
    backlight=Pin(45, Pin.OUT),
    rotation=1,               # 1 = 240x135 landscape (driver applies the 40/53 offset for you)
)

tft.fill(st7789.BLUE)
tft.text(font, "Hello, buddy!", 10, 55, st7789.WHITE, st7789.BLUE)
