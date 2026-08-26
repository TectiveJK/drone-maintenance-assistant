# iOS companion (iPhone & iPad)

Apple does not allow packaging this Python/PySide desktop app for the App Store without a full native rewrite. Instead, this folder is a **Progressive Web App (PWA)** that mirrors the desktop workflows and can be pinned to the Home Screen.

**Dedicated repository:** [TectiveJK/drone-maintenance-assistant-ios](https://github.com/TectiveJK/drone-maintenance-assistant-ios) — prefer that repo for iOS-only work. This `ios/` folder is kept in sync as a convenience copy.

## What you get

- Dashboard, fleet, pre/post-flight inspections, batteries, tasks, incidents, and reports
- Works in Safari on iPhone and iPad (portrait and landscape)
- Offline-capable after the first load (service worker)
- Data stored locally in Safari on that device (not synced with the Linux SQLite database)

## Install on iPhone or iPad

1. On the computer that has this repository, start the local server:

```bash
./scripts/serve-ios.sh
```

2. Note the URL printed (for example `http://192.168.1.20:8765/`).
3. On your iPhone or iPad, join the **same Wi‑Fi network**.
4. Open **Safari** and go to that URL.
5. Tap **Share** → **Add to Home Screen** → **Add**.
6. Open **DroneMaint** from the Home Screen for a full-screen app-like experience.

> Use Safari. Third-party browsers on iOS do not support Add to Home Screen the same way.

## Develop / open on a computer

```bash
./scripts/serve-ios.sh
# then open http://127.0.0.1:8765/
```

Or open `ios/index.html` directly in a desktop browser for a quick look (service worker and Home Screen install need HTTP).

## Files

| Path | Role |
|------|------|
| `index.html` | App shell |
| `styles.css` | Mobile / iPad layout |
| `app.js` | UI + localStorage data |
| `manifest.webmanifest` | Home Screen metadata |
| `sw.js` | Offline cache |
| `icons/` | Touch icons |
