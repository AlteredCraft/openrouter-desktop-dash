"""Host-side unit tests for the pure view-model logic (run with `make test`)."""
import pytest

import usage_view

# A realistic GET /api/v1/key payload (data-wrapped), per OpenRouter's documented schema.
KEY_PAYLOAD = {
    "data": {
        "label": "dash-key",
        "limit": 50.0,
        "limit_reset": None,
        "limit_remaining": 38.5,
        "include_byok_in_limit": False,
        "usage": 11.5,
        "usage_daily": 1.2345,
        "usage_weekly": 8.9,
        "usage_monthly": 31.07,
        "byok_usage": 0.0,
        "is_free_tier": False,
    }
}

CREDITS_PAYLOAD = {"data": {"total_credits": 100.0, "total_usage": 81.1}}


def test_build_view_basic_amounts():
    v = usage_view.build_view(KEY_PAYLOAD, CREDITS_PAYLOAD)
    assert v["today"] == pytest.approx(1.2345)
    assert v["week"] == pytest.approx(8.9)
    assert v["month"] == pytest.approx(31.07)
    assert v["total"] == pytest.approx(11.5)
    assert v["is_free_tier"] is False


def test_budget_prefers_key_limit_over_account():
    # Key has a $50 limit, so the bar measures used-of-$50 even though /credits is present.
    v = usage_view.build_view(KEY_PAYLOAD, CREDITS_PAYLOAD)
    assert v["budget_source"] == "key"
    assert v["budget"] == pytest.approx(50.0)
    assert v["used"] == pytest.approx(11.5)  # limit(50) - limit_remaining(38.5)
    assert v["remaining"] == pytest.approx(38.5)
    assert v["used_frac"] == pytest.approx(0.23)
    assert v["remaining_frac"] == pytest.approx(0.77)


def test_real_world_small_usage_against_20_limit():
    # Mirrors the reported case: $0.35 used on a key with a $20 limit.
    key = {"data": {"limit": 20.0, "limit_remaining": 19.65, "usage": 0.35,
                    "usage_daily": 0.35, "usage_weekly": 0.35, "usage_monthly": 0.35}}
    v = usage_view.build_view(key, {"data": {"total_credits": 20.0, "total_usage": 12.27}})
    assert v["budget"] == pytest.approx(20.0)
    assert v["used"] == pytest.approx(0.35)
    assert v["used_frac"] == pytest.approx(0.0175)
    assert v["account_balance"] == pytest.approx(7.73)  # still available if we want it


def test_falls_back_to_account_when_no_key_limit():
    data = {"data": dict(KEY_PAYLOAD["data"], limit=None, limit_remaining=None)}
    v = usage_view.build_view(data, CREDITS_PAYLOAD)
    assert v["budget_source"] == "account"
    assert v["budget"] == pytest.approx(100.0)
    assert v["used"] == pytest.approx(81.1)
    assert v["remaining"] == pytest.approx(18.9)
    assert v["used_frac"] == pytest.approx(0.811)
    assert v["remaining_frac"] == pytest.approx(0.189)


def test_no_budget_when_neither_limit_nor_credits():
    data = {"data": dict(KEY_PAYLOAD["data"], limit=None, limit_remaining=None)}
    v = usage_view.build_view(data, None)
    assert v["budget_source"] is None
    assert v["budget"] is None
    assert v["used_frac"] is None
    assert v["remaining_frac"] is None


def test_accepts_unwrapped_dicts():
    v = usage_view.build_view(KEY_PAYLOAD["data"], CREDITS_PAYLOAD["data"])
    assert v["month"] == pytest.approx(31.07)
    assert v["budget"] == pytest.approx(50.0)


def test_used_frac_clamps_to_one_when_overspent():
    key = {"data": dict(KEY_PAYLOAD["data"], limit=None, limit_remaining=None)}
    over = {"data": {"total_credits": 10.0, "total_usage": 12.0}}
    v = usage_view.build_view(key, over)
    assert v["used_frac"] == 1.0
    assert v["remaining_frac"] == 0.0


def test_zero_budget_yields_no_bar_not_crash():
    key = {"data": dict(KEY_PAYLOAD["data"], limit=0.0, limit_remaining=0.0)}
    v = usage_view.build_view(key, None)
    assert v["used_frac"] is None  # avoids divide-by-zero


@pytest.mark.parametrize(
    "value,expected",
    [
        (1.2345, "$1.23"),
        (31.07, "$31.07"),
        (0, "$0.00"),
        (None, "—"),
        (-3.0, "$0.00"),
        (1000.5, "$1000.50"),
    ],
)
def test_fmt_usd(value, expected):
    assert usage_view.fmt_usd(value) == expected


@pytest.mark.parametrize(
    "label,expected",
    [
        (None, "OpenRouter"),        # no label -> fallback
        ("", "OpenRouter"),
        ("prod", "prod"),
        ("abcdefghij", "abcdefghij"),      # exactly 10 -> no ellipsis
        ("abcdefghijk", "abcdefghij..."),  # 11 -> first 10 + ...
        ("my-openrouter-key", "my-openrou..."),
    ],
)
def test_header_text(label, expected):
    assert usage_view.header_text(label) == expected


def test_title_comes_from_key_name_not_api():
    # The API's `label` is the key string, not a name — the header title is config-supplied.
    assert usage_view.build_view(KEY_PAYLOAD, CREDITS_PAYLOAD, key_name="warp")["title"] == "warp"
    assert usage_view.build_view(KEY_PAYLOAD, CREDITS_PAYLOAD)["title"] is None  # -> "OpenRouter"


@pytest.mark.parametrize(
    "used_frac,expected",
    [
        (None, None),
        (0.0, "green"),
        (0.0175, "green"),  # the $0.35 / $20 case
        (0.49, "green"),
        (0.50, "orange"),   # boundary: 50% -> orange
        (0.60, "orange"),
        (0.749, "orange"),
        (0.75, "red"),      # boundary: 75% -> red
        (0.90, "red"),
        (1.0, "red"),
    ],
)
def test_budget_color_thresholds(used_frac, expected):
    assert usage_view.budget_color(used_frac) == expected


# --- build_account_view: the D0 account overview ---------------------------------------

# Two keys as GET /key returns them, plus the single account-wide /credits payload.
ACCT_KEY_A = {"data": {"usage_daily": 1.0, "usage_weekly": 2.0, "usage_monthly": 5.0}}
ACCT_KEY_B = {"data": {"usage_daily": 0.5, "usage_weekly": 3.0, "usage_monthly": 7.0}}
ACCT_CREDITS = {"data": {"total_credits": 20.0, "total_usage": 12.4}}


def test_account_sums_usage_across_keys():
    v = usage_view.build_account_view([ACCT_KEY_A, ACCT_KEY_B], ACCT_CREDITS, key_count=2)
    assert v["title"] == "Account"
    assert v["today"] == pytest.approx(1.5)   # 1.0 + 0.5
    assert v["week"] == pytest.approx(5.0)    # 2.0 + 3.0
    assert v["month"] == pytest.approx(12.0)  # 5.0 + 7.0
    assert v["key_count"] == 2


def test_account_balance_and_burn_from_credits():
    v = usage_view.build_account_view([ACCT_KEY_A], ACCT_CREDITS)
    assert v["total_credits"] == pytest.approx(20.0)
    assert v["total_usage"] == pytest.approx(12.4)
    assert v["balance"] == pytest.approx(7.6)      # 20 - 12.4, the "Left" number
    assert v["remaining"] == pytest.approx(7.6)
    assert v["budget"] == pytest.approx(20.0)      # bar measures burn of purchased credits
    assert v["used"] == pytest.approx(12.4)
    assert v["used_frac"] == pytest.approx(0.62)


def test_account_accepts_unwrapped_dicts():
    v = usage_view.build_account_view(
        [ACCT_KEY_A["data"], ACCT_KEY_B["data"]], ACCT_CREDITS["data"], key_count=2
    )
    assert v["today"] == pytest.approx(1.5)
    assert v["balance"] == pytest.approx(7.6)


def test_account_burn_clamps_when_overspent():
    over = {"data": {"total_credits": 10.0, "total_usage": 12.0}}
    v = usage_view.build_account_view([ACCT_KEY_A], over)
    assert v["used_frac"] == 1.0
    assert v["balance"] == pytest.approx(-2.0)  # balance itself isn't clamped, only the bar


def test_account_no_keys_yields_none_usage_not_zero():
    # All key fetches failed but /credits came back: show the balance, not fake $0 rows.
    v = usage_view.build_account_view([], ACCT_CREDITS, key_count=2)
    assert v["today"] is None
    assert v["week"] is None
    assert v["month"] is None
    assert v["balance"] == pytest.approx(7.6)


def test_account_no_credits_yields_no_bar():
    # /credits failed but keys came back: usage still sums, but there's no budget to draw.
    v = usage_view.build_account_view([ACCT_KEY_A, ACCT_KEY_B], None, key_count=2)
    assert v["today"] == pytest.approx(1.5)
    assert v["balance"] is None
    assert v["budget"] is None
    assert v["used_frac"] is None


def test_account_zero_credits_yields_no_bar_not_crash():
    v = usage_view.build_account_view([ACCT_KEY_A], {"data": {"total_credits": 0.0, "total_usage": 0.0}})
    assert v["used_frac"] is None  # avoids divide-by-zero


def test_account_partial_key_field_still_sums():
    # A key missing usage_weekly contributes 0 to that field but its peers still count.
    partial = {"data": {"usage_daily": 1.0, "usage_monthly": 4.0}}  # no usage_weekly
    v = usage_view.build_account_view([partial, ACCT_KEY_B], ACCT_CREDITS, key_count=2)
    assert v["today"] == pytest.approx(1.5)
    assert v["week"] == pytest.approx(3.0)   # 0 (missing) + 3.0
    assert v["month"] == pytest.approx(11.0)
