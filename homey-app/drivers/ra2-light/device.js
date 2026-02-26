'use strict';

const Homey = require('homey');

class Ra2LightDevice extends Homey.Device {
  async onInit() {
    this.log(`Init: ${this.getName()} (RA2 ID ${this.getData().id})`);

    this.registerMultipleCapabilityListener(
      ['onoff', 'dim'],
      async ({ onoff, dim }) => {
        const bridge = this.homey.app.bridge;
        const deviceId = this.getData().id;

        if (onoff === false) {
          bridge.sendCommand(deviceId, 0);
        } else if (dim !== undefined) {
          bridge.sendCommand(deviceId, dim * 100);
        } else {
          bridge.sendCommand(deviceId, 100);
        }
      },
      300,
    );

    // Sync initial state from bridge if available
    const bridge = this.homey.app.bridge;
    const cached = bridge.devices.get(this.getData().id);
    if (cached && cached.level != null) {
      this.updateFromBridge(cached.level);
    }
  }

  updateFromBridge(level) {
    this.setCapabilityValue('onoff', level > 0).catch(this.error);
    this.setCapabilityValue('dim', level / 100).catch(this.error);
  }

  async onDeleted() {
    this.log(`Deleted: ${this.getName()}`);
  }
}

module.exports = Ra2LightDevice;
