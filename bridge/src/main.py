from __future__ import annotations

import asyncio
import logging
import signal
from pathlib import Path

import aiohttp

from src.config import BridgeConfig, load_config
from src.devices.manager import DeviceManager
from src.lip.client import LipClient
from src.lip.commands import set_output_level, query_output_level
from src.lip.parser import LipEvent, LipEventType
from src.mqtt.client import MqttBridge
from src.mqtt.handler import MqttCommandHandler
from src.mqtt.homie import HomiePublisher
from src.setup.discovery import discover_repeater
from src.ws.server import WsServer

logger = logging.getLogger("ra2_bridge")

DEFAULT_CONFIG_PATH = "/app/config.yaml"
DEFAULT_XML_PATH = "/app/integration-report.xml"


class Bridge:
    def __init__(self, config: BridgeConfig, xml_path: Path | str | None = None):
        self._config = config
        self._device_manager = DeviceManager.from_xml(
            xml_path or DEFAULT_XML_PATH, config
        )
        self._lip = LipClient(config, on_event=self._on_lip_event)
        self._mqtt = MqttBridge(config, on_command=self._on_mqtt_command)
        self._command_handler = MqttCommandHandler(topic_prefix=config.mqtt_topic_prefix)
        self._homie = HomiePublisher(
            self._device_manager.registry,
            on_set=self._on_homie_set,
        )
        self._ws = WsServer(
            self._device_manager.registry,
            port=config.ws_port,
            on_command=self._on_ws_command,
        )

    async def _on_lip_event(self, event: LipEvent) -> None:
        if event.type == LipEventType.OUTPUT:
            output = self._device_manager.handle_lip_event(event)
            if output:
                await self._mqtt.publish_state(
                    output.category, output.id, output.to_state_dict()
                )
                # Update Homie property topics
                for topic, payload in self._homie.build_state_update(output).items():
                    await self._mqtt.publish(topic, payload, retain=True)
                # Push to WebSocket clients
                await self._ws.broadcast_state(output.id, output.level)
        elif event.type == LipEventType.DEVICE:
            pico_event = self._device_manager.handle_pico_event(event)
            if pico_event:
                await self._mqtt.publish_event("pico", event.device_id, pico_event)
                await self._ws.broadcast_pico(
                    event.device_id, pico_event["button"], pico_event["action"]
                )

    async def _on_homie_set(self, device_id: int, level: float) -> None:
        """Handle a Homie /set command by sending LIP output level."""
        await self._lip.send(set_output_level(device_id, level))

    async def _on_ws_command(self, device_id: int, level: float, fade: float | None) -> None:
        """Handle a command from the Homey WebSocket app."""
        logger.info("WS -> LIP: device=%d level=%.1f fade=%s", device_id, level, fade)
        await self._lip.send(set_output_level(device_id, level, fade))

    async def _on_mqtt_command(self, topic: str, payload: str) -> None:
        # Route Homie /set commands
        if HomiePublisher.is_homie_topic(topic):
            await self._homie.handle_set(topic, payload)
            return

        cmd = self._command_handler.parse_command(topic, payload)
        if cmd is None:
            return
        device_id = cmd["device_id"]

        if cmd["category"] == "scene":
            from src.lip.commands import press_button, release_button
            await self._lip.send(press_button(device_id, 1))
            await asyncio.sleep(0.1)
            await self._lip.send(release_button(device_id, 1))
            return

        if cmd.get("action") == "stop":
            await self._lip.send(f"#OUTPUT,{device_id},1\r\n")
            return

        level = cmd.get("level")
        if level is not None:
            fade = cmd.get("fade")
            await self._lip.send(set_output_level(device_id, level, fade))

    async def _query_all_states(self) -> None:
        for output in self._device_manager.registry.all_outputs:
            await self._lip.send(query_output_level(output.id))
            await asyncio.sleep(0.1)

    async def run(self) -> None:
        await self._ws.start()

        while True:
            try:
                await self._mqtt.connect()
                await self._mqtt.publish_discovery(self._device_manager.discovery_payload())

                # Publish Homie device tree for MQTT Hub auto-discovery
                for topic, payload in self._homie.build_all_messages().items():
                    await self._mqtt.publish(topic, payload, retain=True)
                logger.info("Published Homie device tree (%d outputs)", len(self._device_manager.registry.all_outputs))

                if not self._lip.connected:
                    await self._lip.connect()

                tasks = [
                    self._lip.listen(),
                    self._lip.heartbeat_loop(),
                    self._mqtt.subscribe_and_listen(
                        extra_topics=[HomiePublisher.set_topic_pattern()]
                    ),
                    self._query_all_states(),
                ]

                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Bridge error: %s, reconnecting in 5s...", exc)
                try:
                    await self._lip.disconnect()
                except Exception:
                    pass
                try:
                    await self._mqtt.disconnect()
                except Exception:
                    pass
                await asyncio.sleep(5)

        await self._shutdown()

    async def _shutdown(self) -> None:
        logger.info("Shutting down...")
        await self._ws.stop()
        for topic, payload in self._homie.lwt_topics().items():
            await self._mqtt.publish(topic, payload, retain=True)
        await self._lip.disconnect()
        await self._mqtt.disconnect()


async def fetch_xml(url: str, fallback_path: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    xml_content = await resp.text()
                    Path(fallback_path).write_text(xml_content)
                    logger.info("Fetched Integration Report from %s", url)
                    return fallback_path
    except Exception as exc:
        logger.warning("Failed to fetch XML from %s: %s", url, exc)

    if Path(fallback_path).exists():
        logger.info("Using local Integration Report at %s", fallback_path)
        return fallback_path

    raise FileNotFoundError(f"No Integration Report available at {url} or {fallback_path}")


async def main() -> None:
    config = load_config(DEFAULT_CONFIG_PATH)
    logging.basicConfig(
        level=getattr(logging, config.log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Auto-discover repeater if not configured
    if not config.repeater_host:
        discovered = await discover_repeater(port=config.repeater_port)
        if discovered:
            config.repeater_host = discovered
        else:
            raise RuntimeError(
                "No RA2 repeater found. Set RA2_HOST in your .env file."
            )

    xml_url = f"http://{config.repeater_host}/DbXmlInfo.xml"
    xml_path = await fetch_xml(xml_url, DEFAULT_XML_PATH)
    bridge = Bridge(config, xml_path=xml_path)
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(bridge._shutdown()))
    await bridge.run()


if __name__ == "__main__":
    asyncio.run(main())
