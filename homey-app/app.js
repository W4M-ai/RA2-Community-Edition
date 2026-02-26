'use strict';

const Homey = require('homey');
const BridgeClient = require('./lib/bridge-client');

class Ra2BridgeApp extends Homey.App {
  async onInit() {
    this.log('RA2 Bridge app starting...');

    const host = this.homey.settings.get('bridge_host') || '';
    const port = this.homey.settings.get('bridge_port') || 8080;

    this.bridge = new BridgeClient({
      host,
      port,
      log: (...args) => this.log(...args),
      error: (...args) => this.error(...args),
    });

    this.bridge.on('state', (deviceId, level) => {
      this._updateDevice(deviceId, level);
    });

    this.bridge.on('connected', () => {
      this.log('Bridge connected — requesting device states');
    });

    this.bridge.on('disconnected', () => {
      this.log('Bridge disconnected');
    });

    // Listen for settings changes
    this.homey.settings.on('set', (key) => {
      if (key === 'bridge_host' || key === 'bridge_port') {
        const newHost = this.homey.settings.get('bridge_host') || '';
        const newPort = this.homey.settings.get('bridge_port') || 8080;
        this.log(`Settings changed: ${newHost}:${newPort}`);
        if (newHost && !this.bridge.connected) {
          this.bridge.updateConfig({ host: newHost, port: newPort });
          this.bridge.connect();
        } else {
          this.bridge.updateConfig({ host: newHost, port: newPort });
        }
      }
    });

    if (host) {
      this.bridge.connect();
    } else {
      this.log('No bridge host configured — open app settings to configure');
    }
  }

  _updateDevice(deviceId, level) {
    const drivers = this.homey.drivers.getDrivers();
    for (const driver of Object.values(drivers)) {
      const devices = driver.getDevices();
      for (const device of devices) {
        if (device.getData().id === deviceId) {
          device.updateFromBridge(level);
          return;
        }
      }
    }
  }

  async onUninit() {
    if (this.bridge) {
      this.bridge.disconnect();
    }
  }
}

module.exports = Ra2BridgeApp;
