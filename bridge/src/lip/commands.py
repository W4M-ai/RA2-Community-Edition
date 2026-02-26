def set_output_level(device_id: int, level: float, fade: float | None = None) -> str:
    if fade is not None:
        return f"#OUTPUT,{device_id},1,{level:.2f},{fade:.2f}\r\n"
    return f"#OUTPUT,{device_id},1,{level:.2f}\r\n"


def query_output_level(device_id: int) -> str:
    return f"?OUTPUT,{device_id},1\r\n"


def press_button(device_id: int, component: int) -> str:
    return f"#DEVICE,{device_id},{component},3\r\n"


def release_button(device_id: int, component: int) -> str:
    return f"#DEVICE,{device_id},{component},4\r\n"


def heartbeat_command() -> str:
    return "?SYSTEM,1\r\n"
