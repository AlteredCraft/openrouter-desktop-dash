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

# Last-refresh stamp, bottom-left: "@ 18:51". The footer row fits 14 cells between the
# 8px gutters; a longer prefix ("upd ") left no room for the account screen's right-
# aligned "2 keys" tag, whose first cell landed on the clock's last digit.
_CLOCK_PREFIX = "@ "


def _row(tft, label, value, y):
    tft.text(font, label, 8, y, st7789.WHITE, st7789.BLACK)
    tft.text(font, usage_view.fmt_usd(value), _VALUE_X, y, st7789.CYAN, st7789.BLACK)


def _center_x(text):
    x = (_W - len(text) * _CHAR) // 2
    return x if x > 0 else 0


def render(tft, view, updated, wifi_ok, note=None, page=None):
    """Draw the full dash. `note`, if set, replaces the clock with a short warning.

    `page` is an optional (current, total) tuple; when more than one key is configured
    it draws a small right-aligned "1/3" pager on the bottom row so you can see which
    key the D1/D2 buttons have selected.
    """
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
        # A warning can be up to the full row width, so skip the pager to avoid
        # overlapping it — the header key name still shows which key is selected.
        tft.text(font, note, 8, 112, st7789.YELLOW, st7789.BLACK)
    else:
        tft.text(font, _CLOCK_PREFIX + updated, 8, 112, _DIM, st7789.BLACK)
        if page and page[1] > 1:
            pager = "%d/%d" % page
            tft.text(font, pager, _W - len(pager) * _CHAR - 8, 112, _DIM, st7789.BLACK)


def render_account(tft, view, updated, wifi_ok, note=None):
    """Draw the D0 account overview: today/week/month summed across all keys, plus the
    account credit balance and a burn bar (credits used of credits purchased).

    Mirrors render()'s layout so the toggle reads instantly, but the header is fixed to
    'Account', the featured number is credits used ('Used', the bar's numerator), and the
    bottom row shows a key count instead of a pager. `note` replaces the clock with a short
    warning, exactly as in render().
    """
    tft.fill(st7789.BLACK)

    tft.text(font, "Account", 8, 0, st7789.WHITE, st7789.BLACK)
    tft.fill_rect(224, 2, 12, 12, st7789.GREEN if wifi_ok else st7789.RED)
    tft.hline(0, 18, _W, _DIM)

    _row(tft, "Today", view["today"], 20)
    _row(tft, "Week", view["week"], 38)
    _row(tft, "Month", view["month"], 56)

    tft.hline(0, 74, _W, _DIM)
    # Feature the credits *used* — the number the bar actually fills to — with the
    # purchased-credits cap ('$20.00') drawn beside the gauge, so "$12.39 of $20.00" is
    # self-evident. Remaining ('Left') is the gauge's unfilled portion; showing that
    # figure here instead put a 38%-looking number next to a 62%-full bar and misread.
    tft.text(font, "Used", 8, 76, st7789.WHITE, st7789.BLACK)
    tft.text(font, usage_view.fmt_usd(view["used"]), _VALUE_X, 76, st7789.CYAN, st7789.BLACK)

    _budget_bar(tft, view["used_frac"], view["budget"], 8, 96, _W - 16, 10)

    if note:
        tft.text(font, note, 8, 112, st7789.YELLOW, st7789.BLACK)
    else:
        clock = _CLOCK_PREFIX + updated
        tft.text(font, clock, 8, 112, _DIM, st7789.BLACK)
        count = view.get("key_count")
        if count:
            # Right-aligned key count, drawn only if it clears the clock by a full
            # cell — a double-digit count ("10 keys") would otherwise run into it.
            tag = "1 key" if count == 1 else "%d keys" % count
            x = _W - len(tag) * _CHAR - 8
            if x >= 8 + (len(clock) + 1) * _CHAR:
                tft.text(font, tag, x, 112, _DIM, st7789.BLACK)


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


def render_loading(tft, title, page=None):
    """Instant acknowledgement of a D1/D2 key switch.

    A key switch has to wait on the network fetch before the new numbers exist, so
    paint the newly selected key's header, a "Loading" cue and the pager right away —
    otherwise the press leaves the *previous* key's dash on screen for the whole
    round-trip and feels unregistered. `title` is the key's config name (None falls
    back like the header does); `page` is the same (current, total) tuple as render().
    """
    tft.fill(st7789.BLACK)
    tft.text(font, usage_view.header_text(title), 8, 0, st7789.WHITE, st7789.BLACK)
    tft.hline(0, 18, _W, _DIM)
    tft.text(font, "Loading", _center_x("Loading"), 56, st7789.CYAN, st7789.BLACK)
    if page and page[1] > 1:
        pager = "%d/%d" % page
        tft.text(font, pager, _W - len(pager) * _CHAR - 8, 112, _DIM, st7789.BLACK)


_MAX_CELLS = _W // _CHAR  # 15 glyphs fit across the 240px panel


def _clip(text):
    """Truncate to the panel width, marking cut-off text with a trailing '~'.

    The driver silently drops any glyph past the right edge, so a long value (e.g. a
    32-char Wi-Fi SSID) would otherwise be cut mid-character with no hint there's more.
    """
    if len(text) <= _MAX_CELLS:
        return text
    return text[: _MAX_CELLS - 1] + "~"


def render_error(tft, title, detail, detail2=None):
    """Centered message for states with no data to show (setup/connect/fatal).

    Two lines by default; pass detail2 for a third row. The Wi-Fi failure screen uses
    it to name the SSID we tried, so a wrong/typo'd or out-of-range network is obvious
    on the panel. Lines longer than the display width are clipped by _clip().
    """
    tft.fill(st7789.BLACK)
    if detail2 is None:
        rows = ((title, 45, st7789.WHITE), (detail, 72, _DIM))
    else:
        rows = ((title, 38, st7789.WHITE), (detail, 65, _DIM), (detail2, 92, _DIM))
    for text, y, color in rows:
        text = _clip(text)
        tft.text(font, text, _center_x(text), y, color, st7789.BLACK)
