'use strict';

const Homey = require('homey');

function dimToLevel(dim) {
  return Math.round(dim * 100);
}

function levelToDim(level) {
  const dim = level / 100;
  return Math.round(dim * 4) / 4;
}

class Ra2FanDevice extends Homey.Device {
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
          bridge.sendCommand(deviceId, dimToLevel(dim));
        } else {
          bridge.sendCommand(deviceId, 50);
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
    this.setCapabilityValue('dim', levelToDim(level)).catch(this.error);
  }

  async onDeleted() {
    this.log(`Deleted: ${this.getName()}`);
  }
}

module.exports = Ra2FanDevice;
