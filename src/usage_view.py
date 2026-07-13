"""Pure logic: turn OpenRouter API payloads into a display view-model.

Imports nothing hardware-specific, so this module runs under CPython and is
unit-tested on the host (see tests/test_usage_view.py). Keep every parsing and
formatting decision here; net.py / openrouter.py / dash.py stay thin around it.
"""


def _num(value):
    """Coerce an API number to float. None / missing / unparseable -> None (not 0)."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _unwrap(payload):
    """Return the inner dict whether given {'data': {...}} or an already-unwrapped {...}."""
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return payload["data"]
    return payload or {}


def fmt_usd(value):
    """Format a credit amount (USD) for the tiny screen: 1.2345 -> '$1.23', None -> '—'."""
    n = _num(value)
    if n is None:
        return "—"
    if n < 0:
        n = 0.0
    return "${:.2f}".format(n)


def header_text(label, limit=10, fallback="OpenRouter"):
    """Top-left header: the key's label, first `limit` chars + '...' if longer.

    Falls back to `fallback` when the key has no label. Kept short so it fits left
    of the Wi-Fi dot (limit + '...' = 13 chars, within the 240px-wide screen).
    """
    if not label:
        return fallback
    label = str(label)
    if len(label) > limit:
        return label[:limit] + "..."
    return label


def budget_color(used_frac):
    """Semantic color for the budget bar as spend approaches the cap.

    green (< 50% used) -> orange (50%-75%) -> red (>= 75%). None when there's no
    budget to measure against. dash.py maps these names to actual pixel colors.
    """
    if used_frac is None:
        return None
    if used_frac < 0.50:
        return "green"
    if used_frac < 0.75:
        return "orange"
    return "red"


def build_view(key_data, credits_data=None, key_name=None):
    """Combine GET /api/v1/key and (optional) GET /api/v1/credits payloads into a view-model.

    Accepts either raw responses ({"data": {...}}) or already-unwrapped dicts.

    `key_name` is the header title. The API's `/key` endpoint only exposes the key
    *string* (its `label`), not the human name you set, so the name is supplied from
    config instead; None falls back to "OpenRouter" in header_text().

    The featured budget is the *key's own credit limit* when one is set — so a key
    with a $20 cap graphs used-of-$20 (`limit`, `limit_remaining`, `usage`). Keys with
    no limit fall back to the account-wide balance from /credits (total_credits /
    total_usage). `used_frac` / `remaining_frac` are None when there's no budget to
    draw a bar against, so dash.py renders text instead of a gauge.
    """
    key = _unwrap(key_data)
    credits = _unwrap(credits_data) if credits_data is not None else None

    limit = _num(key.get("limit"))
    key_remaining = _num(key.get("limit_remaining"))
    key_usage = _num(key.get("usage"))

    balance = None
    total_credits = None
    total_usage = None
    if credits is not None:
        total_credits = _num(credits.get("total_credits"))
        total_usage = _num(credits.get("total_usage"))
        if total_credits is not None and total_usage is not None:
            balance = total_credits - total_usage

    if limit is not None:
        # Per-key budget. Derive "used" from the limit and what's left, so it stays
        # correct even if a resetting limit makes `usage` (all-time) diverge from the cap.
        budget = limit
        remaining = key_remaining
        used = (limit - key_remaining) if key_remaining is not None else key_usage
        budget_source = "key"
    elif balance is not None:
        budget = total_credits
        remaining = balance
        used = total_usage
        budget_source = "account"
    else:
        budget = None
        remaining = key_remaining
        used = key_usage
        budget_source = None

    used_frac = None
    remaining_frac = None
    if budget not in (None, 0):
        if used is not None:
            used_frac = min(1.0, max(0.0, used / budget))
        if remaining is not None:
            remaining_frac = min(1.0, max(0.0, remaining / budget))
        elif used_frac is not None:
            remaining_frac = 1.0 - used_frac

    return {
        "title": key_name,  # header label from config (see key_name above)
        "today": _num(key.get("usage_daily")),
        "week": _num(key.get("usage_weekly")),
        "month": _num(key.get("usage_monthly")),
        "total": key_usage,
        "limit": limit,
        "budget": budget,
        "used": used,
        "remaining": remaining,
        "used_frac": used_frac,
        "remaining_frac": remaining_frac,
        "budget_source": budget_source,
        "account_balance": balance,  # kept even when a key limit is the featured budget
        "is_free_tier": bool(key.get("is_free_tier")),
    }
