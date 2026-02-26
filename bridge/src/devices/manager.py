from __future__ import annotations

import logging
from pathlib import Path

from src.config import BridgeConfig
from src.devices.discovery import parse_integration_report
from src.devices.models import DeviceRegistry, Output
from src.lip.parser import LipEvent, LipEventType

logger = logging.getLogger(__name__)

_ACTION_PRESS = 3
_ACTION_RELEASE = 4


class DeviceManager:
    def __init__(self, registry: DeviceRegistry):
        self.registry = registry

    @classmethod
    def from_xml(cls, xml_path: Path | str, config: BridgeConfig) -> DeviceManager:
        registry = parse_integration_report(
            xml_path,
            exclude_devices=config.exclude_devices,
            include_areas=config.include_areas if config.include_areas else None,
            device_overrides=config.device_overrides if config.device_overrides else None,
        )
        logger.info(
            "Loaded %d outputs (%d lights, %d fans, %d shades) and %d PICOs",
            len(registry.all_outputs), len(registry.lights), len(registry.fans),
            len(registry.shades), len(registry.all_picos),
        )
        return cls(registry)

    def handle_lip_event(self, event: LipEvent) -> Output | None:
        if event.type != LipEventType.OUTPUT:
            return None
        # Only process action 1 (Set/Get Level); ignore fade metadata (29, 30, etc.)
        if event.action != 1:
            return None
        output = self.registry.get_output(event.device_id)
        if output is None:
            logger.debug("Received event for unknown output ID %d", event.device_id)
            return None
        output.level = event.value
        return output

    def handle_pico_event(self, event: LipEvent) -> dict | None:
        if event.type != LipEventType.DEVICE:
            return None
        pico = self.registry.get_pico(event.device_id)
        if pico is None:
            return None
        action = "press" if event.action == _ACTION_PRESS else "release"
        engraving = pico.buttons.get(event.component, "")
        return {
            "device_id": event.device_id,
            "name": pico.name,
            "area": pico.area,
            "button": event.component,
            "engraving": engraving,
            "action": action,
        }

    def discovery_payload(self) -> list[dict]:
        devices = []
        for output in self.registry.all_outputs:
            devices.append(output.to_state_dict())
        for pico in self.registry.all_picos:
            devices.append({
                "id": pico.id,
                "name": pico.name,
                "area": pico.area,
                "category": "pico",
                "num_buttons": pico.num_buttons,
                "buttons": {str(k): v for k, v in pico.buttons.items()},
            })
        return devices
