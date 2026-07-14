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

# --- OpenRouter ---
# A normal *inference* API key (NOT a management/provisioning key) — the dash only reads
# usage, so a read-only key is all it needs. Create one at:
#     https://openrouter.ai/settings/keys
OPENROUTER_API_KEY = "sk-or-v1-..."

# --- Multiple keys (optional) ---
# To watch several keys, list them here and page through them with the on-board buttons:
# D1 = next key, D2 = previous key. The header shows each key's `name` and a "1/3" pager
# marks the current one. When OPENROUTER_KEYS is set it takes precedence over the single
# OPENROUTER_API_KEY above; each entry is a normal inference key, same as that one.
#
# OPENROUTER_KEYS = [
#     {"key": "sk-or-v1-...", "name": "warp"},
#     {"key": "sk-or-v1-...", "name": "prod"},
#     {"key": "sk-or-v1-...", "name": "personal"},
# ]

# --- Dash behavior (optional; these defaults apply if you delete the lines) ---
KEY_NAME = ""           # header label for the single key above, e.g. "warp". Blank shows
                        # "OpenRouter". (The API only exposes the key string, not the name
                        #  you set, so supply it here — see the README "Header name" note.
                        #  With OPENROUTER_KEYS, use each entry's "name" instead.)
REFRESH_SECONDS = 60    # how often to poll OpenRouter
TZ_OFFSET_HOURS = 0     # NTP syncs the clock to UTC; offset the on-screen time, e.g. -7 for PDT
