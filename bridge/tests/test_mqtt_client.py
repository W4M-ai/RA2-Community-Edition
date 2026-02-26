import pytest

from src.mqtt.client import MqttBridge
from src.config import BridgeConfig


@pytest.fixture
def config():
    return BridgeConfig(
        mqtt_host="localhost",
        mqtt_port=1883,
        mqtt_topic_prefix="ra2",
    )


def test_mqtt_bridge_init(config):
    bridge = MqttBridge(config)
    assert bridge._config.mqtt_topic_prefix == "ra2"


def test_mqtt_bridge_state_topic(config):
    bridge = MqttBridge(config)
    assert bridge.state_topic("output", 14) == "ra2/state/output/14"
    assert bridge.state_topic("fan", 15) == "ra2/state/fan/15"
    assert bridge.state_topic("shade", 54) == "ra2/state/shade/54"


def test_mqtt_bridge_event_topic(config):
    bridge = MqttBridge(config)
    assert bridge.event_topic("pico", 50) == "ra2/event/pico/50"


def test_mqtt_bridge_set_topic_pattern(config):
    bridge = MqttBridge(config)
    assert bridge.set_topic_pattern() == "ra2/set/#"


def test_mqtt_bridge_status_topic(config):
    bridge = MqttBridge(config)
    assert bridge.status_topic() == "ra2/status/bridge"


def test_mqtt_bridge_discovery_topic(config):
    bridge = MqttBridge(config)
    assert bridge.discovery_topic() == "ra2/discovery/devices"
