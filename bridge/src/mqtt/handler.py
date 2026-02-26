from __future__ import annotations

import json
import logging

from src.devices.models import FanSpeed

logger = logging.getLogger(__name__)

_SHADE_ACTIONS = {"open": 100.0, "close": 0.0}


class MqttCommandHandler:
    def __init__(self, topic_prefix: str = "ra2"):
        self._prefix = topic_prefix

    def parse_command(self, topic: str, payload: str) -> dict | None:
        set_prefix = f"{self._prefix}/set/"
        if not topic.startswith(set_prefix):
            return None
        remainder = topic[len(set_prefix):]
        parts = remainder.split("/", 1)
        if len(parts) != 2:
            return None
        category, device_id_str = parts
        try:
            device_id = int(device_id_str)
        except ValueError:
            return None
        try:
            data = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Invalid JSON payload on %s: %s", topic, payload)
            return None

        if category == "output":
            return self._parse_output_command(device_id, data)
        elif category == "fan":
            return self._parse_fan_command(device_id, data)
        elif category == "shade":
            return self._parse_shade_command(device_id, data)
        elif category == "scene":
            return self._parse_scene_command(device_id, data)
        return None

    def _parse_output_command(self, device_id: int, data: dict) -> dict:
        return {
            "device_id": device_id, "category": "output",
            "level": float(data.get("level", 0)),
            "fade": float(data["fade"]) if "fade" in data else None,
        }

    def _parse_fan_command(self, device_id: int, data: dict) -> dict:
        if "speed" in data:
            level = float(FanSpeed.from_name(data["speed"]).level)
        else:
            level = float(data.get("level", 0))
        return {"device_id": device_id, "category": "fan", "level": level, "fade": None}

    def _parse_shade_command(self, device_id: int, data: dict) -> dict:
        action = data.get("action")
        if action == "stop":
            return {"device_id": device_id, "category": "shade", "level": None, "action": "stop", "fade": None}
        if action in _SHADE_ACTIONS:
            level = _SHADE_ACTIONS[action]
        else:
            level = float(data.get("level", 0))
        return {"device_id": device_id, "category": "shade", "level": level, "fade": None}

    def _parse_scene_command(self, device_id: int, data: dict) -> dict:
        return {"device_id": device_id, "category": "scene", "action": data.get("action", "activate")}
