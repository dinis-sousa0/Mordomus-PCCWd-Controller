from pathlib import Path

from config import load_config

EXAMPLE = Path(__file__).resolve().parent.parent / "config.yaml.example"


def test_example_config_parses():
    cfg = load_config(str(EXAMPLE))

    assert isinstance(cfg, dict)
    for section in ("waveshare", "mqtt", "blinds", "lights", "inputs", "mappings"):
        assert section in cfg, f"missing section {section!r}"


def test_example_config_ids_are_ints():
    cfg = load_config(str(EXAMPLE))

    # The handlers look devices up by the integer IDs found in the byte frames
    for section in ("blinds", "lights", "inputs", "mappings"):
        assert all(isinstance(k, int) for k in cfg[section]), section
