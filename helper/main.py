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


def convert_csv_to_yaml(
        filepath_input="mods_input.csv",
        filepath_output="mods_output.csv",
        filepath_func="mods_input_func.csv",
        output_filepath="config.yaml"
        ):

    prompt_input = input(f"Enter the input CSV file name [{filepath_input}]: ").strip()
    prompt_output = input(f"Enter the input functions CSV file name [{filepath_output}]: ").strip()
    prompt_func = input(f"Enter the input functions CSV file name [{filepath_func}]: ").strip()
    if prompt_input :
        filepath_input = prompt_input
    if prompt_output:
        filepath_output = prompt_output
    if prompt_func:
        filepath_func = prompt_func

    # Load existing config.yaml to preserve light/blind definitions if present
    base_config = DEFAULT_CONFIG.copy()
    if os.path.exists(output_filepath):
        try:
            with open(output_filepath, "r", encoding="utf-8") as f:
                existing = yaml.safe_load(f)
                if isinstance(existing, dict):
                    base_config.update(existing)
        except Exception as e:
            print(f"[WARNING] Could not read existing {output_filepath}, using default template: {e}")

    inputs = {}
    outputs = {}
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
        with open(filepath_func, mode="r", encoding="utf-8-sig") as f:
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
    base_config["inputs"] = inputs
    base_config["mappings"] = mappings

    # export the yaml
    with open(output_filepath, "w", encoding="utf-8") as f:
        yaml.dump(base_config, f, sort_keys=False, default_flow_style=False, allow_unicode=True)

    print(f"[SUCCESS] Exported full configuration to {output_filepath}")


if __name__ == "__main__":
    convert_csv_to_yaml()