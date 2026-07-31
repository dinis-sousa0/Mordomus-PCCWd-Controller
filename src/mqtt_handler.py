import json
import paho.mqtt.client as mqtt

ACTIONS = {
    0x01: "single_press",
    0x02: "double_press",
    0x03: "long_press"
}

MORDOMUS_GATEWAY_DEVICE = {
    "identifiers": ["mordomus_gateway_main"],
    "name": "Mordomus Domótica",
    "model": "PCCWd TCP Gateway",
    "manufacturer": "Mordomus",
}


class HomeAssistantMQTT:

    def __init__(self, broker: str, port: int, user: str, password: str, lights: dict, blinds: dict, inputs: dict, transport):
        self.broker = broker
        self.port = port
        self.lights = lights
        self.blinds = blinds
        self.inputs = inputs
        self.transport = transport

        self.client = mqtt.Client()
        if user and password:
            self.client.username_pw_set(user, password)

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

        # Register callback for TCP telemetry
        self.transport.on_telemetry_callback = self._handle_hardware_telemetry

    def start(self):
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()

    def _publish_discovery(self):
        print("[MQTT] Publishing Home Assistant Auto-Discovery entities...")

        # Discover Lights
        for dev_id, name in self.lights.items():
            if name.lower() == "blank":
                continue
            topic = f"homeassistant/light/mordomus_{dev_id}/config"
            payload = {
                "name": f"Luz {name}",
                "unique_id": f"mordomus_light_{dev_id}",
                "command_topic": f"mordomus/light/{dev_id}/set",
                "state_topic": f"mordomus/light/{dev_id}/state",
                "payload_on": "ON",
                "payload_off": "OFF",
                "device": MORDOMUS_GATEWAY_DEVICE,
            }
            self.client.publish(topic, "", retain=True) #purge old entities
            self.client.publish(topic, json.dumps(payload), retain=True)

        # Discover Blinds
        for dev_id, name in self.blinds.items():
            if name.lower() == "blank":
                continue
            topic = f"homeassistant/cover/mordomus_{dev_id}/config"
            payload = {
                "name": f"Persiana {name}",
                "unique_id": f"mordomus_blind_{dev_id}",
                "command_topic": f"mordomus/blind/{dev_id}/set",
                "position_topic": f"mordomus/blind/{dev_id}/position",
                "set_position_topic": f"mordomus/blind/{dev_id}/set_position",
                "position_open": 100,
                "position_closed": 0,
                "device": MORDOMUS_GATEWAY_DEVICE,
            }
            self.client.publish(topic, "", retain=True) #purge old entities
            self.client.publish(topic, json.dumps(payload), retain=True)

        # Discover Inputs/Switches
        for dev_id, name in self.inputs.items():
            if str(name).lower() == "blank":
                continue
            topic = f"homeassistant/event/mordomus_input_{dev_id}/config"
            payload = {
                "name": f"Interruptor {name}",
                "unique_id": f"mordomus_input_{dev_id}",
                "state_topic": f"mordomus/input/{dev_id}/event",
                "event_types": ["single_press", "double_press", "long_press"],
                "device": MORDOMUS_GATEWAY_DEVICE,
            }
            self.client.publish(topic, "", retain=True) #purge old entities
            self.client.publish(topic, json.dumps(payload), retain=True)

    def _on_connect(self, client, userdata, flags, rc):
        print(f"[MQTT] Connected to Broker (RC: {rc})")
        self._publish_discovery()
        self.client.subscribe("mordomus/light/+/set")
        self.client.subscribe("mordomus/blind/+/set")
        self.client.subscribe("mordomus/blind/+/set_position")

    def _on_message(self, client, userdata, msg):
        parts = msg.topic.split("/")
        device_type, dev_id, action = parts[1], int(parts[2]), parts[3]
        payload = msg.payload.decode("utf-8")

        val = 0x01
        if device_type == "light":
            val = 0x64 if payload == "ON" else 0x01
            # Optimistically update HA state
            self.client.publish(
                f"mordomus/light/{dev_id}/state", payload, retain=True
            )
        elif device_type == "blind":
            if action == "set":
                val = 0x64 if payload == "OPEN" else 0x01
            elif action == "set_position":
                val = max(1, min(100, int(payload)))
            self.client.publish(
                f"mordomus/blind/{dev_id}/position", val, retain=True
            )

        # Send via transport queue
        self.transport.send_command(dev_id, val)

    def _handle_hardware_telemetry(self, raw_bytes: bytes):
        """Parses byte frames pushed from Mordomus hardware to update HA."""
        # 5-byte Input frame: 0x49 0xAA [ID] [ACTION] 0x46
        if len(raw_bytes) == 5 and raw_bytes[0] == 0x49 and raw_bytes[1] == 0xAA and raw_bytes[4] == 0x46:
            dev_id = raw_bytes[2]
            action_code = raw_bytes[3]
            event_type = ACTIONS.get(action_code)

            if event_type and dev_id in self.inputs:
                print(f"[TCP IN] Input {dev_id} triggered: {event_type}")
                payload = json.dumps({"event_type": event_type})
                self.client.publish(f"mordomus/input/{dev_id}/event", payload)