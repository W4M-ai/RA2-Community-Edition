from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

# Output types that support dimming
_DIMMABLE_TYPES = {"INC", "ELV", "MLV", "AUTO_DETECT", "TU_WIRE"}

# Output type -> category mapping
_CATEGORY_MAP = {
    "CEILING_FAN_TYPE": "fan",
    "SYSTEM_SHADE": "shade",
}


class FanSpeed(Enum):
    OFF = (0, "off")
    LOW = (25, "low")
    MEDIUM = (50, "medium")
    MEDIUM_HIGH = (75, "medium-high")
    HIGH = (100, "high")

    def __init__(self, level: int, label: str):
        self._level = level
        self._label = label

    @property
    def level(self) -> int:
        return self._level

    @property
    def label(self) -> str:
        return self._label

    @classmethod
    def from_level(cls, level: float) -> FanSpeed:
        """Map a 0-100 level to the nearest fan speed."""
        thresholds = [
            (12.5, cls.OFF),
            (37.5, cls.LOW),
            (62.5, cls.MEDIUM),
            (87.5, cls.MEDIUM_HIGH),
        ]
        for threshold, speed in thresholds:
            if level < threshold:
                return speed
        return cls.HIGH

    @classmethod
    def from_name(cls, name: str) -> FanSpeed:
        """Map a speed name like 'low' or 'medium-high' to FanSpeed."""
        for member in cls:
            if member.label == name.lower():
                return member
        raise ValueError(f"Unknown fan speed: {name}")


@dataclass
class Output:
    id: int
    name: str
    output_type: str
    area: str
    level: float = 0.0

    @property
    def category(self) -> str:
        return _CATEGORY_MAP.get(self.output_type, "light")

    @property
    def is_dimmable(self) -> bool:
        return self.output_type in _DIMMABLE_TYPES

    def to_state_dict(self) -> dict:
        base = {
            "id": self.id,
            "name": self.name,
            "area": self.area,
            "type": self.output_type,
            "category": self.category,
            "level": self.level,
        }
        if self.category == "fan":
            base["speed"] = FanSpeed.from_level(self.level).label
        elif self.category == "shade":
            if self.level >= 100:
                base["state"] = "open"
            elif self.level <= 0:
                base["state"] = "closed"
            else:
                base["state"] = "partially_open"
        else:
            base["on"] = self.level > 0
        return base


@dataclass
class PicoRemote:
    id: int
    name: str
    area: str
    buttons: dict[int, str] = field(default_factory=dict)  # component_number -> engraving

    @property
    def num_buttons(self) -> int:
        return len(self.buttons)


@dataclass
class DeviceRegistry:
    _outputs: dict[int, Output] = field(default_factory=dict)
    _picos: dict[int, PicoRemote] = field(default_factory=dict)

    def add_output(self, output: Output) -> None:
        self._outputs[output.id] = output

    def add_pico(self, pico: PicoRemote) -> None:
        self._picos[pico.id] = pico

    def get_output(self, device_id: int) -> Output | None:
        return self._outputs.get(device_id)

    def get_pico(self, device_id: int) -> PicoRemote | None:
        return self._picos.get(device_id)

    @property
    def all_outputs(self) -> list[Output]:
        return list(self._outputs.values())

    @property
    def all_picos(self) -> list[PicoRemote]:
        return list(self._picos.values())

    @property
    def lights(self) -> list[Output]:
        return [o for o in self._outputs.values() if o.category == "light"]

    @property
    def fans(self) -> list[Output]:
        return [o for o in self._outputs.values() if o.category == "fan"]

    @property
    def shades(self) -> list[Output]:
        return [o for o in self._outputs.values() if o.category == "shade"]
