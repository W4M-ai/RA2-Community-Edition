import json

import pytest

from src.mqtt.handler import MqttCommandHandler
from src.devices.models import FanSpeed


@pytest.fixture
def handler():
    return MqttCommandHandler(topic_prefix="ra2")


def test_parse_set_output_level(handler):
    cmd = handler.parse_command("ra2/set/output/14", json.dumps({"level": 75}))
    assert cmd is not None
    assert cmd["device_id"] == 14
    assert cmd["category"] == "output"
    assert cmd["level"] == 75.0
    assert cmd["fade"] is None


def test_parse_set_output_with_fade(handler):
    cmd = handler.parse_command("ra2/set/output/14", json.dumps({"level": 75, "fade": 2}))
    assert cmd["level"] == 75.0
    assert cmd["fade"] == 2.0


def test_parse_set_fan_by_speed(handler):
    cmd = handler.parse_command("ra2/set/fan/15", json.dumps({"speed": "low"}))
    assert cmd is not None
    assert cmd["device_id"] == 15
    assert cmd["category"] == "fan"
    assert cmd["level"] == 25.0


def test_parse_set_fan_by_level(handler):
    cmd = handler.parse_command("ra2/set/fan/15", json.dumps({"level": 50}))
    assert cmd["level"] == 50.0


def test_parse_set_shade_level(handler):
    cmd = handler.parse_command("ra2/set/shade/54", json.dumps({"level": 50}))
    assert cmd is not None
    assert cmd["device_id"] == 54
    assert cmd["category"] == "shade"
    assert cmd["level"] == 50.0


def test_parse_set_shade_action_open(handler):
    cmd = handler.parse_command("ra2/set/shade/54", json.dumps({"action": "open"}))
    assert cmd["level"] == 100.0


def test_parse_set_shade_action_close(handler):
    cmd = handler.parse_command("ra2/set/shade/54", json.dumps({"action": "close"}))
    assert cmd["level"] == 0.0


def test_parse_set_shade_action_stop(handler):
    cmd = handler.parse_command("ra2/set/shade/54", json.dumps({"action": "stop"}))
    assert cmd["action"] == "stop"
    assert cmd["level"] is None


def test_parse_scene_activate(handler):
    cmd = handler.parse_command("ra2/set/scene/100", json.dumps({"action": "activate"}))
    assert cmd is not None
    assert cmd["category"] == "scene"
    assert cmd["device_id"] == 100


def test_parse_unknown_topic(handler):
    cmd = handler.parse_command("ra2/state/output/14", json.dumps({"level": 75}))
    assert cmd is None


def test_parse_invalid_json(handler):
    cmd = handler.parse_command("ra2/set/output/14", "not json")
    assert cmd is None


def test_parse_wrong_prefix(handler):
    cmd = handler.parse_command("home/set/output/14", json.dumps({"level": 75}))
    assert cmd is None
