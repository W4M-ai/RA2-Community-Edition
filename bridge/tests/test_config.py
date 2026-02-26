import os
from pathlib import Path
from unittest.mock import patch

from src.config import load_config, BridgeConfig


def test_load_config_defaults():
    config = load_config(config_path=None)
    assert config.repeater_host == ""
    assert config.repeater_port == 23
    assert config.repeater_username == "lutron"
    assert config.repeater_password == "integration"
    assert config.mqtt_host == "mosquitto"
    assert config.mqtt_port == 1883
    assert config.mqtt_topic_prefix == "ra2"
    assert config.heartbeat_interval == 30
    assert config.heartbeat_timeout == 10
    assert config.reconnect_min_delay == 1
    assert config.reconnect_max_delay == 60
    assert config.device_overrides == {}
    assert config.exclude_devices == []
    assert config.include_areas == []
    assert config.log_level == "INFO"


def test_load_config_from_yaml(tmp_path):
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text("""
repeater:
  host: 10.10.0.237
  port: 23
  username: lutron
  password: secret

mqtt:
  host: mybroker
  port: 8883
  topic_prefix: home/ra2

heartbeat:
  interval: 15
  timeout: 5

device_overrides:
  14:
    name: Kitchen Cans

exclude_devices: [99, 100]
include_areas: [Kitchen, Theater]

logging:
  level: DEBUG
""")
    config = load_config(config_path=str(yaml_file))
    assert config.repeater_host == "10.10.0.237"
    assert config.repeater_password == "secret"
    assert config.mqtt_host == "mybroker"
    assert config.mqtt_port == 8883
    assert config.mqtt_topic_prefix == "home/ra2"
    assert config.heartbeat_interval == 15
    assert config.heartbeat_timeout == 5
    assert config.device_overrides == {14: {"name": "Kitchen Cans"}}
    assert config.exclude_devices == [99, 100]
    assert config.include_areas == ["Kitchen", "Theater"]
    assert config.log_level == "DEBUG"


def test_load_config_env_overrides(tmp_path):
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text("""
repeater:
  host: 10.10.0.237
  password: yaml_pass
mqtt:
  host: yaml_broker
""")
    env = {
        "RA2_HOST": "10.10.1.100",
        "RA2_PASSWORD": "env_pass",
        "MQTT_HOST": "env_broker",
        "MQTT_PORT": "9999",
        "LOG_LEVEL": "WARNING",
    }
    with patch.dict(os.environ, env, clear=False):
        config = load_config(config_path=str(yaml_file))
    assert config.repeater_host == "10.10.1.100"
    assert config.repeater_password == "env_pass"
    assert config.mqtt_host == "env_broker"
    assert config.mqtt_port == 9999
    assert config.log_level == "WARNING"


def test_load_config_env_without_yaml():
    env = {
        "RA2_HOST": "10.10.0.237",
        "RA2_PASSWORD": "mypass",
        "MQTT_HOST": "localhost",
    }
    with patch.dict(os.environ, env, clear=False):
        config = load_config(config_path=None)
    assert config.repeater_host == "10.10.0.237"
    assert config.repeater_password == "mypass"
    assert config.mqtt_host == "localhost"
