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

# --- Dash behavior (optional; these defaults apply if you delete the lines) ---
KEY_NAME = ""           # header label, e.g. "warp". Blank shows "OpenRouter".
                        # (The API only exposes the key string, not the name you set, so
                        #  supply it here — see the README "Header name" note.)
REFRESH_SECONDS = 60    # how often to poll OpenRouter
TZ_OFFSET_HOURS = 0     # NTP syncs the clock to UTC; offset the on-screen time, e.g. -7 for PDT
