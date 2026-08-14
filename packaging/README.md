# Linux distribution

The project can be distributed as a portable Linux archive or an AppImage.

## Build locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --name DroneMaintenanceAssistant main.py
tar -czf DroneMaintenanceAssistant-linux-x86_64.tar.gz -C dist DroneMaintenanceAssistant
```

## GitHub downloadable release

Create and push a version tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

GitHub Actions will build the Linux x86_64 AppImage and portable archive and attach them to the release.
