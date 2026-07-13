"""Render the usage view-model onto the 240x135 TFT (runs on the board).

Layout is tuned for the vendored 16x16 bitmap font (15 chars wide, ~8 rows tall).
User-facing text stays short and non-technical per the project's logging rules —
full error detail is printed to the serial REPL by main.py, never shown here.
"""
import st7789py as st7789
import vga2_bold_16x16 as font

import usage_view

_W = 240
_CHAR = 16  # font is 16x16

_DIM = st7789.color565(90, 90, 90)
_BARBG = st7789.color565(40, 40, 40)

# Budget-bar colors keyed by usage_view.budget_color(); the driver has no ORANGE constant.
_BAR_COLORS = {
    "green": st7789.GREEN,
    "orange": st7789.color565(255, 140, 0),
    "red": st7789.RED,
}


# Value column starts here: labels are <=5 chars (<=80px from x=8), and x=104 leaves room
# for amounts up to "$9999.99" (8 chars = 128px) without running past the 240px edge.
_VALUE_X = 104


def _row(tft, label, value, y):
    tft.text(font, label, 8, y, st7789.WHITE, st7789.BLACK)
    tft.text(font, usage_view.fmt_usd(value), _VALUE_X, y, st7789.CYAN, st7789.BLACK)


def _center_x(text):
    x = (_W - len(text) * _CHAR) // 2
    return x if x > 0 else 0


def render(tft, view, updated, wifi_ok, note=None):
    """Draw the full dash. `note`, if set, replaces the clock with a short warning."""
    tft.fill(st7789.BLACK)

    tft.text(font, usage_view.header_text(view.get("title")), 8, 0, st7789.WHITE, st7789.BLACK)
    tft.fill_rect(224, 2, 12, 12, st7789.GREEN if wifi_ok else st7789.RED)
    tft.hline(0, 18, _W, _DIM)

    _row(tft, "Today", view["today"], 20)
    _row(tft, "Week", view["week"], 38)
    _row(tft, "Month", view["month"], 56)

    tft.hline(0, 74, _W, _DIM)
    tft.text(font, "Used", 8, 76, st7789.WHITE, st7789.BLACK)
    tft.text(font, usage_view.fmt_usd(view["used"]), _VALUE_X, 76, st7789.CYAN, st7789.BLACK)

    _budget_bar(tft, view["used_frac"], view["budget"], 8, 96, _W - 16, 10)

    if note:
        tft.text(font, note, 8, 112, st7789.YELLOW, st7789.BLACK)
    else:
        tft.text(font, "upd " + updated, 8, 112, _DIM, st7789.BLACK)


def _budget_bar(tft, used_frac, budget, x, y, w, h):
    """Budget-used meter: fills toward the limit (green -> orange -> red), limit shown at right.

    `used_frac` is None when the key has no limit and no account budget to measure against.
    """
    if used_frac is None:
        tft.text(font, "no limit", x, y - 3, _DIM, st7789.BLACK)
        return

    label = usage_view.fmt_usd(budget)  # e.g. "$20.00"
    bar_w = w - len(label) * _CHAR - 6
    tft.fill_rect(x, y, bar_w, h, _BARBG)

    fill_w = int(bar_w * used_frac)
    if fill_w < 1 and used_frac > 0:
        fill_w = 1  # show a sliver as soon as there's any spend
    if fill_w > 0:
        tft.fill_rect(x, y, fill_w, h, _BAR_COLORS[usage_view.budget_color(used_frac)])
    tft.rect(x, y, bar_w, h, _DIM)
    tft.text(font, label, x + bar_w + 6, y - 3, _DIM, st7789.BLACK)


def render_error(tft, title, detail):
    """Centered two-line message for states with no data to show (setup/connect/fatal)."""
    tft.fill(st7789.BLACK)
    tft.text(font, title, _center_x(title), 45, st7789.WHITE, st7789.BLACK)
    tft.text(font, detail, _center_x(detail), 72, _DIM, st7789.BLACK)
