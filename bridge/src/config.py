from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class BridgeConfig:
    repeater_host: str = ""
    repeater_port: int = 23
    repeater_username: str = "lutron"
    repeater_password: str = "integration"
    mqtt_host: str = "mosquitto"
    mqtt_port: int = 1883
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_topic_prefix: str = "ra2"
    heartbeat_interval: int = 30
    heartbeat_timeout: int = 10
    reconnect_min_delay: int = 1
    reconnect_max_delay: int = 60
    ws_port: int = 8080
    device_overrides: dict = field(default_factory=dict)
    exclude_devices: list[int] = field(default_factory=list)
    include_areas: list[str] = field(default_factory=list)
    log_level: str = "INFO"


def load_config(config_path: str | None = None) -> BridgeConfig:
    raw: dict = {}
    if config_path and Path(config_path).exists():
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}

    repeater = raw.get("repeater", {})
    mqtt = raw.get("mqtt", {})
    heartbeat = raw.get("heartbeat", {})
    reconnect = raw.get("reconnect", {})
    logging_cfg = raw.get("logging", {})

    raw_overrides = raw.get("device_overrides", {})
    device_overrides = {int(k): v for k, v in raw_overrides.items()} if raw_overrides else {}

    config = BridgeConfig(
        repeater_host=repeater.get("host", ""),
        repeater_port=repeater.get("port", 23),
        repeater_username=repeater.get("username", "lutron"),
        repeater_password=repeater.get("password", "integration"),
        mqtt_host=mqtt.get("host", "mosquitto"),
        mqtt_port=mqtt.get("port", 1883),
        mqtt_username=mqtt.get("username", ""),
        mqtt_password=mqtt.get("password", ""),
        mqtt_topic_prefix=mqtt.get("topic_prefix", "ra2"),
        heartbeat_interval=heartbeat.get("interval", 30),
        heartbeat_timeout=heartbeat.get("timeout", 10),
        reconnect_min_delay=reconnect.get("min_delay", 1),
        reconnect_max_delay=reconnect.get("max_delay", 60),
        ws_port=raw.get("ws", {}).get("port", 8080),
        device_overrides=device_overrides,
        exclude_devices=raw.get("exclude_devices", []),
        include_areas=raw.get("include_areas", []),
        log_level=logging_cfg.get("level", "INFO"),
    )

    env_map = {
        "RA2_HOST": ("repeater_host", str),
        "RA2_PORT": ("repeater_port", int),
        "RA2_USERNAME": ("repeater_username", str),
        "RA2_PASSWORD": ("repeater_password", str),
        "MQTT_HOST": ("mqtt_host", str),
        "MQTT_PORT": ("mqtt_port", int),
        "MQTT_USER": ("mqtt_username", str),
        "MQTT_PASSWORD": ("mqtt_password", str),
        "MQTT_TOPIC_PREFIX": ("mqtt_topic_prefix", str),
        "WS_PORT": ("ws_port", int),
        "LOG_LEVEL": ("log_level", str),
    }
    for env_var, (attr, type_fn) in env_map.items():
        val = os.environ.get(env_var)
        if val is not None:
            setattr(config, attr, type_fn(val))

    return config
