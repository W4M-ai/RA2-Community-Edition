from src.lip.parser import parse_lip_response, LipEvent, LipEventType


def test_parse_output_level_change():
    event = parse_lip_response("~OUTPUT,14,1,75.00")
    assert event is not None
    assert event.type == LipEventType.OUTPUT
    assert event.device_id == 14
    assert event.action == 1
    assert event.value == 75.0


def test_parse_output_off():
    event = parse_lip_response("~OUTPUT,14,1,0.00")
    assert event.type == LipEventType.OUTPUT
    assert event.device_id == 14
    assert event.value == 0.0


def test_parse_device_button_press():
    event = parse_lip_response("~DEVICE,50,3,3")
    assert event is not None
    assert event.type == LipEventType.DEVICE
    assert event.device_id == 50
    assert event.component == 3
    assert event.action == 3


def test_parse_device_button_release():
    event = parse_lip_response("~DEVICE,50,3,4")
    assert event.type == LipEventType.DEVICE
    assert event.device_id == 50
    assert event.component == 3
    assert event.action == 4


def test_parse_system_response():
    event = parse_lip_response("~SYSTEM,1")
    assert event is not None
    assert event.type == LipEventType.SYSTEM


def test_parse_gnet_prompt():
    event = parse_lip_response("GNET> ")
    assert event is not None
    assert event.type == LipEventType.PROMPT


def test_parse_login_prompt():
    event = parse_lip_response("login: ")
    assert event is not None
    assert event.type == LipEventType.LOGIN


def test_parse_password_prompt():
    event = parse_lip_response("password: ")
    assert event is not None
    assert event.type == LipEventType.PASSWORD


def test_parse_empty_line():
    event = parse_lip_response("")
    assert event is None


def test_parse_unknown_line():
    event = parse_lip_response("some random text")
    assert event is None


def test_parse_output_with_whitespace():
    event = parse_lip_response("~OUTPUT,14,1,75.00\r\n")
    assert event is not None
    assert event.device_id == 14
    assert event.value == 75.0


def test_parse_output_integer_level():
    event = parse_lip_response("~OUTPUT,14,1,100")
    assert event.value == 100.0
