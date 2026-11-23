# AquaTrack

Water flow monitoring system with an ESP32 sensor node, Django backend, and React (Vite) frontend.

## Quick Start

Run the unified launcher from the repository root:

```bash
node start.mjs
```

Or on Windows, double-click / run:

```bat
start-aquatrack.bat
```

This starts:
- **Backend (Django):** `0.0.0.0:8000` (uses `aquatrack-backend/.venv` if present)
- **Frontend (Vite):** `http://localhost:5173`
- **USB Serial Bridge (Windows):** Automatically reads `COM3` (or the first available COM port) at `115200` baud and forwards readings to `http://127.0.0.1:8000/api/ingest/` if Wi-Fi is unavailable. Close the Arduino IDE Serial Monitor so `COM3` is not busy.

---

## Things to Manually Change Before Running

### 1. ESP32 Firmware (`esp32/sketch_nov23a/sketch_nov23a.ino`)
Update the Wi-Fi credentials, your PC's local IPv4 address, and the device API key before uploading to the ESP32:

```cpp
const char* WIFI_SSID     = "Redmi 13C";
const char* WIFI_PASSWORD = "12345678";
// Point to the PC running AquaTrack backend (check with `ipconfig` -> IPv4 Address)
const char* SERVER_URL    = "http://10.138.54.77:8000";
// Paste the api_key printed when registering this ESP32 device
const char* DEVICE_KEY    = "ydwqBbiuvYBzxTwyiEEnI5Ju6sGGayGGBxSsNfJssrc";
```

- **`WIFI_SSID` / `WIFI_PASSWORD`**: Must match the Wi-Fi network/hotspot your PC and ESP32 are both connected to.
- **`SERVER_URL`**: Run `ipconfig` on your PC (or check the `ESP32 SERVER_URL candidates:` line printed by `node start.mjs`) and set this to your PC's current IPv4 address on port `8000`. If you switch hotspots/networks, this IP will change and must be updated and re-uploaded.
- **`DEVICE_KEY`**: Must match the registered device key in the backend.

### 2. USB Serial Bridge Key (`start.mjs`)
If you register a new device key, also update `$key` in `start.mjs`:

```powershell
$key = 'ydwqBbiuvYBzxTwyiEEnI5Ju6sGGayGGBxSsNfJssrc'
```

### 3. Backend Environment (`aquatrack-backend/.env`)
Check `aquatrack-backend/.env` (copy from `aquatrack-backend/.env.example` if missing):
- `DB_ENGINE=sqlite` is configured for local development with zero DB setup; switch to `postgres` and set `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` for PostgreSQL.
- `CORS_ALLOWED_ORIGINS` includes `http://localhost:5173,http://127.0.0.1:5173`.
- `DJANGO_ALLOWED_HOSTS=*` allows connections from the ESP32 over LAN.

### 4. Windows Firewall (if ESP32 gets connection refused / timeout)
- Ensure inbound TCP port `8000` is allowed on your active Windows network profile (e.g., `Public` when connected to a phone hotspot), and that no firewall rule blocks your `.venv` Python executable.
