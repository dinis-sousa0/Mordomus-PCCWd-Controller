import csv
import os
import yaml

ACTION_MAP = {
    "1": "single_press",
    "2": "double_press",
    "3": "long_press"
}

# Base config template used if no config.yaml exists
DEFAULT_CONFIG = {
    "waveshare": {
        "ip": "192.168.1.200",
        "port": 4196
    },
    "mqtt": {
        "broker": "localhost",
        "port": 1883,
        "username": "",
        "password": ""
    },
    "blinds": {},
    "lights": {},
    "inputs": {},
    "mappings": {}
}

def prompt_val(label, default_val):
    #help prompt if needed
    val = input(f"Enter {label} [{default_val}]: ").strip()
    return val if val != "" else default_val

def convert_csv_to_yaml(
        filepath_input="mods_input.csv",
        filepath_output="mods_output.csv",
        filepath_func="mods_input_func.csv"
        ):

    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PARENT_DIR = os.path.dirname(SCRIPT_DIR)
    DEFAULT_OUTPUT = os.path.join(PARENT_DIR, "config.yaml")
    # Load existing config.yaml to preserve light/blind definitions if present
    base_config = DEFAULT_CONFIG.copy()
    if os.path.exists(DEFAULT_OUTPUT):
        try:
            with open(DEFAULT_OUTPUT, "r", encoding="utf-8") as f:
                existing = yaml.safe_load(f)
                if isinstance(existing, dict):
                    base_config.update(existing)
        except Exception as e:
            print(f"[WARNING] Could not read existing {DEFAULT_OUTPUT}, using default template: {e}")

    ws_curr = base_config.get("waveshare", DEFAULT_CONFIG["waveshare"])
    mq_curr = base_config.get("mqtt", DEFAULT_CONFIG["mqtt"])

    # 2. Prompt for Waveshare & MQTT settings
    print("\n--- Network & Gateway Configuration ---")
    ws_ip = prompt_val("Waveshare IP", ws_curr.get("ip", "192.168.1.200"))
    ws_port = prompt_val("Waveshare Port", ws_curr.get("port", 4196))

    print("\n--- MQTT Broker Configuration ---")
    mq_broker = prompt_val("MQTT Broker Host", mq_curr.get("broker", "localhost"))
    mq_port = prompt_val("MQTT Port", mq_curr.get("port", 1883))
    mq_user = prompt_val("MQTT Username", mq_curr.get("username", ""))
    mq_pass = prompt_val("MQTT Password", mq_curr.get("password", ""))

    # Write network configuration back to dictionary
    base_config["waveshare"] = {
        "ip": ws_ip,
        "port": int(ws_port) if str(ws_port).isdigit() else ws_port
    }
    base_config["mqtt"] = {
        "broker": mq_broker,
        "port": int(mq_port) if str(mq_port).isdigit() else mq_port,
        "username": mq_user,
        "password": mq_pass
    }


    prompt_input = input(f"Enter the input CSV file name [{filepath_input}]: ").strip()
    prompt_output = input(f"Enter the input functions CSV file name [{filepath_output}]: ").strip()
    prompt_func = input(f"Enter the input functions CSV file name [{filepath_func}]: ").strip()
    if prompt_input :
        filepath_input = prompt_input
    if prompt_output:
        filepath_output = prompt_output
    if prompt_func:
        filepath_func = prompt_func

    lights = {}
    blinds= {}
    inputs = {}
    mappings = {}

    try:
        with open(filepath_input, mode="r", encoding="iso-8859-1") as f:
            reader = csv.DictReader(f, delimiter=";")
            
            for row in reader:
                #skip useless columns
                if row.get("Estado")!="True":
                    continue

                raw_adde = row["ADDE"].strip()
                raw_desc = row["Descricao"].strip()

                if not raw_adde.isdigit() or not raw_desc:
                    continue

                inp_id = int(raw_adde)

                inputs[inp_id] = raw_desc

    except FileNotFoundError:
        print(f"[ERROR] Could not find CSV file '{filepath_input}'.")
        return


    try:
        with open(filepath_output, mode="r", encoding="iso-8859-1") as f:
            reader = csv.DictReader(f, delimiter=";")
            
            for row in reader:
                #skip useless columns
                if row.get("Estado")!="True":
                    continue

                raw_adde = row["ADDE"].strip()
                raw_desc = row["Descricao"].strip()

                if not raw_adde.isdigit() or not raw_desc:
                    continue

                inp_id = int(raw_adde)

                if row.get("Tipo") == "1":
                    lights[inp_id] = raw_desc
                elif row.get("Tipo") == "2":
                    blinds[inp_id] = raw_desc
                else:
                    print(f"[WARNING] Unknown type for ADDE {inp_id}: {row.get('Tipo')}")
                    continue

    except FileNotFoundError:
        print(f"[ERROR] Could not find CSV file '{filepath_output}'.")
        return
    

    try:
        with open(filepath_func, mode="r", encoding="iso-8859-1") as f:
            reader = csv.DictReader(f, delimiter=";")
            
            for row in reader:
                # Skip empty rows or missing columns
                if not row.get("Adde") or not row.get("Out1"):
                    continue

                raw_add = row["Adde"].strip()
                raw_type = row["Accao"].strip() if row.get("Accao") else ""
                raw_out = row["Out1"].strip()

                if not raw_add.isdigit() or not raw_out.isdigit():
                    continue

                inp_id = int(raw_add)
                light_id = int(raw_out)

                # Skip unmapped/placeholder light IDs
                if light_id in (0, 255):
                    continue

                # Translate action type
                action = ACTION_MAP.get(raw_type)
                if not action:
                    continue

                if inp_id not in mappings:
                    mappings[inp_id] = {}

                # Handle single vs multiple light targets per action
                if action in mappings[inp_id]:
                    existing = mappings[inp_id][action]
                    if isinstance(existing, list):
                        existing.append(light_id)
                    else:
                        mappings[inp_id][action] = [existing, light_id]
                else:
                    mappings[inp_id][action] = light_id

    except FileNotFoundError:
        print(f"[ERROR] Could not find CSV file '{filepath_func}'.")
        return

    #convert into the config file for write
    base_config["blinds"] = blinds
    base_config["lights"] = lights
    base_config["inputs"] = inputs
    base_config["mappings"] = mappings

    # export the yaml
    with open(DEFAULT_OUTPUT, "w", encoding="utf-8") as f:
        yaml.dump(base_config, f, sort_keys=False, default_flow_style=False, allow_unicode=True)

    print(f"[SUCCESS] Exported full configuration to {DEFAULT_OUTPUT}")


if __name__ == "__main__":
    convert_csv_to_yaml()