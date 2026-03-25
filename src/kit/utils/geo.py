"""Location parsing and resolution utilities."""

from __future__ import annotations

import re
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from kit.config import KitConfig

_COORD_PATTERN = re.compile(
    r"^(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)$"
)
_SAVED_NAMES = {"home"}


class LocationType(Enum):
    COORDINATES = "coordinates"
    ADDRESS = "address"
    SAVED = "saved"


class ParsedLocation(BaseModel):
    raw: str
    type: LocationType
    lat: float | None = None
    lng: float | None = None
    name: str | None = None

    def resolve(self, config: KitConfig | None = None) -> str:
        if self.type == LocationType.COORDINATES:
            return f"{self.lat},{self.lng}"
        if self.type == LocationType.SAVED:
            if config is None:
                raise ValueError(f"Config required to resolve saved location '{self.name}'")
            value = getattr(config, self.name, None)  # type: ignore[arg-type]
            if not value:
                raise ValueError(f"Saved location '{self.name}' not configured. Run: kit setup")
            return value
        return self.raw


def parse_location(raw: str) -> ParsedLocation:
    raw = raw.strip()
    match = _COORD_PATTERN.match(raw)
    if match:
        return ParsedLocation(
            raw=raw,
            type=LocationType.COORDINATES,
            lat=float(match.group(1)),
            lng=float(match.group(2)),
        )
    if raw.lower() in _SAVED_NAMES:
        return ParsedLocation(raw=raw, type=LocationType.SAVED, name=raw.lower())
    return ParsedLocation(raw=raw, type=LocationType.ADDRESS)
