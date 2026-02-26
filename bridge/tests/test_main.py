from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from src.main import Bridge
from src.config import BridgeConfig

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_integration_report.xml"


@pytest.fixture
def config():
    return BridgeConfig(
        repeater_host="10.10.0.237",
        mqtt_host="localhost",
        mqtt_port=1883,
    )


def test_bridge_init(config):
    bridge = Bridge(config, xml_path=FIXTURE_PATH)
    assert bridge._device_manager is not None
    assert len(bridge._device_manager.registry.all_outputs) == 4


@pytest.mark.asyncio
async def test_bridge_handle_lip_output_event(config):
    bridge = Bridge(config, xml_path=FIXTURE_PATH)
    bridge._mqtt = MagicMock()
    bridge._mqtt.publish_state = AsyncMock()
    bridge._mqtt.publish = AsyncMock()

    from src.lip.parser import LipEvent, LipEventType
    event = LipEvent(type=LipEventType.OUTPUT, device_id=14, action=1, value=75.0)
    await bridge._on_lip_event(event)

    bridge._mqtt.publish_state.assert_called_once()
    call_args = bridge._mqtt.publish_state.call_args
    assert call_args[0][0] == "light"  # INC output_type maps to "light" category
    assert call_args[0][1] == 14


@pytest.mark.asyncio
async def test_bridge_handle_lip_pico_event(config):
    bridge = Bridge(config, xml_path=FIXTURE_PATH)
    bridge._mqtt = MagicMock()
    bridge._mqtt.publish_event = AsyncMock()

    from src.lip.parser import LipEvent, LipEventType
    event = LipEvent(type=LipEventType.DEVICE, device_id=50, component=3, action=3)
    await bridge._on_lip_event(event)

    bridge._mqtt.publish_event.assert_called_once()
    call_args = bridge._mqtt.publish_event.call_args
    assert call_args[0][0] == "pico"
    assert call_args[0][1] == 50


@pytest.mark.asyncio
async def test_bridge_handle_mqtt_command(config):
    bridge = Bridge(config, xml_path=FIXTURE_PATH)
    bridge._lip = MagicMock()
    bridge._lip.send = AsyncMock()

    import json
    await bridge._on_mqtt_command("ra2/set/output/14", json.dumps({"level": 75}))

    bridge._lip.send.assert_called_once()
    cmd = bridge._lip.send.call_args[0][0]
    assert "#OUTPUT,14,1,75.00" in cmd
