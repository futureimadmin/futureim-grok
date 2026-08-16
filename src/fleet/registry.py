"""Load and serve the Fleet registry."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import yaml

from src.fleet.models import Fleet, FleetRegistry, FleetStatus, Rack

logger = logging.getLogger(__name__)

DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parents[2] / "config" / "fleets" / "registry.yaml"


def _load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def get_registry(path: Optional[str] = None) -> FleetRegistry:
    p = Path(path) if path else DEFAULT_REGISTRY_PATH
    if not p.exists():
        logger.warning("Fleet registry not found at %s – empty registry", p)
        return FleetRegistry(fleets=[])
    data = _load_yaml(p)
    fleets: List[Fleet] = []
    for raw in data.get("fleets", []):
        racks = [Rack(**r) for r in raw.pop("racks", [])]
        status = raw.pop("status", "active")
        fleets.append(Fleet(racks=racks, status=FleetStatus(status), **raw))
    reg = FleetRegistry(fleets=fleets)
    logger.info("Loaded %d fleets from %s", len(reg.fleets), p)
    return reg


def list_fleets() -> List[Fleet]:
    return get_registry().list_active()


def get_fleet(fleet_id: str) -> Optional[Fleet]:
    return get_registry().get(fleet_id)


def get_rack(fleet_id: str, rack_id: str) -> Optional[Rack]:
    fleet = get_fleet(fleet_id)
    if not fleet:
        return None
    return fleet.rack(rack_id)
