'use strict';

const { EventEmitter } = require('events');
const WebSocket = require('ws');

class BridgeClient extends EventEmitter {
  constructor({ host, port, log, error }) {
    super();
    this._host = host;
    this._port = port;
    this._log = log || console.log;
    this._error = error || console.error;
    this._ws = null;
    this._reconnectDelay = 1000;
    this._maxReconnectDelay = 30000;
    this._shouldConnect = false;
    this._reconnectTimer = null;
    this._devices = new Map();
  }

  get connected() {
    return this._ws && this._ws.readyState === WebSocket.OPEN;
  }

  get devices() {
    return this._devices;
  }

  updateConfig({ host, port }) {
    const changed = host !== this._host || port !== this._port;
    this._host = host;
    this._port = port;
    if (changed && this._shouldConnect) {
      this._reconnect();
    }
  }

  connect() {
    this._shouldConnect = true;
    this._reconnectDelay = 1000;
    this._doConnect();
  }

  disconnect() {
    this._shouldConnect = false;
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
    if (this._ws) {
      this._ws.removeAllListeners();
      this._ws.close();
      this._ws = null;
    }
  }

  sendCommand(deviceId, level, fade = null) {
    if (!this.connected) return;
    const msg = { type: 'set_level', device_id: deviceId, level };
    if (fade != null) msg.fade = fade;
    this._ws.send(JSON.stringify(msg));
  }

  requestDevices() {
    if (!this.connected) return;
    this._ws.send(JSON.stringify({ type: 'get_devices' }));
  }

  _doConnect() {
    if (!this._shouldConnect || !this._host) return;

    const url = `ws://${this._host}:${this._port}/ws`;
    this._log(`Connecting to bridge at ${url}`);

    try {
      this._ws = new WebSocket(url);
    } catch (err) {
      this._error('WebSocket create error:', err.message);
      this._scheduleReconnect();
      return;
    }

    this._ws.on('open', () => {
      this._log('Connected to bridge');
      this._reconnectDelay = 1000;
      this.emit('connected');
    });

    this._ws.on('message', (raw) => {
      try {
        const msg = JSON.parse(raw.toString());
        this._handleMessage(msg);
      } catch (err) {
        this._error('Bad message:', err.message);
      }
    });

    this._ws.on('close', () => {
      this._log('Bridge connection closed');
      this._ws = null;
      this.emit('disconnected');
      this._scheduleReconnect();
    });

    this._ws.on('error', (err) => {
      this._error('WebSocket error:', err.message);
    });
  }

  _handleMessage(msg) {
    switch (msg.type) {
      case 'hello':
        this._log(`Bridge version ${msg.version}`);
        this.requestDevices();
        break;
      case 'devices':
        this._devices.clear();
        for (const d of msg.devices) {
          this._devices.set(d.id, d);
        }
        this._log(`Received ${msg.devices.length} devices`);
        this.emit('devices', msg.devices);
        // Push initial state for each device so Homey devices get their levels
        for (const d of msg.devices) {
          if (d.level != null) {
            this.emit('state', d.id, d.level);
          }
        }
        break;
      case 'state':
        this.emit('state', msg.device_id, msg.level);
        break;
      case 'pico':
        this.emit('pico', msg.device_id, msg.button, msg.action);
        break;
    }
  }

  _scheduleReconnect() {
    if (!this._shouldConnect) return;
    this._log(`Reconnecting in ${this._reconnectDelay / 1000}s...`);
    this._reconnectTimer = setTimeout(() => {
      this._reconnectTimer = null;
      this._doConnect();
    }, this._reconnectDelay);
    this._reconnectDelay = Math.min(this._reconnectDelay * 2, this._maxReconnectDelay);
  }

  _reconnect() {
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
    if (this._ws) {
      this._ws.close();
    } else {
      this._doConnect();
    }
  }
}

module.exports = BridgeClient;
