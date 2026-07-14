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
