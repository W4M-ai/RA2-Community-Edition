from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from src.devices.models import DeviceRegistry, Output, PicoRemote


def parse_integration_report(
    xml_path: Path | str,
    exclude_devices: list[int] | None = None,
    include_areas: list[str] | None = None,
    device_overrides: dict[int, dict] | None = None,
) -> DeviceRegistry:
    exclude_devices = set(exclude_devices or [])
    include_areas = set(include_areas) if include_areas else None
    device_overrides = device_overrides or {}

    tree = ET.parse(str(xml_path))
    root = tree.getroot()

    registry = DeviceRegistry()
    seen_output_ids: set[int] = set()
    seen_device_ids: set[int] = set()

    def parse_area(area_elem: ET.Element) -> None:
        area_name = area_elem.get("Name", "")

        if include_areas and area_name not in include_areas:
            for sub_area in area_elem.findall("Areas/Area"):
                parse_area(sub_area)
            return

        for output_elem in area_elem.findall("Outputs/Output"):
            integration_id = int(output_elem.get("IntegrationID", "0"))
            if integration_id in seen_output_ids or integration_id in exclude_devices:
                continue
            seen_output_ids.add(integration_id)

            name = output_elem.get("Name", "")
            output_type = output_elem.get("OutputType", "")

            if integration_id in device_overrides:
                name = device_overrides[integration_id].get("name", name)

            registry.add_output(Output(
                id=integration_id,
                name=name,
                output_type=output_type,
                area=area_name,
            ))

        for device_group in area_elem.findall("DeviceGroups/DeviceGroup"):
            for device_elem in device_group.findall("Devices/Device"):
                device_type = device_elem.get("DeviceType", "")
                integration_id = int(device_elem.get("IntegrationID", "0"))

                if integration_id in seen_device_ids or integration_id in exclude_devices:
                    continue
                seen_device_ids.add(integration_id)

                if device_type == "PICO_KEYPAD":
                    buttons: dict[int, str] = {}
                    for component in device_elem.findall("Components/Component"):
                        if component.get("ComponentType") == "BUTTON":
                            comp_num = int(component.get("ComponentNumber", "0"))
                            button = component.find("Button")
                            engraving = button.get("Engraving", "") if button is not None else ""
                            buttons[comp_num] = engraving

                    name = device_elem.get("Name", "")
                    if integration_id in device_overrides:
                        name = device_overrides[integration_id].get("name", name)

                    registry.add_pico(PicoRemote(
                        id=integration_id,
                        name=name,
                        area=area_name,
                        buttons=buttons,
                    ))

        for sub_area in area_elem.findall("Areas/Area"):
            parse_area(sub_area)

    for area in root.findall(".//Areas/Area"):
        parse_area(area)

    return registry
