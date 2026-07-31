import json
import paho.mqtt.client as mqtt


class HomeAssistantMQTT:

    def __init__(self, broker: str, port: int, user: str, password: str, lights: dict, blinds: dict, transport):
        self.broker = broker
        self.port = port
        self.lights = lights
        self.blinds = blinds
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
                "device": {
                    "identifiers": [f"mordomus_module_{dev_id}"],
                    "name": "Mordomus System",
                },
            }
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
                "device": {
                    "identifiers": [f"mordomus_module_{dev_id}"],
                    "name": "Mordomus System",
                },
            }
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
        for i in range(0, len(raw_bytes), 3):
            chunk = raw_bytes[i : i + 3]
            if len(chunk) == 3 and chunk[0] == 0xAA:
                dev_id, val = chunk[1], chunk[2]
                if dev_id in self.lights:
                    state = "ON" if val == 0x64 else "OFF"
                    self.client.publish(
                        f"mordomus/light/{dev_id}/state", state, retain=True
                    )
                elif dev_id in self.blinds:
                    self.client.publish(
                        f"mordomus/blind/{dev_id}/position", val, retain=True
                    )