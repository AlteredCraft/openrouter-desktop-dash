# src/config.example.py
#
# Settings + secrets for the OpenRouter usage dash. Copy this to config.py and fill it in:
#
#     cp src/config.example.py src/config.py
#
# config.py is gitignored, so your real credentials never get committed. Both files live
# under src/ so they deploy to the board with `make deploy`. main.py fails fast with an
# on-screen "Setup needed" message if any required value below is still a placeholder.

# --- Wi-Fi (2.4 GHz only — the ESP32-S3 has no 5 GHz radio) ---
WIFI_SSID = "your-wifi-name"
WIFI_PASSWORD = "your-wifi-password"

# --- OpenRouter (required) ---
# One or more OpenRouter keys, listed here as OPENROUTER_KEYS. Each is a normal
# *inference* API key (NOT a management/provisioning key) — the dash only reads usage,
# so a read-only key is all it needs. Create keys at:
#     https://openrouter.ai/settings/keys
#
# Each entry is a {"key", "name"} dict. `name` is the header label for that key (the API
# only exposes the key string, not the name you gave it, so supply it here — see the
# README "Header name" note); it's optional and falls back to "OpenRouter" if omitted.
#
# List several keys to watch them all on one board: page through them with the on-board
# buttons (D1 = next key, D2 = previous key). The header shows the current key's `name`
# and a "1/3" pager marks which one is active. With a single key the buttons do nothing.
OPENROUTER_KEYS = [
    {"key": "sk-or-v1-...", "name": "warp"},
    # {"key": "sk-or-v1-...", "name": "prod"},
    # {"key": "sk-or-v1-...", "name": "personal"},
]

# --- Dash behavior (optional; these defaults apply if you delete the lines) ---
REFRESH_SECONDS = 60    # how often to poll OpenRouter
TZ_OFFSET_HOURS = 0     # NTP syncs the clock to UTC; offset the on-screen time, e.g. -7 for PDT
