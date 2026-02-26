# RA2 Community Edition

**Bridge your Lutron RadioRA2 system to Homey Pro** — full control of lights, fans, and shades from the Homey app with real-time state sync.

We built this to control our own RA2 system from Homey. It works great for us, so we're sharing it with the community. Fork it, make it your own, and enjoy.

**Found a bug?** [Open a GitHub issue](https://github.com/W4M-ai/RA2-Community-Edition/issues). **Want a feature?** PRs are welcome. No guarantees on response time — this is a passion project, not a product.

---

## How It Works

```
Lutron RA2 Repeater ←── LIP (telnet) ──→ RA2 Bridge (Docker)
                                              ├── WebSocket ──→ Homey App
                                              └── MQTT ──→ (optional)
```

The **bridge** connects to your RA2 repeater via Lutron's Integration Protocol (LIP), discovers all your devices from the Integration Report, and exposes them over WebSocket.

The **Homey app** connects to the bridge and lets you pair RA2 devices directly into Homey — no MQTT flows, no manual topic mapping, no virtual devices to configure.

---

## Prerequisites

- Lutron RadioRA2 system with a main repeater
- Homey Pro (any model running Homey v5+)
- A Docker host on the same network (NAS, Raspberry Pi, any Linux box)
- Integration access enabled on your RA2 repeater (default credentials: `lutron` / `integration`)

---

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/W4M-ai/RA2-Community-Edition.git
cd RA2-Community-Edition/bridge
cp .env.example .env
```

Edit `.env` if you know your repeater's IP. Or leave `RA2_HOST` blank — the bridge will auto-discover it.

### 2. Start the bridge

```bash
docker compose up -d
```

This starts two containers: the RA2 bridge and a Mosquitto MQTT broker. Check the logs:

```bash
docker compose logs -f ra2-bridge
```

You should see:
```
[INFO] Auto-discovery: Found RA2 repeater at 192.168.1.50
[INFO] Connected to RA2 repeater (147 devices discovered)
[INFO] WebSocket server listening on port 8080
```

### 3. Install the Homey app

Install **Lutron RA2 Bridge** from the Homey App Store (or sideload from the `homey-app/` directory).

### 4. Configure and pair

1. Open the app settings in Homey → enter your Docker host's IP address
2. Go to **Add Device** → **Lutron RA2 Bridge** → pick a device type
3. Select your devices from the list → **Add**

That's it. Your RA2 devices are now controllable from Homey.

---

## Supported Devices

| Device Type | Homey Controls | RA2 Output Types |
|-------------|---------------|-----------------|
| Dimmable Light | On/Off, Brightness | INC, ELV, MLV, AUTO_DETECT |
| Switch | On/Off | NON_DIM, NON_DIM_INC |
| Ceiling Fan | On/Off, Speed (4 levels) | CEILING_FAN_TYPE |
| Shade | Position (0-100%) | SYSTEM_SHADE |

---

## Configuration

### Basic (.env)

The `.env` file is all most users need. See `.env.example` for all options.

| Variable | Default | Description |
|----------|---------|-------------|
| `RA2_HOST` | *(auto-discover)* | Repeater IP address |
| `RA2_PORT` | `23` | Repeater telnet port |
| `RA2_USERNAME` | `lutron` | Repeater login |
| `RA2_PASSWORD` | `integration` | Repeater password |
| `MQTT_HOST` | `mosquitto` | MQTT broker hostname |
| `MQTT_PORT` | `1883` | MQTT broker port |
| `WS_PORT` | `8080` | WebSocket server port |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

### Advanced (config.yaml)

For power users who want device overrides, area filtering, or custom names. Copy `config.yaml.example` and mount it into the container.

```yaml
# Rename devices
device_overrides:
  14:
    name: "Kitchen Island Lights"

# Exclude specific device IDs
exclude_devices: [999]

# Only include specific areas (empty = all areas)
include_areas: ["Kitchen", "Master Bedroom"]
```

---

## Troubleshooting

<details>
<summary><strong>Bridge can't find my repeater</strong></summary>

Set `RA2_HOST` in your `.env` to the repeater's IP address. You can find it in your router's DHCP table or the Lutron software.

Make sure the Docker host is on the same network/VLAN as the repeater.
</details>

<details>
<summary><strong>Devices not appearing in Homey pairing</strong></summary>

1. Check that the bridge is running: `docker compose logs ra2-bridge`
2. Verify the bridge discovered devices (look for "devices discovered" in logs)
3. In the Homey app settings, confirm the bridge host IP is correct
4. Make sure port 8080 is accessible from Homey to your Docker host
</details>

<details>
<summary><strong>Commands work but state doesn't update</strong></summary>

The bridge queries all device states on startup. If a device was changed while the bridge was offline, restart it:

```bash
docker compose restart ra2-bridge
```
</details>

<details>
<summary><strong>WebSocket connection keeps dropping</strong></summary>

The Homey app auto-reconnects with exponential backoff. Check your network — the Docker host and Homey need stable LAN connectivity. Verify with:

```bash
curl http://<docker-host>:8080/api/devices
```
</details>

---

## Architecture

```
┌──────────────────┐     Telnet/LIP      ┌───────────────────────────────────┐
│   Lutron RA2     │ ◄──────────────────► │   RA2 Bridge (Python/Docker)     │
│   Main Repeater  │     Port 23          │                                   │
└──────────────────┘                      │   ┌─ LIP Client (telnet)         │
                                          │   ├─ Device Manager (state)       │
                                          │   ├─ WebSocket Server (:8080)     │
                                          │   ├─ MQTT Client (Homie v3)       │
                                          │   └─ Auto-Discovery               │
                                          └─────────┬──────────┬──────────────┘
                                                    │          │
                                          WebSocket │          │ MQTT
                                                    │          │
                                          ┌─────────▼───┐  ┌──▼──────────────┐
                                          │  Homey App  │  │  Mosquitto      │
                                          │  (4 drivers)│  │  MQTT Broker    │
                                          └─────────────┘  └─────────────────┘
```

### Bridge Modules

| Module | Purpose |
|--------|---------|
| `src/lip/` | LIP protocol: telnet client, parser, command builder |
| `src/devices/` | Device models, Integration Report XML parser, state manager |
| `src/mqtt/` | MQTT client, Homie v3 publisher, command handler |
| `src/ws/` | WebSocket server (aiohttp) for Homey app communication |
| `src/setup/` | Auto-discovery of RA2 repeaters on the network |
| `src/config.py` | Configuration from `.env` and `config.yaml` |
| `src/main.py` | Bridge orchestrator |

### WebSocket API

The Homey app communicates with the bridge over a simple JSON WebSocket protocol:

**Bridge → App:**
```json
{"type": "hello", "version": "1.0"}
{"type": "devices", "devices": [{"id": 14, "name": "Kitchen Main", "area": "Kitchen", "category": "light", "is_dimmable": true, "level": 75.0}]}
{"type": "state", "device_id": 14, "level": 75.0}
{"type": "pico", "device_id": 50, "button": 2, "action": "press"}
```

**App → Bridge:**
```json
{"type": "get_devices"}
{"type": "set_level", "device_id": 14, "level": 75.0}
{"type": "set_level", "device_id": 14, "level": 75.0, "fade": 2.0}
```

---

## Contributing

PRs are welcome! This project was built to solve our needs, and we'd love to see the community extend it.

Some ideas:
- Scene/phantom button support
- PICO remote → Homey Flow Card triggers
- Occupancy sensor integration
- Support for RadioRA3 / Caseta

Please open an issue before starting major work so we can discuss the approach.

---

## License

[MIT](LICENSE)
