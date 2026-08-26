# Drone Maintenance Assistant

Desktop Linux application for first-level drone fleet maintenance, inspections, battery tracking, maintenance tasks, faults/incidents, flight-log retrieval, shared flight-test data and operational reports.

## Current version

**0.4.0**

## Features

- Drone fleet registration
- Equipment / Hardware field for each drone
- Pre-flight inspection
- Post-flight inspection
- PASS / FAIL / N/A inspection results
- Automatic creation of maintenance issues from failed inspection items
- Battery register with battery ID, cycles, voltage, health and notes
- Maintenance task tracking with priority, status, due date and notes
- Fault / incident tracking with severity, description, corrective action and resolution status
- Fleet and maintenance reports
- TXT report export
- Flight Logs & Test Data window
- Flight-log retrieval from mounted folders, HTTP and FTP sources
- Local storage and tracking of retrieved flight logs
- Import and preview of multi-flight Drone Flight Test Reporter JSON data
- Grey application interface with black field text for readability
- Linux AppImage and portable archive builds through GitHub Actions

## Requirements for development

- Ubuntu/Linux x86_64
- Python 3.11+
- PySide6

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Run from source:

```bash
python3 main.py
```

## Linux release

The GitHub Actions workflow builds:

- `DroneMaintenanceAssistant-x86_64.AppImage`
- `DroneMaintenanceAssistant-linux-x86_64.tar.gz`

The AppImage can be made executable with:

```bash
chmod +x DroneMaintenanceAssistant-x86_64.AppImage
./DroneMaintenanceAssistant-x86_64.AppImage
```

## iPhone & iPad companion

There is no App Store build (this product is a Linux desktop app). An installable Safari Progressive Web App covers the same day-to-day maintenance workflows.

- **Standalone GitHub repo:** [TectiveJK/drone-maintenance-assistant-ios](https://github.com/TectiveJK/drone-maintenance-assistant-ios)
- A copy also lives in [`ios/`](ios/) in this repository for reference while developing both apps together.

```bash
# from this repo
./scripts/serve-ios.sh

# or from the dedicated iOS repo
git clone https://github.com/TectiveJK/drone-maintenance-assistant-ios.git
cd drone-maintenance-assistant-ios && ./scripts/serve-ios.sh
```

On the device (same Wi‑Fi), open the printed URL in **Safari**, then **Share → Add to Home Screen**. Full steps: [`ios/README.md`](ios/README.md).

## Project structure

- `main.py` — application entry point
- `app/main_window.py` — main user interface
- `app/database.py` — SQLite database and migrations
- `app/integrations.py` — flight-log retrieval and shared flight-test data integration
- `ios/` — iPhone / iPad Progressive Web App companion
- `.github/workflows/build-linux.yml` — Linux build workflow

## Data

The application uses SQLite for local data storage. Drone, inspection, battery, maintenance, incident, retrieved flight-log and imported flight-test records are stored locally unless the project is later extended with synchronization.

## Status

Active development. Current development includes integration with the Drone Flight Test Reporter and direct retrieval of flight logs from drone-connected network devices.
