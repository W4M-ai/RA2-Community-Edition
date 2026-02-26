import pytest
from unittest.mock import AsyncMock

from src.devices.models import Output, DeviceRegistry
from src.mqtt.homie import HomiePublisher


@pytest.fixture
def registry():
    reg = DeviceRegistry()
    reg.add_output(Output(id=18, name="Fireplace Lights", output_type="INC", area="Master Bedroom"))
    reg.add_output(Output(id=19, name="Outlets", output_type="NON_DIM", area="Master Bedroom"))
    reg.add_output(Output(id=136, name="North Fan", output_type="CEILING_FAN_TYPE", area="Master Bedroom"))
    reg.add_output(Output(id=54, name="Theater Door Shade", output_type="SYSTEM_SHADE", area="Theater"))
    return reg


def test_build_all_messages_per_device(registry):
    pub = HomiePublisher(registry)
    msgs = pub.build_all_messages()
    # Each output is its own Homie device
    assert msgs["homie/ra2-light-18/$homie"] == "3.0.1"
    assert msgs["homie/ra2-light-18/$name"] == "Master Bedroom - Fireplace Lights"
    assert msgs["homie/ra2-light-18/$state"] == "ready"
    assert msgs["homie/ra2-light-18/$nodes"] == "main"
    assert msgs["homie/ra2-fan-136/$homie"] == "3.0.1"
    assert msgs["homie/ra2-shade-54/$homie"] == "3.0.1"
    # Old single-device structure should NOT exist
    assert "homie/ra2-bridge/$homie" not in msgs


def test_build_dimmable_light_node(registry):
    pub = HomiePublisher(registry)
    msgs = pub.build_all_messages()
    assert msgs["homie/ra2-light-18/main/$name"] == "Fireplace Lights"
    assert msgs["homie/ra2-light-18/main/$type"] == "light"
    assert msgs["homie/ra2-light-18/main/$properties"] == "on,dim"
    assert msgs["homie/ra2-light-18/main/on/$datatype"] == "boolean"
    assert msgs["homie/ra2-light-18/main/on/$settable"] == "true"
    assert msgs["homie/ra2-light-18/main/dim/$datatype"] == "integer"
    assert msgs["homie/ra2-light-18/main/dim/$format"] == "0:100"


def test_build_non_dim_light_node(registry):
    pub = HomiePublisher(registry)
    msgs = pub.build_all_messages()
    assert msgs["homie/ra2-light-19/main/$properties"] == "on"
    assert "homie/ra2-light-19/main/dim/$datatype" not in msgs


def test_build_fan_node(registry):
    pub = HomiePublisher(registry)
    msgs = pub.build_all_messages()
    assert msgs["homie/ra2-fan-136/main/$type"] == "fan"
    assert msgs["homie/ra2-fan-136/main/$properties"] == "on,dim"


def test_build_shade_node(registry):
    pub = HomiePublisher(registry)
    msgs = pub.build_all_messages()
    assert msgs["homie/ra2-shade-54/main/$type"] == "shade"
    assert msgs["homie/ra2-shade-54/main/$properties"] == "position"
    assert msgs["homie/ra2-shade-54/main/position/$datatype"] == "integer"


def test_state_update_dimmable(registry):
    pub = HomiePublisher(registry)
    output = registry.get_output(18)
    output.level = 75.0
    updates = pub.build_state_update(output)
    assert updates["homie/ra2-light-18/main/on"] == "true"
    assert updates["homie/ra2-light-18/main/dim"] == "75"


def test_state_update_off(registry):
    pub = HomiePublisher(registry)
    output = registry.get_output(18)
    output.level = 0.0
    updates = pub.build_state_update(output)
    assert updates["homie/ra2-light-18/main/on"] == "false"
    assert updates["homie/ra2-light-18/main/dim"] == "0"


def test_state_update_shade(registry):
    pub = HomiePublisher(registry)
    output = registry.get_output(54)
    output.level = 50.0
    updates = pub.build_state_update(output)
    assert updates["homie/ra2-shade-54/main/position"] == "50"


@pytest.mark.asyncio
async def test_handle_set_on():
    reg = DeviceRegistry()
    reg.add_output(Output(id=18, name="Test", output_type="INC", area="Test"))
    callback = AsyncMock()
    pub = HomiePublisher(reg, on_set=callback)

    await pub.handle_set("homie/ra2-light-18/main/on/set", "true")
    callback.assert_called_once_with(18, 100.0)


@pytest.mark.asyncio
async def test_handle_set_off():
    reg = DeviceRegistry()
    reg.add_output(Output(id=18, name="Test", output_type="INC", area="Test"))
    callback = AsyncMock()
    pub = HomiePublisher(reg, on_set=callback)

    await pub.handle_set("homie/ra2-light-18/main/on/set", "false")
    callback.assert_called_once_with(18, 0.0)


@pytest.mark.asyncio
async def test_handle_set_dim():
    reg = DeviceRegistry()
    reg.add_output(Output(id=18, name="Test", output_type="INC", area="Test"))
    callback = AsyncMock()
    pub = HomiePublisher(reg, on_set=callback)

    await pub.handle_set("homie/ra2-light-18/main/dim/set", "50")
    callback.assert_called_once_with(18, 50.0)


@pytest.mark.asyncio
async def test_handle_set_unknown_device():
    reg = DeviceRegistry()
    callback = AsyncMock()
    pub = HomiePublisher(reg, on_set=callback)

    await pub.handle_set("homie/ra2-light-999/main/on/set", "true")
    callback.assert_not_called()


def test_set_topic_pattern():
    assert HomiePublisher.set_topic_pattern() == "homie/+/main/+/set"


def test_lwt_topics(registry):
    pub = HomiePublisher(registry)
    lwts = pub.lwt_topics()
    assert lwts["homie/ra2-light-18/$state"] == "lost"
    assert lwts["homie/ra2-fan-136/$state"] == "lost"
    assert lwts["homie/ra2-shade-54/$state"] == "lost"


def test_is_homie_topic():
    assert HomiePublisher.is_homie_topic("homie/ra2-light-18/main/on/set") is True
    assert HomiePublisher.is_homie_topic("homie/ra2-shade-54/main/position/set") is True
    assert HomiePublisher.is_homie_topic("ra2/set/output/14") is False
