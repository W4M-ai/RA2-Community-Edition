'use strict';

const Homey = require('homey');

class Ra2FanDriver extends Homey.Driver {
  async onPairListDevices() {
    const bridge = this.homey.app.bridge;
    if (!bridge.connected) {
      throw new Error('Not connected to RA2 Bridge. Check app settings.');
    }

    bridge.requestDevices();
    const devices = await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('Timeout')), 5000);
      bridge.once('devices', (list) => { clearTimeout(timeout); resolve(list); });
    });

    return devices
      .filter(d => d.category === 'fan')
      .map(d => ({
        name: `${d.area} - ${d.name}`,
        data: { id: d.id },
        store: { area: d.area },
      }));
  }
}

module.exports = Ra2FanDriver;
