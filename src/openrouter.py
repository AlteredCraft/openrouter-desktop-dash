"""OpenRouter API client (hardware-only I/O; runs on the board).

Thin wrapper over urequests: fetch a payload, return the parsed dict. All the
parsing/formatting decisions live in usage_view.py so they stay host-testable.

Uses a normal inference API key (Authorization: Bearer ...), not a management key.
Endpoints:
  GET /api/v1/key      -> per-key usage (daily/weekly/monthly), limit, remaining
  GET /api/v1/credits  -> account-wide total_credits / total_usage
"""
import urequests

_BASE = "https://openrouter.ai/api/v1"


class ApiError(Exception):
    """Non-200 response. Carries `status` so callers can tell 401 (bad key) from an outage."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def _get(path, api_key):
    resp = urequests.get(_BASE + path, headers={"Authorization": "Bearer " + api_key})
    try:
        if resp.status_code != 200:
            raise ApiError(resp.status_code, "HTTP %d" % resp.status_code)
        return resp.json()
    finally:
        resp.close()


def fetch_key(api_key):
    """GET /key -> dict with usage_daily/weekly/monthly, limit, limit_remaining, ..."""
    return _get("/key", api_key)


def fetch_credits(api_key):
    """GET /credits -> dict with total_credits and total_usage."""
    return _get("/credits", api_key)
