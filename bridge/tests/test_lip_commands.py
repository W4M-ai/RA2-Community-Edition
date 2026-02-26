from src.lip.commands import (
    set_output_level,
    query_output_level,
    press_button,
    release_button,
    heartbeat_command,
)


def test_set_output_level():
    assert set_output_level(14, 75.0) == "#OUTPUT,14,1,75.00\r\n"


def test_set_output_level_with_fade():
    assert set_output_level(14, 75.0, fade=2.0) == "#OUTPUT,14,1,75.00,2.00\r\n"


def test_set_output_level_zero():
    assert set_output_level(14, 0) == "#OUTPUT,14,1,0.00\r\n"


def test_set_output_level_hundred():
    assert set_output_level(14, 100) == "#OUTPUT,14,1,100.00\r\n"


def test_query_output_level():
    assert query_output_level(14) == "?OUTPUT,14,1\r\n"


def test_press_button():
    assert press_button(50, 3) == "#DEVICE,50,3,3\r\n"


def test_release_button():
    assert release_button(50, 3) == "#DEVICE,50,3,4\r\n"


def test_heartbeat():
    assert heartbeat_command() == "?SYSTEM,1\r\n"
