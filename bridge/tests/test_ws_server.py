import asyncio
import json
import pytest
import aiohttp

from src.devices.models import Output, DeviceRegistry
from src.ws.server import WsServer


@pytest.fixture
def registry():
    reg = DeviceRegistry()
    reg.add_output(Output(id=14, name="Kitchen Main", output_type="INC", area="Kitchen", level=75.0))
    reg.add_output(Output(id=15, name="Kitchen Fan", output_type="CEILING_FAN_TYPE", area="Kitchen", level=50.0))
    reg.add_output(Output(id=20, name="Hall Light", output_type="NON_DIM", area="Hall", level=0.0))
    reg.add_output(Output(id=54, name="Theater Shade", output_type="SYSTEM_SHADE", area="Theater", level=100.0))
    return reg


@pytest.fixture
async def ws_server(registry):
    server = WsServer(registry, port=0)
    await server.start()
    yield server
    await server.stop()


async def test_hello_on_connect(ws_server):
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(f"http://localhost:{ws_server.port}/ws") as ws:
            msg = await ws.receive_json()
            assert msg["type"] == "hello"
            assert msg["version"] == "1.0"


async def test_get_devices(ws_server):
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(f"http://localhost:{ws_server.port}/ws") as ws:
            await ws.receive_json()  # hello
            await ws.send_json({"type": "get_devices"})
            msg = await ws.receive_json()
            assert msg["type"] == "devices"
            assert len(msg["devices"]) == 4
            kitchen = next(d for d in msg["devices"] if d["id"] == 14)
            assert kitchen["name"] == "Kitchen Main"
            assert kitchen["category"] == "light"
            assert kitchen["is_dimmable"] is True
            assert kitchen["level"] == 75.0


async def test_set_level_callback(ws_server):
    received = []

    async def handler(did, lvl, fade):
        received.append((did, lvl, fade))

    ws_server.on_command = handler

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(f"http://localhost:{ws_server.port}/ws") as ws:
            await ws.receive_json()  # hello
            await ws.send_json({"type": "set_level", "device_id": 14, "level": 50.0})
            await asyncio.sleep(0.1)
            assert received == [(14, 50.0, None)]


async def test_set_level_with_fade(ws_server):
    received = []

    async def handler(did, lvl, fade):
        received.append((did, lvl, fade))

    ws_server.on_command = handler

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(f"http://localhost:{ws_server.port}/ws") as ws:
            await ws.receive_json()
            await ws.send_json({"type": "set_level", "device_id": 14, "level": 75.0, "fade": 2.0})
            await asyncio.sleep(0.1)
            assert received == [(14, 75.0, 2.0)]


async def test_broadcast_state(ws_server):
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(f"http://localhost:{ws_server.port}/ws") as ws:
            await ws.receive_json()  # hello
            await ws_server.broadcast_state(14, 80.0)
            msg = await ws.receive_json()
            assert msg == {"type": "state", "device_id": 14, "level": 80.0}


async def test_broadcast_pico(ws_server):
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(f"http://localhost:{ws_server.port}/ws") as ws:
            await ws.receive_json()  # hello
            await ws_server.broadcast_pico(50, 2, "press")
            msg = await ws.receive_json()
            assert msg == {"type": "pico", "device_id": 50, "button": 2, "action": "press"}


async def test_rest_devices_endpoint(ws_server):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://localhost:{ws_server.port}/api/devices") as resp:
            assert resp.status == 200
            data = await resp.json()
            assert len(data) == 4
            fan = next(d for d in data if d["id"] == 15)
            assert fan["category"] == "fan"
            shade = next(d for d in data if d["id"] == 54)
            assert shade["category"] == "shade"


async def test_multiple_clients_broadcast(ws_server):
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(f"http://localhost:{ws_server.port}/ws") as ws1:
            async with session.ws_connect(f"http://localhost:{ws_server.port}/ws") as ws2:
                await ws1.receive_json()  # hello
                await ws2.receive_json()  # hello
                await ws_server.broadcast_state(14, 60.0)
                msg1 = await ws1.receive_json()
                msg2 = await ws2.receive_json()
                assert msg1["level"] == 60.0
                assert msg2["level"] == 60.0
