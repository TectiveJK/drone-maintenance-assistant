# Drone Maintenance Assistant — iOS

This directory is a separate iPhone web app (PWA). It does **not** change the Linux desktop application.

## Install on iPhone

1. Open the published app in **Safari**:
   `https://tectivejk.github.io/drone-maintenance-assistant/`
2. Tap **Share**.
3. Tap **Add to Home Screen**.

After that it opens like an app and works offline. Data is stored on that iPhone only. Ethernet log retrieval stays on the Linux app.

To copy a report back to the computer, use **Share**, **Export PDF**, or **Export JSON**, then save the file into `~/DroneTestDay`.

## Ubuntu development

```bash
cd ios-app
npm install
npm run dev
```

Preview the production build on the local network (then open the printed URL in iPhone Safari):

```bash
npm run build
npm run preview -- --host
```

## iOS packaging

The project uses Capacitor. The native iOS project must be generated with Xcode on macOS:

```bash
npm install
npm run build
npx cap add ios
npx cap sync ios
npx cap open ios
```

## Current iOS features

- Drone fleet
- Pre-flight and post-flight inspections
- Batteries
- Maintenance tasks
- Faults / incidents
- Test-day report, share, print/PDF and JSON export
- Local draft persistence with `localStorage`
- Offline home-screen install

The Linux desktop application remains separate.
