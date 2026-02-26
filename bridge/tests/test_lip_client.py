import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.lip.client import LipClient
from src.config import BridgeConfig


@pytest.fixture
def config():
    return BridgeConfig(
        repeater_host="10.10.0.237",
        repeater_port=23,
        repeater_username="lutron",
        repeater_password="integration",
        heartbeat_interval=30,
        heartbeat_timeout=10,
        reconnect_min_delay=1,
        reconnect_max_delay=60,
    )


def test_lip_client_init(config):
    client = LipClient(config)
    assert client.connected is False


@pytest.mark.asyncio
async def test_lip_client_send_command(config):
    client = LipClient(config)
    writer = MagicMock()
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    client._writer = writer
    client._connected = True

    await client.send("#OUTPUT,14,1,75.00\r\n")
    writer.write.assert_called_once_with(b"#OUTPUT,14,1,75.00\r\n")
    writer.drain.assert_awaited_once()


@pytest.mark.asyncio
async def test_lip_client_send_when_disconnected(config):
    client = LipClient(config)
    await client.send("#OUTPUT,14,1,75.00\r\n")


def test_lip_client_backoff(config):
    client = LipClient(config)
    assert client._next_delay() == 1
    assert client._next_delay() == 2
    assert client._next_delay() == 4
    assert client._next_delay() == 8
    assert client._next_delay() == 16
    assert client._next_delay() == 32
    assert client._next_delay() == 60  # capped
    assert client._next_delay() == 60  # stays capped

    client._reset_delay()
    assert client._next_delay() == 1  # reset


@pytest.mark.asyncio
async def test_lip_client_event_callback(config):
    received = []

    async def on_event(event):
        received.append(event)

    client = LipClient(config, on_event=on_event)
    await client._handle_line("~OUTPUT,14,1,75.00")

    assert len(received) == 1
    assert received[0].device_id == 14
    assert received[0].value == 75.0
