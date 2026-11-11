import json
from types import SimpleNamespace

import pytest

from mqtt_handler import HomeAssistantMQTT


class FakeClient:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload=None, retain=False):
        self.published.append((topic, payload, retain))

    def last(self, topic):
        matches = [p for t, p, _ in self.published if t == topic]
        return matches[-1] if matches else None


class FakeTransport:
    def __init__(self):
        self.on_telemetry_callback = None
        self.sent = []

    def send_command(self, dev_id, val, meta=None):
        self.sent.append((dev_id, val))


@pytest.fixture
def bridge():
    transport = FakeTransport()
    handler = HomeAssistantMQTT(
        broker="localhost",
        port=1883,
        user="",
        password="",
        lights={3: "Sala", 4: "Cozinha"},
        blinds={1: "Quarto", 2: "blank"},
        inputs={10: "Entrada", 11: "Corredor"},
        mappings={
            10: {"single_press": 3, "double_press": [3, 4]},
            11: 4,  # integer shorthand: single_press only
        },
        transport=transport,
    )
    handler.client = FakeClient()
    return handler, transport


def send(handler, topic, payload):
    handler._on_message(None, None, SimpleNamespace(topic=topic, payload=payload.encode()))


def press(handler, input_id, action_code):
    handler._handle_hardware_telemetry(bytes([0x49, 0xAA, input_id, action_code, 0x46]))


# --- Lights -----------------------------------------------------------------


@pytest.mark.parametrize(("payload", "byte"), [("ON", 0x64), ("OFF", 0x01)])
def test_light_command(bridge, payload, byte):
    handler, transport = bridge
    send(handler, "mordomus/light/3/set", payload)

    assert transport.sent == [(3, byte)]
    assert handler.client.last("mordomus/light/3/state") == payload
    assert handler.light_states[3] == payload


# --- Blinds -----------------------------------------------------------------


@pytest.mark.parametrize(("payload", "byte", "position"), [("OPEN", 0x64, 100), ("CLOSE", 0x01, 0)])
def test_blind_open_close(bridge, payload, byte, position):
    handler, transport = bridge
    send(handler, "mordomus/blind/1/set", payload)

    assert transport.sent == [(1, byte)]
    assert handler.client.last("mordomus/blind/1/position") == position


def test_blind_stop_is_ignored(bridge):
    handler, transport = bridge
    send(handler, "mordomus/blind/1/set", "STOP")

    assert transport.sent == []
    assert handler.client.last("mordomus/blind/1/position") is None


@pytest.mark.parametrize(
    ("payload", "byte", "position"),
    [("50", 50, 50), ("0", 0x01, 0), ("1", 0x01, 0), ("100", 100, 100), ("150", 100, 100), ("-5", 0x01, 0)],
)
def test_blind_set_position_is_clamped(bridge, payload, byte, position):
    handler, transport = bridge
    send(handler, "mordomus/blind/1/set_position", payload)

    assert transport.sent == [(1, byte)]
    assert handler.client.last("mordomus/blind/1/position") == position


def test_blind_invalid_position_is_ignored(bridge):
    handler, transport = bridge
    send(handler, "mordomus/blind/1/set_position", "abc")

    assert transport.sent == []


# --- Discovery --------------------------------------------------------------


def test_discovery_hides_stop_and_skips_blank(bridge):
    handler, _ = bridge
    handler._publish_discovery()

    cover = json.loads(handler.client.last("homeassistant/cover/mordomus_1/config"))
    assert cover["payload_stop"] is None
    assert handler.client.last("homeassistant/cover/mordomus_2/config") is None


# --- Wall buttons -----------------------------------------------------------


def test_input_publishes_event(bridge):
    handler, _ = bridge
    press(handler, 10, 0x03)

    assert json.loads(handler.client.last("mordomus/input/10/event")) == {"event_type": "long_press"}


def test_input_mapping_toggles_light(bridge):
    handler, transport = bridge
    press(handler, 10, 0x01)
    assert handler.client.last("mordomus/light/3/state") == "ON"

    press(handler, 10, 0x01)
    assert handler.client.last("mordomus/light/3/state") == "OFF"
    assert transport.sent == [], "wall buttons drive the lights directly; the bridge only syncs state"


def test_input_mapping_to_multiple_lights(bridge):
    handler, _ = bridge
    press(handler, 10, 0x02)

    assert handler.light_states[3] == "ON"
    assert handler.light_states[4] == "ON"


def test_integer_mapping_only_applies_to_single_press(bridge):
    handler, _ = bridge
    press(handler, 11, 0x02)
    assert handler.light_states[4] == "OFF"

    press(handler, 11, 0x01)
    assert handler.light_states[4] == "ON"


def test_unknown_input_is_ignored(bridge):
    handler, _ = bridge
    press(handler, 99, 0x01)

    assert handler.client.published == []
