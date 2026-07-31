import os
import sys
import yaml


def load_config(config_file="config.yaml"):
    # Fallback to subdirectory if present
    if not os.path.exists(config_file):
        alt_path = os.path.join("config", "config.yaml")
        if os.path.exists(alt_path):
            config_file = alt_path

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"[Config Error] Could not load {config_file}: {e}")
        sys.exit(1)