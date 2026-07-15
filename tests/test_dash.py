"""Host-side tests for the dash renderer's instant-feedback loading screen.

dash.py imports the display driver but does no hardware I/O at import time, so it
runs under CPython against a fake TFT that just records the primitives it's asked
to draw. We only assert the loading screen's user-visible contract (it clears, shows
a loading cue, names the selected key, pages when there's more than one key) — pixel
geometry is left to the board.
"""
import dash


class FakeTFT:
    """Records every draw call so a test can assert what landed on screen."""

    def __init__(self):
        self.calls = []          # method names, in call order
        self.texts = []          # (string, x, y) for each text() call

    def fill(self, *_a):
        self.calls.append("fill")

    def text(self, _font, string, x, y, *_a):
        self.calls.append("text")
        self.texts.append((string, x, y))

    def hline(self, *_a):
        self.calls.append("hline")

    def fill_rect(self, *_a):
        self.calls.append("fill_rect")

    def rect(self, *_a):
        self.calls.append("rect")

    def strings(self):
        return [s for (s, _x, _y) in self.texts]


def _assert_no_overlap_on_row(tft, y):
    """No two texts on row `y` may overlap, given the 16px-per-char font metric."""
    spans = sorted((x, x + 16 * len(s), s) for (s, x, row) in tft.texts if row == y)
    for (_, a_end, a), (b_start, _, b) in zip(spans, spans[1:]):
        assert a_end <= b_start, "%r overlaps %r" % (a, b)


def test_render_loading_clears_before_drawing():
    # Clearing first wipes the previous key's numbers so nothing stale lingers.
    tft = FakeTFT()
    dash.render_loading(tft, "prod", page=(2, 3))
    assert tft.calls[0] == "fill"


def test_render_loading_shows_a_loading_cue():
    tft = FakeTFT()
    dash.render_loading(tft, "prod", page=(2, 3))
    assert any("Load" in s for s in tft.strings())


def test_render_loading_names_the_selected_key():
    # The header confirms which key D1/D2 switched to, immediately.
    tft = FakeTFT()
    dash.render_loading(tft, "prod", page=(2, 3))
    assert "prod" in tft.strings()


def test_render_loading_falls_back_when_key_has_no_name():
    tft = FakeTFT()
    dash.render_loading(tft, None, page=(2, 3))
    assert "OpenRouter" in tft.strings()


def test_render_loading_pages_when_multiple_keys():
    tft = FakeTFT()
    dash.render_loading(tft, "prod", page=(2, 3))
    assert "2/3" in tft.strings()


def test_render_loading_hides_pager_for_a_single_key():
    # One key: paging is meaningless, matching render()'s behaviour.
    tft = FakeTFT()
    dash.render_loading(tft, "solo", page=(1, 1))
    assert not any("/" in s for s in tft.strings())


def test_render_loading_without_page_does_not_crash():
    tft = FakeTFT()
    dash.render_loading(tft, "prod")
    assert any("Load" in s for s in tft.strings())


def test_render_loading_reused_for_account_toggle():
    # D0 shows the same loading emblem; "Account" is just another title, no pager.
    tft = FakeTFT()
    dash.render_loading(tft, "Account")
    assert tft.calls[0] == "fill"
    assert "Account" in tft.strings()
    assert any("Load" in s for s in tft.strings())
    assert not any("/" in s for s in tft.strings())


# --- render_account: the D0 account overview -------------------------------------------

ACCOUNT_VIEW = {
    "title": "Account",
    "today": 1.5,
    "week": 5.0,
    "month": 12.0,
    "total_credits": 20.0,
    "total_usage": 12.4,
    "balance": 7.6,
    "used": 12.4,
    "budget": 20.0,
    "remaining": 7.6,
    "used_frac": 0.62,
    "key_count": 2,
}


def test_render_account_clears_and_headers():
    tft = FakeTFT()
    dash.render_account(tft, ACCOUNT_VIEW, "18:51", wifi_ok=True)
    assert tft.calls[0] == "fill"
    assert "Account" in tft.strings()


def test_render_account_features_used_with_cap():
    # The featured number is the credits *used* — the value that actually drives the
    # bar's fill — with the purchased-credits cap drawn beside the gauge so the ratio
    # ("$12.40 of $20.00") is self-evident. Showing the remaining balance here instead
    # sat a 38%-looking number next to a 62%-full "used" gauge and read as a mismatch.
    tft = FakeTFT()
    dash.render_account(tft, ACCOUNT_VIEW, "18:51", wifi_ok=True)
    strings = tft.strings()
    assert "Used" in strings
    assert "$12.40" in strings   # total_usage — the bar's numerator
    assert "$20.00" in strings   # total_credits — the bar's cap, beside the gauge
    assert "Left" not in strings  # balance is now the gauge's empty portion, not a row


def test_render_account_shows_summed_rows():
    tft = FakeTFT()
    dash.render_account(tft, ACCOUNT_VIEW, "18:51", wifi_ok=True)
    strings = tft.strings()
    assert "Today" in strings and "Week" in strings and "Month" in strings
    assert "$1.50" in strings and "$12.00" in strings  # today / month sums


def test_render_account_shows_key_count():
    tft = FakeTFT()
    dash.render_account(tft, ACCOUNT_VIEW, "18:51", wifi_ok=True)
    assert "2 keys" in tft.strings()


def test_render_account_singular_key_count():
    tft = FakeTFT()
    dash.render_account(tft, dict(ACCOUNT_VIEW, key_count=1), "18:51", wifi_ok=True)
    assert "1 key" in tft.strings()


def test_render_account_note_replaces_clock():
    tft = FakeTFT()
    dash.render_account(tft, ACCOUNT_VIEW, "18:51", wifi_ok=False, note="API unreachable")
    strings = tft.strings()
    assert "API unreachable" in strings
    assert not any("18:51" in s for s in strings)


def test_render_account_footer_fits_on_one_row():
    # Regression: the old "upd 18:51" clock (9 cells, ending at x=152) collided with
    # the right-aligned "2 keys" tag (starting at x=136) — the tag's first character
    # overwrote the clock's last digit on the real panel.
    tft = FakeTFT()
    dash.render_account(tft, ACCOUNT_VIEW, "18:51", wifi_ok=True)
    assert "@ 18:51" in tft.strings()
    assert "2 keys" in tft.strings()
    _assert_no_overlap_on_row(tft, 112)


def test_render_account_many_keys_drops_count_not_the_clock():
    # "10 keys" can't clear the clock; it's skipped rather than drawn on top of it.
    tft = FakeTFT()
    dash.render_account(tft, dict(ACCOUNT_VIEW, key_count=10), "18:51", wifi_ok=True)
    strings = tft.strings()
    assert "@ 18:51" in strings
    assert not any("keys" in s for s in strings)
    _assert_no_overlap_on_row(tft, 112)


def test_render_account_without_budget_shows_no_limit():
    # /credits failed: no budget/usage to draw, but the summed rows still render.
    # build_account_view sets used (total_usage) to None alongside budget in this case,
    # so the featured value degrades to "—" rather than a stale figure.
    tft = FakeTFT()
    view = dict(ACCOUNT_VIEW, balance=None, budget=None, used=None, used_frac=None)
    dash.render_account(tft, view, "18:51", wifi_ok=True)
    strings = tft.strings()
    assert any("no limit" in s for s in strings)
    assert "Used" in strings and "—" in strings


# --- render: the per-key dash footer ----------------------------------------------------

KEY_VIEW = {
    "title": "warp",
    "today": 0.35,
    "week": 1.2,
    "month": 4.5,
    "used": 0.35,
    "budget": 20.0,
    "used_frac": 0.0175,
}


def test_render_footer_clock_and_pager_do_not_overlap():
    # Worst realistic pager ("10/10", 5 cells) beside the clock on the footer row.
    tft = FakeTFT()
    dash.render(tft, KEY_VIEW, "18:51", wifi_ok=True, page=(10, 10))
    assert "@ 18:51" in tft.strings()
    assert "10/10" in tft.strings()
    _assert_no_overlap_on_row(tft, 112)
