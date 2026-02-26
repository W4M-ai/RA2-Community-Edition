Control your Lutron RadioRA2 lighting system directly from Homey.

RA2 Bridge connects your Homey to a Lutron RadioRA2 repeater, giving you control of lights, switches, shades, and ceiling fans. State changes sync in real-time so Homey always reflects the current state of your devices.

SUPPORTED DEVICES
- Dimmable lights (on/off + brightness)
- Non-dimmable switches (on/off)
- Window shades (position control)
- Ceiling fans (on/off + 4-speed control)

REQUIREMENTS
- Lutron RadioRA2 Main Repeater (RR-MAIN-REP-WH or similar)
- RA2 Bridge Docker container running on your local network
- Integration access enabled on your repeater

SETUP
1. Deploy the RA2 Bridge Docker container on a machine on your local network (Synology, QNAP, Raspberry Pi, etc.)
2. Install this app on your Homey
3. Open app settings and enter the IP address of the machine running the bridge
4. Add devices — the app will discover all RA2 devices from your repeater automatically

For setup instructions, Docker deployment guide, and source code visit:
https://github.com/W4M-ai/RA2-Community-Edition

This is a community project shared as-is. Bug reports and contributions welcome via GitHub Issues.
