from __future__ import annotations

import json
import logging
from typing import Callable, Awaitable

import aiomqtt

from src.config import BridgeConfig

logger = logging.getLogger(__name__)

CommandCallback = Callable[[str, str], Awaitable[None]]


class MqttBridge:
    def __init__(self, config: BridgeConfig, on_command: CommandCallback | None = None):
        self._config = config
        self._on_command = on_command
        self._client: aiomqtt.Client | None = None

    def state_topic(self, category: str, device_id: int) -> str:
        return f"{self._config.mqtt_topic_prefix}/state/{category}/{device_id}"

    def event_topic(self, category: str, device_id: int) -> str:
        return f"{self._config.mqtt_topic_prefix}/event/{category}/{device_id}"

    def set_topic_pattern(self) -> str:
        return f"{self._config.mqtt_topic_prefix}/set/#"

    def status_topic(self) -> str:
        return f"{self._config.mqtt_topic_prefix}/status/bridge"

    def discovery_topic(self) -> str:
        return f"{self._config.mqtt_topic_prefix}/discovery/devices"

    async def connect(self) -> None:
        kwargs = {
            "hostname": self._config.mqtt_host,
            "port": self._config.mqtt_port,
        }
        if self._config.mqtt_username:
            kwargs["username"] = self._config.mqtt_username
            kwargs["password"] = self._config.mqtt_password

        self._client = aiomqtt.Client(
            **kwargs,
            will=aiomqtt.Will(
                topic=self.status_topic(),
                payload="offline",
                qos=1,
                retain=True,
            ),
        )
        await self._client.__aenter__()
        await self.publish(self.status_topic(), "online", retain=True)
        logger.info("Connected to MQTT broker at %s:%d", self._config.mqtt_host, self._config.mqtt_port)

    async def disconnect(self) -> None:
        if self._client:
            await self.publish(self.status_topic(), "offline", retain=True)
            await self._client.__aexit__(None, None, None)
            self._client = None
            logger.info("Disconnected from MQTT broker")

    async def publish(self, topic: str, payload: str | dict | list, retain: bool = False, qos: int = 1) -> None:
        if self._client is None:
            logger.warning("Cannot publish, not connected: %s", topic)
            return
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload)
        await self._client.publish(topic, payload, qos=qos, retain=retain)

    async def publish_state(self, category: str, device_id: int, state: dict) -> None:
        topic = self.state_topic(category, device_id)
        await self.publish(topic, state, retain=True)

    async def publish_event(self, category: str, device_id: int, event: dict) -> None:
        topic = self.event_topic(category, device_id)
        await self.publish(topic, event, retain=False)

    async def publish_discovery(self, devices: list[dict]) -> None:
        await self.publish(self.discovery_topic(), devices, retain=True)

    async def subscribe_and_listen(self, extra_topics: list[str] | None = None) -> None:
        if self._client is None:
            return
        await self._client.subscribe(self.set_topic_pattern(), qos=1)
        logger.info("Subscribed to %s", self.set_topic_pattern())
        for pattern in (extra_topics or []):
            await self._client.subscribe(pattern, qos=1)
            logger.info("Subscribed to %s", pattern)
        async for message in self._client.messages:
            topic = str(message.topic)
            payload = message.payload.decode() if message.payload else ""
            logger.info("MQTT recv: %s = %s", topic, payload[:100])
            if self._on_command:
                await self._on_command(topic, payload)
