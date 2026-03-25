# tests/test_config.py
import pytest
from pathlib import Path
from kit.config import KitConfig, load_config, save_config, get_config_dir


def test_get_config_dir_returns_path():
    path = get_config_dir()
    assert isinstance(path, Path)
    assert path.name == "kit"


def test_default_config():
    config = KitConfig()
    assert config.default_mode == "transit"
    assert config.home is None
    assert config.google_maps_api_key is None
    assert config.calendar_id == "primary"
    assert config.meta_version == 1


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("KIT_GOOGLE_MAPS_API_KEY", "test-key-123")
    config = KitConfig()
    assert config.google_maps_api_key == "test-key-123"


def test_save_and_load_config(tmp_path):
    config = KitConfig(home="Teststr 1, Berlin", default_mode="bicycling")
    save_config(config, config_dir=tmp_path)
    loaded = load_config(config_dir=tmp_path)
    assert loaded.home == "Teststr 1, Berlin"
    assert loaded.default_mode == "bicycling"


def test_load_config_missing_file_returns_default(tmp_path):
    config = load_config(config_dir=tmp_path)
    assert config.default_mode == "transit"
