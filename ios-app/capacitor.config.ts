import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.tective.dronemaintenanceassistant.ios',
  appName: 'Drone Maintenance Assistant',
  webDir: 'dist',
  bundledWebRuntime: false,
  ios: {
    contentInset: 'automatic'
  }
};

export default config;
