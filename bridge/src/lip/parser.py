from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class LipEventType(Enum):
    OUTPUT = auto()
    DEVICE = auto()
    SYSTEM = auto()
    PROMPT = auto()
    LOGIN = auto()
    PASSWORD = auto()


@dataclass
class LipEvent:
    type: LipEventType
    device_id: int = 0
    component: int = 0
    action: int = 0
    value: float = 0.0


def parse_lip_response(line: str) -> LipEvent | None:
    line = line.strip()
    if not line:
        return None

    if line.startswith("GNET>"):
        return LipEvent(type=LipEventType.PROMPT)
    if line.startswith("login:"):
        return LipEvent(type=LipEventType.LOGIN)
    if line.startswith("password:"):
        return LipEvent(type=LipEventType.PASSWORD)

    if line.startswith("~OUTPUT,"):
        parts = line[1:].split(",")
        if len(parts) >= 3:
            return LipEvent(
                type=LipEventType.OUTPUT,
                device_id=int(parts[1]),
                action=int(parts[2]),
                value=float(parts[3]) if len(parts) > 3 else 0.0,
            )

    if line.startswith("~DEVICE,"):
        parts = line[1:].split(",")
        if len(parts) >= 4:
            return LipEvent(
                type=LipEventType.DEVICE,
                device_id=int(parts[1]),
                component=int(parts[2]),
                action=int(parts[3]),
            )

    if line.startswith("~SYSTEM"):
        return LipEvent(type=LipEventType.SYSTEM)

    return None
