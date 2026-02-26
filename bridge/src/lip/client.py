from __future__ import annotations

import asyncio
import logging
from typing import Callable, Awaitable

from src.config import BridgeConfig
from src.lip.parser import parse_lip_response, LipEvent, LipEventType

logger = logging.getLogger(__name__)

EventCallback = Callable[[LipEvent], Awaitable[None]]


class LipClient:
    def __init__(self, config: BridgeConfig, on_event: EventCallback | None = None):
        self._config = config
        self._on_event = on_event
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._connected = False
        self._delay_exp = 0

    @property
    def connected(self) -> bool:
        return self._connected

    def _next_delay(self) -> int:
        delay = min(
            self._config.reconnect_min_delay * (2 ** self._delay_exp),
            self._config.reconnect_max_delay,
        )
        self._delay_exp += 1
        return delay

    def _reset_delay(self) -> None:
        self._delay_exp = 0

    async def connect(self) -> None:
        host = self._config.repeater_host
        port = self._config.repeater_port
        logger.info("Connecting to RA2 repeater at %s:%d", host, port)
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=10,
            )
        except (OSError, asyncio.TimeoutError) as exc:
            logger.error("Failed to connect to %s:%d: %s", host, port, exc)
            raise
        await self._login()
        self._connected = True
        self._reset_delay()
        logger.info("Connected and logged in to RA2 repeater")

    async def _login(self) -> None:
        data = await asyncio.wait_for(self._reader.readuntil(b"login: "), timeout=10)
        self._writer.write(f"{self._config.repeater_username}\r\n".encode())
        data = await asyncio.wait_for(self._reader.readuntil(b"password: "), timeout=10)
        self._writer.write(f"{self._config.repeater_password}\r\n".encode())
        data = await asyncio.wait_for(self._reader.readuntil(b"GNET>"), timeout=10)

    async def send(self, command: str) -> None:
        if not self._connected or self._writer is None:
            logger.warning("Cannot send command, not connected: %s", command.strip())
            return
        logger.info("LIP send: %s", command.strip())
        self._writer.write(command.encode())
        await self._writer.drain()

    async def _handle_line(self, line: str) -> None:
        stripped = line.strip()
        if not stripped:
            return
        # Repeater may combine GNET> prompts with responses on one line
        # e.g. "GNET> ~OUTPUT,217,1,0.00"
        for part in stripped.split("GNET>"):
            part = part.strip()
            if not part:
                continue
            logger.debug("LIP recv: %s", part)
            event = parse_lip_response(part)
            if event:
                logger.info("LIP event: %s id=%d action=%d val=%.2f", event.type.name, event.device_id, event.action, event.value)
                if self._on_event:
                    await self._on_event(event)

    async def listen(self) -> None:
        if not self._reader:
            return
        try:
            while self._connected:
                line = await asyncio.wait_for(
                    self._reader.readline(),
                    timeout=self._config.heartbeat_interval + self._config.heartbeat_timeout,
                )
                if not line:
                    logger.warning("Connection closed by repeater")
                    break
                await self._handle_line(line.decode("ascii", errors="replace"))
        except asyncio.TimeoutError:
            logger.warning("No data received, connection may be stale")
        except (ConnectionResetError, OSError) as exc:
            logger.error("Connection error: %s", exc)
        finally:
            self._connected = False

    async def heartbeat_loop(self) -> None:
        from src.lip.commands import heartbeat_command
        while self._connected:
            await asyncio.sleep(self._config.heartbeat_interval)
            if self._connected:
                logger.debug("Sending heartbeat")
                await self.send(heartbeat_command())

    async def disconnect(self) -> None:
        self._connected = False
        if self._writer:
            self._writer.close()
            self._writer = None
        self._reader = None
        logger.info("Disconnected from RA2 repeater")

    async def run_with_reconnect(self) -> None:
        while True:
            try:
                await self.connect()
                await asyncio.gather(self.listen(), self.heartbeat_loop())
            except Exception as exc:
                logger.error("LIP client error: %s", exc)
            self._connected = False
            delay = self._next_delay()
            logger.info("Reconnecting in %ds...", delay)
            await asyncio.sleep(delay)
