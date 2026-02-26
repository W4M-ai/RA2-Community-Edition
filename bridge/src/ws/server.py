from __future__ import annotations

import asyncio
import json
import logging
from typing import Callable, Awaitable

from aiohttp import web

from src.devices.models import DeviceRegistry

logger = logging.getLogger(__name__)

CommandCallback = Callable[[int, float, float | None], Awaitable[None]]


class WsServer:
    def __init__(
        self,
        registry: DeviceRegistry,
        port: int = 8080,
        on_command: CommandCallback | None = None,
    ):
        self._registry = registry
        self._port = port
        self.on_command = on_command
        self._clients: set[web.WebSocketResponse] = set()
        self._app = web.Application()
        self._app.router.add_get("/ws", self._ws_handler)
        self._app.router.add_get("/api/devices", self._rest_devices)
        self._runner: web.AppRunner | None = None
        self._actual_port: int | None = None

    @property
    def port(self) -> int:
        return self._actual_port or self._port

    async def start(self) -> None:
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "0.0.0.0", self._port)
        await site.start()
        for sock in site._server.sockets:
            self._actual_port = sock.getsockname()[1]
            break
        logger.info("WebSocket server listening on port %d", self.port)

    async def stop(self) -> None:
        for ws in list(self._clients):
            await ws.close()
        self._clients.clear()
        if self._runner:
            await self._runner.cleanup()

    def _device_list(self) -> list[dict]:
        result = []
        for output in self._registry.all_outputs:
            result.append({
                "id": output.id,
                "name": output.name,
                "area": output.area,
                "category": output.category,
                "output_type": output.output_type,
                "is_dimmable": output.is_dimmable,
                "level": output.level,
            })
        return result

    async def _rest_devices(self, request: web.Request) -> web.Response:
        return web.json_response(self._device_list())

    async def _ws_handler(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._clients.add(ws)
        logger.info("WebSocket client connected (%d total)", len(self._clients))

        await ws.send_json({"type": "hello", "version": "1.0"})

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    await self._handle_message(ws, json.loads(msg.data))
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error("WS error: %s", ws.exception())
        finally:
            self._clients.discard(ws)
            logger.info("WebSocket client disconnected (%d total)", len(self._clients))

        return ws

    async def _handle_message(self, ws: web.WebSocketResponse, data: dict) -> None:
        msg_type = data.get("type")
        if msg_type == "get_devices":
            await ws.send_json({"type": "devices", "devices": self._device_list()})
        elif msg_type == "set_level":
            device_id = data["device_id"]
            level = float(data["level"])
            fade = data.get("fade")
            if fade is not None:
                fade = float(fade)
            if self.on_command:
                await self.on_command(device_id, level, fade)

    async def broadcast_state(self, device_id: int, level: float) -> None:
        msg = {"type": "state", "device_id": device_id, "level": level}
        dead = []
        for ws in self._clients:
            try:
                await ws.send_json(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._clients.discard(ws)

    async def broadcast_pico(self, device_id: int, button: int, action: str) -> None:
        msg = {"type": "pico", "device_id": device_id, "button": button, "action": action}
        dead = []
        for ws in self._clients:
            try:
                await ws.send_json(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._clients.discard(ws)
