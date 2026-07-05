# src/config.example.py
#
# Secrets template. Used starting in Phase 3 (Wi-Fi + weather API); nothing imports it yet.
# Copy it to config.py and fill in your values:
#
#     cp src/config.example.py src/config.py
#
# config.py is gitignored, so your real credentials never get committed. Both files live
# under src/ so they deploy to the board with everything else. On the board, read them with:
#
#     import config
#     wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)

WIFI_SSID = "your-wifi-name"
WIFI_PASSWORD = "your-wifi-password"
WEATHER_API_KEY = ""  # only if a service needs one; Open-Meteo does not
