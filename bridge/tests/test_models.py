from src.devices.models import Output, PicoRemote, DeviceRegistry, FanSpeed


def test_output_light_category():
    output = Output(id=14, name="Kitchen Main", output_type="INC", area="Kitchen")
    assert output.category == "light"
    assert output.is_dimmable is True


def test_output_non_dim_category():
    output = Output(id=5, name="Floodlight", output_type="NON_DIM", area="Backyard")
    assert output.category == "light"
    assert output.is_dimmable is False


def test_output_fan_category():
    output = Output(id=15, name="Kitchen Fan", output_type="CEILING_FAN_TYPE", area="Kitchen")
    assert output.category == "fan"
    assert output.is_dimmable is False


def test_output_shade_category():
    output = Output(id=54, name="Theater Door Shade", output_type="SYSTEM_SHADE", area="Theater")
    assert output.category == "shade"
    assert output.is_dimmable is False


def test_output_default_level():
    output = Output(id=14, name="Kitchen Main", output_type="INC", area="Kitchen")
    assert output.level == 0.0


def test_fan_speed_from_level():
    assert FanSpeed.from_level(0) == FanSpeed.OFF
    assert FanSpeed.from_level(25) == FanSpeed.LOW
    assert FanSpeed.from_level(50) == FanSpeed.MEDIUM
    assert FanSpeed.from_level(75) == FanSpeed.MEDIUM_HIGH
    assert FanSpeed.from_level(100) == FanSpeed.HIGH


def test_fan_speed_from_level_rounds():
    assert FanSpeed.from_level(10) == FanSpeed.OFF
    assert FanSpeed.from_level(30) == FanSpeed.LOW
    assert FanSpeed.from_level(60) == FanSpeed.MEDIUM
    assert FanSpeed.from_level(90) == FanSpeed.HIGH


def test_fan_speed_to_level():
    assert FanSpeed.OFF.level == 0
    assert FanSpeed.LOW.level == 25
    assert FanSpeed.MEDIUM.level == 50
    assert FanSpeed.MEDIUM_HIGH.level == 75
    assert FanSpeed.HIGH.level == 100


def test_fan_speed_from_name():
    assert FanSpeed.from_name("off") == FanSpeed.OFF
    assert FanSpeed.from_name("low") == FanSpeed.LOW
    assert FanSpeed.from_name("medium") == FanSpeed.MEDIUM
    assert FanSpeed.from_name("medium-high") == FanSpeed.MEDIUM_HIGH
    assert FanSpeed.from_name("high") == FanSpeed.HIGH


def test_pico_remote():
    pico = PicoRemote(
        id=50, name="Kitchen Pico", area="Kitchen",
        buttons={2: "Center", 3: "Top", 4: "Middle", 5: "Raise", 6: "Lower"}
    )
    assert pico.num_buttons == 5
    assert pico.buttons[2] == "Center"


def test_device_registry():
    output = Output(id=14, name="Kitchen Main", output_type="INC", area="Kitchen")
    pico = PicoRemote(
        id=50, name="Kitchen Pico", area="Kitchen",
        buttons={2: "Center", 3: "Top", 4: "Middle", 5: "Raise", 6: "Lower"}
    )
    registry = DeviceRegistry()
    registry.add_output(output)
    registry.add_pico(pico)

    assert registry.get_output(14) is output
    assert registry.get_pico(50) is pico
    assert registry.get_output(999) is None
    assert len(registry.all_outputs) == 1
    assert len(registry.all_picos) == 1


def test_device_registry_outputs_by_category():
    light = Output(id=14, name="Kitchen Main", output_type="INC", area="Kitchen")
    fan = Output(id=15, name="Kitchen Fan", output_type="CEILING_FAN_TYPE", area="Kitchen")
    shade = Output(id=54, name="Shade", output_type="SYSTEM_SHADE", area="Theater")

    registry = DeviceRegistry()
    registry.add_output(light)
    registry.add_output(fan)
    registry.add_output(shade)

    assert len(registry.lights) == 1
    assert len(registry.fans) == 1
    assert len(registry.shades) == 1


def test_output_to_state_dict_light():
    output = Output(id=14, name="Kitchen Main", output_type="INC", area="Kitchen", level=75.0)
    state = output.to_state_dict()
    assert state == {
        "id": 14,
        "name": "Kitchen Main",
        "area": "Kitchen",
        "type": "INC",
        "category": "light",
        "level": 75.0,
        "on": True,
    }


def test_output_to_state_dict_fan():
    output = Output(id=15, name="Kitchen Fan", output_type="CEILING_FAN_TYPE", area="Kitchen", level=50.0)
    state = output.to_state_dict()
    assert state == {
        "id": 15,
        "name": "Kitchen Fan",
        "area": "Kitchen",
        "type": "CEILING_FAN_TYPE",
        "category": "fan",
        "level": 50.0,
        "speed": "medium",
    }


def test_output_to_state_dict_shade():
    output = Output(id=54, name="Shade", output_type="SYSTEM_SHADE", area="Theater", level=100.0)
    state = output.to_state_dict()
    assert state == {
        "id": 54,
        "name": "Shade",
        "area": "Theater",
        "type": "SYSTEM_SHADE",
        "category": "shade",
        "level": 100.0,
        "state": "open",
    }
