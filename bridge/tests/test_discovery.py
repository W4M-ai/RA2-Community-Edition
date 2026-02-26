from pathlib import Path

from src.devices.discovery import parse_integration_report
from src.devices.models import DeviceRegistry

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_integration_report.xml"


def test_parse_returns_registry():
    registry = parse_integration_report(FIXTURE_PATH)
    assert isinstance(registry, DeviceRegistry)


def test_parse_finds_all_outputs():
    registry = parse_integration_report(FIXTURE_PATH)
    assert len(registry.all_outputs) == 4  # Kitchen Main, Kitchen Fan, Theater Door Shade, Theater Downlights


def test_parse_finds_light():
    registry = parse_integration_report(FIXTURE_PATH)
    light = registry.get_output(14)
    assert light is not None
    assert light.name == "Kitchen Main"
    assert light.output_type == "INC"
    assert light.area == "Kitchen"
    assert light.category == "light"


def test_parse_finds_fan():
    registry = parse_integration_report(FIXTURE_PATH)
    fan = registry.get_output(15)
    assert fan is not None
    assert fan.name == "Kitchen Fan"
    assert fan.output_type == "CEILING_FAN_TYPE"
    assert fan.category == "fan"


def test_parse_finds_shade():
    registry = parse_integration_report(FIXTURE_PATH)
    shade = registry.get_output(54)
    assert shade is not None
    assert shade.name == "Theater Door Shade"
    assert shade.output_type == "SYSTEM_SHADE"
    assert shade.category == "shade"


def test_parse_finds_pico():
    registry = parse_integration_report(FIXTURE_PATH)
    pico = registry.get_pico(50)
    assert pico is not None
    assert pico.name == "Kitchen Pico"
    assert pico.area == "Kitchen"
    assert pico.num_buttons == 5
    assert pico.buttons[2] == "Center"
    assert pico.buttons[6] == "Lower"


def test_parse_deduplicates_by_id():
    registry = parse_integration_report(FIXTURE_PATH)
    ids = [o.id for o in registry.all_outputs]
    assert len(ids) == len(set(ids))


def test_parse_excludes_devices():
    registry = parse_integration_report(FIXTURE_PATH, exclude_devices=[14, 50])
    assert registry.get_output(14) is None
    assert registry.get_pico(50) is None
    assert registry.get_output(15) is not None


def test_parse_filters_areas():
    registry = parse_integration_report(FIXTURE_PATH, include_areas=["Kitchen"])
    assert registry.get_output(14) is not None
    assert registry.get_output(54) is None


def test_parse_applies_name_overrides():
    overrides = {14: {"name": "Kitchen Cans"}}
    registry = parse_integration_report(FIXTURE_PATH, device_overrides=overrides)
    assert registry.get_output(14).name == "Kitchen Cans"


def test_parse_real_integration_report():
    real_path = Path(__file__).parent.parent / "integration-report.xml"
    if not real_path.exists():
        import pytest
        pytest.skip("Real integration report not available")
    registry = parse_integration_report(real_path)
    assert len(registry.all_outputs) == 147
    assert len(registry.all_picos) == 18
    assert len(registry.lights) > 100
    assert len(registry.fans) == 14
    assert len(registry.shades) == 7
