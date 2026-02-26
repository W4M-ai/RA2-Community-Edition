from pathlib import Path

import pytest

from src.devices.manager import DeviceManager
from src.devices.models import Output, FanSpeed
from src.config import BridgeConfig
from src.lip.parser import LipEvent, LipEventType

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_integration_report.xml"


@pytest.fixture
def config():
    return BridgeConfig(repeater_host="10.10.0.237")


@pytest.fixture
def manager(config):
    return DeviceManager.from_xml(FIXTURE_PATH, config)


def test_manager_loads_devices(manager):
    assert len(manager.registry.all_outputs) == 4
    assert len(manager.registry.all_picos) == 1


def test_manager_update_output_level(manager):
    event = LipEvent(type=LipEventType.OUTPUT, device_id=14, action=1, value=75.0)
    changed = manager.handle_lip_event(event)
    assert changed is not None
    assert changed.id == 14
    assert changed.level == 75.0


def test_manager_update_fan_level(manager):
    event = LipEvent(type=LipEventType.OUTPUT, device_id=15, action=1, value=50.0)
    changed = manager.handle_lip_event(event)
    assert changed is not None
    assert changed.category == "fan"
    assert changed.level == 50.0


def test_manager_update_shade_level(manager):
    event = LipEvent(type=LipEventType.OUTPUT, device_id=54, action=1, value=100.0)
    changed = manager.handle_lip_event(event)
    assert changed.category == "shade"
    assert changed.level == 100.0


def test_manager_unknown_device_returns_none(manager):
    event = LipEvent(type=LipEventType.OUTPUT, device_id=999, action=1, value=50.0)
    changed = manager.handle_lip_event(event)
    assert changed is None


def test_manager_pico_event(manager):
    event = LipEvent(type=LipEventType.DEVICE, device_id=50, component=3, action=3)
    pico_event = manager.handle_pico_event(event)
    assert pico_event is not None
    assert pico_event["device_id"] == 50
    assert pico_event["name"] == "Kitchen Pico"
    assert pico_event["button"] == 3
    assert pico_event["engraving"] == "Top"
    assert pico_event["action"] == "press"


def test_manager_pico_release_event(manager):
    event = LipEvent(type=LipEventType.DEVICE, device_id=50, component=3, action=4)
    pico_event = manager.handle_pico_event(event)
    assert pico_event["action"] == "release"


def test_manager_unknown_pico_returns_none(manager):
    event = LipEvent(type=LipEventType.DEVICE, device_id=999, component=3, action=3)
    pico_event = manager.handle_pico_event(event)
    assert pico_event is None


def test_manager_discovery_payload(manager):
    payload = manager.discovery_payload()
    assert isinstance(payload, list)
    assert len(payload) == 5  # 4 outputs + 1 pico
    ids = {d["id"] for d in payload}
    assert 14 in ids
    assert 15 in ids
    assert 50 in ids
    assert 54 in ids


def test_manager_applies_config_overrides():
    config = BridgeConfig(
        repeater_host="10.10.0.237",
        device_overrides={14: {"name": "Kitchen Cans"}},
        exclude_devices=[55],
        include_areas=["Kitchen"],
    )
    manager = DeviceManager.from_xml(FIXTURE_PATH, config)
    assert manager.registry.get_output(14).name == "Kitchen Cans"
    assert manager.registry.get_output(55) is None
    assert manager.registry.get_output(54) is None
