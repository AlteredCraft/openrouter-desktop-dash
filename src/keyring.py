"""Pure logic: a cycle of OpenRouter API keys the user pages through with the buttons.

Imports nothing hardware-specific, so this module runs under CPython and is
unit-tested on the host (see tests/test_keyring.py). main.py wires the board's
D1/D2 buttons to KeyRing.next()/prev(); dash.py draws position() as a "1/3" pager.

Config accepts two forms (newest first):
  OPENROUTER_KEYS = [{"key": "sk-or-...", "name": "warp"}, {"key": "sk-or-...", "name": "prod"}]
  OPENROUTER_API_KEY = "sk-or-..."   # legacy single-key form, still supported
"""


def _blank_or_placeholder(value):
    """True if `value` is unset or still a template placeholder (so we skip it)."""
    if not value or not isinstance(value, str):
        return True
    value = value.strip()
    # "your-..." matches config.example.py's Wi-Fi placeholders; "sk-or-v1-..." is the
    # key placeholder. A real key is longer than the bare "sk-or-v1-..." stub.
    return not value or value.startswith("your-") or value == "sk-or-v1-..."


def normalize_keys(keys=None, api_key=None, key_name=None):
    """Build a list of {"key", "name"} entries from config, multi-key form first.

    `keys` is the OPENROUTER_KEYS list — each item a {"key", "name"} dict or a bare
    "sk-or-..." string. `api_key` / `key_name` are the legacy single-key config, used
    only when `keys` yields nothing usable. Blank/placeholder entries are dropped, so
    an untouched template contributes no keys and main.py shows "Setup needed".
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

    if not entries and not _blank_or_placeholder(api_key):
        entries.append({"key": api_key, "name": key_name or None})

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

    def next(self):
        self._index = (self._index + 1) % len(self._entries)
        return self.current()

    def prev(self):
        self._index = (self._index - 1) % len(self._entries)
        return self.current()

    def position(self):
        """1-based (current, total) for the on-screen pager, e.g. (1, 3)."""
        return (self._index + 1, len(self._entries))
