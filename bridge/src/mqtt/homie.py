"""Homie v3.0.1 convention publisher for MQTT Hub auto-discovery.

Each RA2 output is published as its own Homie device so MQTT Hub can
discover and pair them individually.  Topic structure:

    homie/ra2-<category>-<id>/$homie        = 3.0.1
    homie/ra2-<category>-<id>/$name         = "<area> - <name>"
    homie/ra2-<category>-<id>/$state        = ready
    homie/ra2-<category>-<id>/$nodes        = main
    homie/ra2-<category>-<id>/main/$properties = on,dim  (varies by type)
"""

from __future__ import annotations

import logging
from typing import Callable, Awaitable

from src.devices.models import DeviceRegistry, Output

logger = logging.getLogger(__name__)

_PREFIX = "homie"
_NODE = "main"  # single node per device

# Output types that are non-dimmable
_NON_DIM_TYPES = {"NON_DIM", "NON_DIM_INC"}


def _device_topic(output: Output) -> str:
    """Build the Homie device base topic: e.g. 'homie/ra2-light-18'."""
    return f"{_PREFIX}/ra2-{output.category}-{output.id}"


def _build_device_msgs(output: Output) -> dict[str, str]:
    """Build all Homie messages for a single output as its own device."""
    base = _device_topic(output)
    prop_prefix = f"{base}/{_NODE}"
    msgs: dict[str, str] = {}

    # Device attributes
    msgs[f"{base}/$homie"] = "3.0.1"
    msgs[f"{base}/$name"] = f"{output.area} - {output.name}"
    msgs[f"{base}/$state"] = "init"
    msgs[f"{base}/$nodes"] = _NODE

    # Node attributes
    msgs[f"{prop_prefix}/$name"] = output.name
    msgs[f"{prop_prefix}/$type"] = output.category

    if output.category == "shade":
        msgs[f"{prop_prefix}/$properties"] = "position"
        msgs[f"{prop_prefix}/position"] = str(int(output.level))
        msgs[f"{prop_prefix}/position/$name"] = "Position"
        msgs[f"{prop_prefix}/position/$datatype"] = "integer"
        msgs[f"{prop_prefix}/position/$format"] = "0:100"
        msgs[f"{prop_prefix}/position/$unit"] = "%"
        msgs[f"{prop_prefix}/position/$settable"] = "true"
        msgs[f"{prop_prefix}/position/$retained"] = "true"
    elif output.output_type in _NON_DIM_TYPES:
        msgs[f"{prop_prefix}/$properties"] = "on"
        msgs[f"{prop_prefix}/on"] = "true" if output.level > 0 else "false"
        msgs[f"{prop_prefix}/on/$name"] = "Power"
        msgs[f"{prop_prefix}/on/$datatype"] = "boolean"
        msgs[f"{prop_prefix}/on/$settable"] = "true"
        msgs[f"{prop_prefix}/on/$retained"] = "true"
    else:
        # Dimmable lights and fans
        msgs[f"{prop_prefix}/$properties"] = "on,dim"
        msgs[f"{prop_prefix}/on"] = "true" if output.level > 0 else "false"
        msgs[f"{prop_prefix}/on/$name"] = "Power"
        msgs[f"{prop_prefix}/on/$datatype"] = "boolean"
        msgs[f"{prop_prefix}/on/$settable"] = "true"
        msgs[f"{prop_prefix}/on/$retained"] = "true"
        msgs[f"{prop_prefix}/dim"] = str(int(output.level))
        msgs[f"{prop_prefix}/dim/$name"] = "Brightness"
        msgs[f"{prop_prefix}/dim/$datatype"] = "integer"
        msgs[f"{prop_prefix}/dim/$format"] = "0:100"
        msgs[f"{prop_prefix}/dim/$unit"] = "%"
        msgs[f"{prop_prefix}/dim/$settable"] = "true"
        msgs[f"{prop_prefix}/dim/$retained"] = "true"

    # Final state
    msgs[f"{base}/$state"] = "ready"
    return msgs


SetCallback = Callable[[int, float | None], Awaitable[None]]


class HomiePublisher:
    """Publishes Homie v3.0.1 per-device tree and handles /set commands."""

    def __init__(self, registry: DeviceRegistry, on_set: SetCallback | None = None):
        self._registry = registry
        self._on_set = on_set

    def build_all_messages(self) -> dict[str, str]:
        """Build the full Homie message tree (topic -> payload), all retained."""
        msgs: dict[str, str] = {}
        for output in self._registry.all_outputs:
            msgs.update(_build_device_msgs(output))
        return msgs

    def build_state_update(self, output: Output) -> dict[str, str]:
        """Build Homie property updates for a single output that changed."""
        base = _device_topic(output)
        prop_prefix = f"{base}/{_NODE}"
        msgs: dict[str, str] = {}

        if output.category == "shade":
            msgs[f"{prop_prefix}/position"] = str(int(output.level))
        elif output.output_type in _NON_DIM_TYPES:
            msgs[f"{prop_prefix}/on"] = "true" if output.level > 0 else "false"
        else:
            msgs[f"{prop_prefix}/on"] = "true" if output.level > 0 else "false"
            msgs[f"{prop_prefix}/dim"] = str(int(output.level))

        return msgs

    async def handle_set(self, topic: str, payload: str) -> None:
        """Handle incoming homie/ra2-<cat>-<id>/main/<prop>/set commands."""
        if not self._on_set:
            return

        # Parse: homie/ra2-<cat>-<id>/main/<property>/set
        parts = topic.split("/")
        if len(parts) != 5 or parts[4] != "set":
            return

        device_base = parts[1]  # e.g. "ra2-light-18"
        prop = parts[3]         # e.g. "on", "dim", "position"

        # Extract device_id from device_base
        try:
            device_id = int(device_base.rsplit("-", 1)[1])
        except (ValueError, IndexError):
            logger.warning("Invalid Homie device ID: %s", device_base)
            return

        output = self._registry.get_output(device_id)
        if output is None:
            logger.warning("Homie set for unknown device %d", device_id)
            return

        if prop == "on":
            level = 100.0 if payload.lower() == "true" else 0.0
            logger.info("Homie set: device=%d prop=%s payload=%s -> level=%.1f", device_id, prop, payload, level)
            await self._on_set(device_id, level)
        elif prop in ("dim", "position"):
            try:
                level = float(payload)
            except ValueError:
                logger.warning("Invalid Homie value: %s", payload)
                return
            logger.info("Homie set: device=%d prop=%s payload=%s -> level=%.1f", device_id, prop, payload, level)
            await self._on_set(device_id, level)

    @staticmethod
    def set_topic_pattern() -> str:
        return f"{_PREFIX}/+/{_NODE}/+/set"

    @staticmethod
    def lwt_topic() -> str:
        """Not used for per-device model (each device has its own $state)."""
        return f"{_PREFIX}/ra2-bridge/$state"

    @staticmethod
    def lwt_payload() -> str:
        return "lost"

    def lwt_topics(self) -> dict[str, str]:
        """Build LWT messages for all devices (set $state to lost)."""
        msgs: dict[str, str] = {}
        for output in self._registry.all_outputs:
            base = _device_topic(output)
            msgs[f"{base}/$state"] = "lost"
        return msgs

    @staticmethod
    def is_homie_topic(topic: str) -> bool:
        """Check if a topic is a Homie /set command."""
        return topic.startswith(f"{_PREFIX}/ra2-")
