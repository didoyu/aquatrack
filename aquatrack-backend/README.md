# AquaTrack Backend (Django + DRF)

Local-first REST API for the AquaTrack capstone: ESP32 sensor ingest, daily/weekly/monthly
consumption summaries, two-stage leak detection (24 h / 48 h), COWD tiered billing forecast,
alerts, device administration, and storage of the ML model comparison results.

> Status: written from the paper but **not yet run**. Expect to fix a small bug or two on first run;
> paste any error and it can be fixed quickly.

## 1. Install (Windows / macOS / Linux)

Install: **Python 3.11+**, **Git**, **VS Code**, and **PostgreSQL**.

```bash
cd aquatrack-backend
python -m venv .venv
# Windows (PowerShell):   .venv\Scripts\Activate.ps1
# Windows (cmd):          .venv\Scripts\activate.bat
# macOS / Linux:          source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Configure

```bash
copy .env.example .env      # Windows   (macOS/Linux: cp .env.example .env)
```
Edit `.env` and set a real `DJANGO_SECRET_KEY` and the password for your PostgreSQL user.

## 3. Create the database tables

Run **accounts first** (custom user model):

```bash
python manage.py makemigrations accounts monitoring detection billing
python manage.py migrate
python manage.py createsuperuser          # becomes role=admin
python manage.py seed_defaults            # loads the COWD rate schedule
```

## 4. Configure PostgreSQL

Create a database named `aquatrack` in pgAdmin 4. Set `DB_ENGINE=postgres` and the correct `DB_*`
connection values in `.env` (the default username is `postgres`), then run the migrations above.
To use SQLite instead, change `DB_ENGINE=sqlite` in `.env`.

## 5. Load simulated data and run

```bash
python manage.py simulate_data --days 5 --leak-hours 60 --detect
python manage.py runserver
```

- API docs (Swagger, try requests in the browser): http://127.0.0.1:8000/api/docs/
- Django admin: http://127.0.0.1:8000/admin/
- Demo logins created by `simulate_data`: `demo@aquatrack.local / demo12345` (homeowner),
  `maint@aquatrack.local / maint12345` (maintenance)

`--leak-hours 60` makes each simulated leak last 60 h so you can see Stage 1 (>=24 h) and Stage 2 (>=48 h).

## 6. Run the tests

```bash
python manage.py test
```
Includes the three billing examples from the paper (10 -> 218.40, 15 -> 371.15, 27 -> 746.85) and the
two-stage leak escalation.

## 7. Periodic job (offline detection, forecast refresh)

```bash
python manage.py run_periodic_tasks
```
Schedule every 5 minutes: cron on the Raspberry Pi, Task Scheduler on Windows.

## API overview

| Area | Endpoint |
|---|---|
| Auth | `POST /api/auth/register/` `login/` `refresh/`, `GET/PATCH /api/auth/me/`, `POST /api/auth/change-password/` |
| Households | `/api/households/`, `/{id}/dashboard/`, `/{id}/usage/?period=daily|weekly|monthly` |
| Readings | `GET /api/readings/?household=&start=&end=`, `/api/readings/latest/`, `/api/summaries/` |
| Leaks | `/api/leaks/`, `POST /api/leaks/{id}/inspect/` `resolve/` `false-alarm/` |
| Alerts | `/api/alerts/`, `POST /{id}/read/`, `POST read-all/`, `GET unread-count/` |
| Billing | `GET /api/billing/forecast/`, `/calculate/?cubic_meters=27`, `/rates/`, `/forecast/history/` |
| Devices (maintenance) | `/api/devices/`, `POST /{id}/regenerate-key/`, `/api/sensors/`, `/api/logs/` |
| ML study (maintenance) | `/api/ml/evaluations/`, `GET /api/ml/evaluations/comparison/` |
| ESP32 | `POST /api/ingest/readings/`, `POST /api/ingest/heartbeat/` (header `X-Device-Key`) |

Screens in the wireframes map to: Dashboard -> `dashboard/`, Usage History -> `usage/` + `readings/`,
Anomaly Detection -> `leaks/`, Warning Stage 1/2 -> `leaks/{id}` (has `recommended_steps`),
Billing -> `billing/forecast/`.

### ESP32 payload

Register a device (as maintenance) with `POST /api/devices/` `{ "household": 1, "device_name": "ESP32-01" }`.
The response contains `api_key` **once**. The ESP32 then sends:

```http
POST /api/ingest/readings/
X-Device-Key: <api_key>
Content-Type: application/json

{"timestamp": "2026-06-01T08:00:00+08:00", "flow_rate": 4.2, "water_volume": 1250.5,
 "pressure_level": 36.4, "sampling_interval": 60, "edge_flag": false}
```
For buffered data after reconnecting, send `{"readings": [ ... up to 1000 ... ]}`. Re-sending is safe
(duplicates are skipped).

## How the paper's rules are implemented

| Rule | Where |
|---|---|
| 1 timestamped readings | `monitoring.WaterReading`, `ingest/readings/` |
| 2 daily/weekly/monthly summaries | `monitoring/services/aggregation.py` |
| 3 labelled dataset (0/1) | `WaterReading.leak_label`, `simulate_data`, `export_dataset` |
| 4 Stage 1 at 24 h, Stage 2 at 48 h | `detection/services.py` (`STAGE1_HOURS`, `STAGE2_HOURS` in settings) |
| 5 alert details + inspection checklist | `AlertNotification.data`, `LeakDetection` serializer |
| 6 COWD tiered bill | `billing/services.py`, rates editable in Django admin |
| 7/8 local-only, LAN access | SQLite/PostgreSQL local; add the Pi IP to `DJANGO_ALLOWED_HOSTS` |
| 9 ESP32 edge flag | `edge_flag` -> early-warning alert |
| 11 offline buffering | duplicate-safe batch upload + offline detection in `run_periodic_tasks` |

## Plugging in your trained model

Edit `detection/ml_inference.py::predict_anomaly` (anomaly) and
`billing/services.py::predict_monthly_with_model` (forecast). Until then the server uses the ESP32 flag,
a continuous-flow rule, and a run-rate forecast. Export training data with:
`python manage.py export_dataset --household 1 --out dataset.csv`.
