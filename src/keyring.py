"""Pure logic: a cycle of OpenRouter API keys the user pages through with the buttons.

Imports nothing hardware-specific, so this module runs under CPython and is
unit-tested on the host (see tests/test_keyring.py). main.py wires the board's
D1/D2 buttons to KeyRing.next()/prev(); dash.py draws position() as a "1/3" pager.

Keys come from config as OPENROUTER_KEYS, a list of entries — each a
{"key", "name"} dict or a bare "sk-or-..." string:
  OPENROUTER_KEYS = [{"key": "sk-or-...", "name": "warp"}, {"key": "sk-or-...", "name": "prod"}]

Wi-Fi networks come from config as WIFI_NETWORKS, a list of {"ssid", "password"}
dicts (see normalize_wifi). The dash tries each in order until one connects.
"""


def _blank_or_placeholder(value):
    """True if `value` is unset or still a template placeholder (so we skip it)."""
    if not value or not isinstance(value, str):
        return True
    value = value.strip()
    # "your-..." matches config.example.py's Wi-Fi placeholders; "sk-or-v1-..." is the
    # key placeholder. A real key is longer than the bare "sk-or-v1-..." stub.
    return not value or value.startswith("your-") or value == "sk-or-v1-..."


def normalize_keys(keys=None):
    """Build a list of {"key", "name"} entries from config's OPENROUTER_KEYS.

    `keys` is the OPENROUTER_KEYS list — each item a {"key", "name"} dict or a bare
    "sk-or-..." string. Blank/placeholder entries are dropped, so an untouched
    template contributes no keys and main.py shows "Setup needed".
    """
    entries = []
    for item in keys or ():
        if isinstance(item, str):
            key, name = item, None
        elif isinstance(item, dict):
            key, name = item.get("key"), item.get("name")
        else:
            continue
        if _blank_or_placeholder(key):
            continue
        entries.append({"key": key, "name": name or None})

    return entries


def normalize_wifi(networks=None):
    """Build a list of {"ssid", "password"} entries from config's WIFI_NETWORKS.

    `networks` is the WIFI_NETWORKS list — each item a {"ssid", "password"} dict
    (password optional, defaults to "" for open networks). Blank/placeholder SSIDs
    are dropped, so an untouched template contributes no networks. Returns the
    usable networks in config order; the list may be empty, in which case main.py
    falls back to the legacy WIFI_SSID/WIFI_PASSWORD pair before complaining.
    """
    entries = []
    for item in networks or ():
        if not isinstance(item, dict):
            continue
        ssid, password = item.get("ssid"), item.get("password", "")
        if _blank_or_placeholder(ssid):
            continue
        entries.append({"ssid": ssid, "password": password or ""})
    return entries


class KeyRing:
    """A non-empty, cyclic list of {"key", "name"} entries with a current selection.

    next()/prev() advance the selection (wrapping at both ends) and return the newly
    current entry. Raises ValueError on an empty list so main.py can fail fast to a
    "Setup needed" screen instead of dividing by zero.
    """

    def __init__(self, entries):
        if not entries:
            raise ValueError("no API keys configured")
        self._entries = list(entries)
        self._index = 0

    def __len__(self):
        return len(self._entries)

    @property
    def index(self):
        return self._index

    @property
    def has_multiple(self):
        """True when paging is meaningful (more than one key configured)."""
        return len(self._entries) > 1

    def current(self):
        return self._entries[self._index]

    def entries(self):
        """A copy of every entry in ring order, for the account rollup (D0 screen).

        Returns a fresh list so a caller iterating all keys can't disturb the ring's
        selection; the on-screen index is unchanged.
        """
        return list(self._entries)

    def next(self):
        self._index = (self._index + 1) % len(self._entries)
        return self.current()

    def prev(self):
        self._index = (self._index - 1) % len(self._entries)
        return self.current()

    def position(self):
        """1-based (current, total) for the on-screen pager, e.g. (1, 3)."""
        return (self._index + 1, len(self._entries))
