"""Config management for kit. Stores settings in ~/.config/kit/config.toml."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

import tomli_w


def get_config_dir() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "kit"


class KitConfig(BaseModel):
    meta_version: int = 1
    default_mode: str = "transit"
    home: str | None = None
    google_maps_api_key: str | None = Field(
        default_factory=lambda: os.environ.get("KIT_GOOGLE_MAPS_API_KEY")
    )
    calendar_id: str = "primary"


def load_config(config_dir: Path | None = None) -> KitConfig:
    config_dir = config_dir or get_config_dir()
    config_file = config_dir / "config.toml"
    if not config_file.exists():
        return KitConfig()
    data = tomllib.loads(config_file.read_text())
    flat = {}
    for section in data.values():
        if isinstance(section, dict):
            flat.update(section)
        else:
            flat.update(data)
            break
    return KitConfig(**flat)


def save_config(config: KitConfig, config_dir: Path | None = None) -> None:
    config_dir = config_dir or get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.toml"
    data = {
        "meta": {"version": config.meta_version},
        "general": {"default_mode": config.default_mode},
        "google_maps": {},
        "google_calendar": {"calendar_id": config.calendar_id},
    }
    if config.home:
        data["general"]["home"] = config.home
    if config.google_maps_api_key:
        data["google_maps"]["api_key"] = config.google_maps_api_key
    config_file.write_text(tomli_w.dumps(data))
    config_file.chmod(0o600)
