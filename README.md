# Drone Maintenance Assistant

Desktop Linux application for first-level drone fleet maintenance, inspections, battery tracking, maintenance tasks, faults/incidents, and operational reports.

## Current version

**0.3.0**

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

## Project structure

- `main.py` — application entry point
- `app/main_window.py` — main user interface
- `app/database.py` — SQLite database and migrations
- `app/inspection.py` — inspection functionality
- `app/battery.py` — battery functionality
- `app/maintenance.py` — maintenance functionality
- `app/reports.py` — reporting functionality
- `.github/workflows/build-linux.yml` — Linux build workflow

## Data

The application uses SQLite for local data storage. Drone, inspection, battery, maintenance and incident records are intended to remain local to the workstation unless the project is later extended with synchronization.

## Status

Active development. The current focus is expanding the operational modules and validating the Linux release on Ubuntu.
