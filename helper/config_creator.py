import csv
import yaml

ACTION_MAP = {
    "1": "single_press",
    "2": "double_press",
    "3": "long_press"
}

def convert_csv_to_yaml(csv_filepath="mods_input_func.csv", output_filepath="mappings.yaml"):
    mappings = {}

    csv_filepath = str(input("Enter the input function CSV file name") or csv_filepath)
    with open(csv_filepath, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        
        for row in reader:
            #skip empty rows or missing values
            if not row.get("Adde") or not row.get("Out1"):
                continue

            raw_add = row["Adde"].strip()
            raw_type = row["Accao"].strip() if row.get("Accao") else ""
            raw_out = row["Out1"].strip()

            if not raw_add.isdigit() or not raw_out.isdigit():
                continue

            inp_id = int(raw_add)
            light_id = int(raw_out)

            #skip unmapped/invalid
            if light_id in (0, 255):
                continue

            #only proceed if button action type in list
            action = ACTION_MAP.get(raw_type)
            if not action:
                continue

            if inp_id not in mappings:
                mappings[inp_id] = {}

            #handle single vs multiple light targets per action
            if action in mappings[inp_id]:
                existing = mappings[inp_id][action]
                if isinstance(existing, list):
                    existing.append(light_id)
                else:
                    mappings[inp_id][action] = [existing, light_id]
            else:
                mappings[inp_id][action] = light_id

    #export
    with open(output_filepath, "w", encoding="utf-8") as f:
        yaml.dump({"mappings": mappings}, f, sort_keys=False, default_flow_style=False)

    print(f"[SUCCESS] Exported clean mappings to {output_filepath}")

if __name__ == "__config_creator__":
    convert_csv_to_yaml("mods_input_func.csv")