from core.network.booth_config import (
    DEFAULT_BOOTH_TOKEN,
    DEFAULT_DISCOVERY_PORT,
    DEFAULT_LAN_PORT,
    load_booth_config,
    save_booth_config,
)


def test_booth_config_defaults_and_roundtrip(tmp_path):
    cfg_path = str(tmp_path / "nested" / "booth_config.json")
    assert DEFAULT_DISCOVERY_PORT == 8766
    assert load_booth_config(cfg_path) == {
        "host": "",
        "port": DEFAULT_LAN_PORT,
        "token": DEFAULT_BOOTH_TOKEN,
    }
    save_booth_config(cfg_path, {"host": "192.168.1.50", "port": 9000, "token": "secret"})
    assert load_booth_config(cfg_path) == {
        "host": "192.168.1.50",
        "port": 9000,
        "token": "secret",
    }


def test_booth_config_handles_corrupt_json(tmp_path):
    cfg_path = tmp_path / "booth_config.json"
    cfg_path.write_text("{not valid json", encoding="utf-8")
    assert load_booth_config(str(cfg_path)) == {
        "host": "",
        "port": DEFAULT_LAN_PORT,
        "token": DEFAULT_BOOTH_TOKEN,
    }
