'use strict';

const Homey = require('homey');

class Ra2ShadeDevice extends Homey.Device {
  async onInit() {
    this.log(`Init: ${this.getName()} (RA2 ID ${this.getData().id})`);

    this.registerCapabilityListener('windowcoverings_set', async (value) => {
      const bridge = this.homey.app.bridge;
      bridge.sendCommand(this.getData().id, value * 100);
    });

    // Sync initial state from bridge if available
    const bridge = this.homey.app.bridge;
    const cached = bridge.devices.get(this.getData().id);
    if (cached && cached.level != null) {
      this.updateFromBridge(cached.level);
    }
  }

  updateFromBridge(level) {
    this.setCapabilityValue('windowcoverings_set', level / 100).catch(this.error);
  }

  async onDeleted() {
    this.log(`Deleted: ${this.getName()}`);
  }
}

module.exports = Ra2ShadeDevice;
