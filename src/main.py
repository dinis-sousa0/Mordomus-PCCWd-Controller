import time
from src.config import load_config
from src.mordomus import MordomusTransport
from src.mqtt_handler import HomeAssistantMQTT


def main():
    cfg = load_config()

    #extract configuration
    ws_ip = cfg.get("waveshare", {}).get("ip", "192.168.1.200") #fallback value
    ws_port = cfg.get("waveshare", {}).get("port", 4196) #fallback value

    mq_broker = cfg.get("mqtt", {}).get("broker", "localhost") #fallback value
    mq_port = cfg.get("mqtt", {}).get("port", 1883) #fallback value
    mq_user = cfg.get("mqtt", {}).get("username", "")
    mq_pass = cfg.get("mqtt", {}).get("password", "")

    lights = cfg.get("lights", {})
    blinds = cfg.get("blinds", {})

    #TCP Layer
    transport = MordomusTransport(ip=ws_ip, port=ws_port, inter_frame_delay=0.05) #delay between commands
    transport.connect()

    #MQTT Broker Layer
    mqtt_service = HomeAssistantMQTT(
        broker=mq_broker,
        port=mq_port,
        user=mq_user,
        password=mq_pass,
        lights=lights,
        blinds=blinds,
        transport=transport,
    )
    mqtt_service.start()

    #Main Thread Alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down Mordomus Bridge...")


if __name__ == "__main__":
    main()