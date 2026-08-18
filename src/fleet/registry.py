"""Load and serve the Fleet / Rack / Tier registry (including BIAN maps)."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import yaml

from src.fleet.models import Fleet, FleetRegistry, FleetStatus, Rack, Tier

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
    # Optional extension file: config/fleets/banking_extensions.yaml
    ext = p.parent / "banking_extensions.yaml"
    if ext.exists():
        extra = _load_yaml(ext)
        extra_fleets = extra.get("fleets") if isinstance(extra, dict) else None
        if extra_fleets is None and isinstance(extra, dict):
            extra_fleets = []
        if extra_fleets:
            data.setdefault("fleets", []).extend(extra_fleets)
            logger.info("Merged %d fleets from %s", len(extra_fleets), ext)
    fleets: List[Fleet] = []
    for raw in data.get("fleets", []):
        racks = [Rack(**r) for r in raw.pop("racks", [])]
        tiers = [Tier(**t) for t in raw.pop("tiers", [])]
        status = raw.pop("status", "active")
        fleets.append(
            Fleet(racks=racks, tiers=tiers, status=FleetStatus(status), **raw)
        )
    reg = FleetRegistry(
        fleets=fleets,
        bian_version_default=str(data.get("bian_version_default", "12")),
    )
    logger.info(
        "Loaded %d fleets (%d banking, ref=%s) from %s",
        len(reg.fleets),
        len(reg.list_banking()),
        reg.reference_fleet().fleet_id if reg.reference_fleet() else None,
        p,
    )
    return reg


def reload_registry() -> FleetRegistry:
    get_registry.cache_clear()
    return get_registry()


def list_fleets() -> List[Fleet]:
    return get_registry().list_active()


def get_fleet(fleet_id: str) -> Optional[Fleet]:
    return get_registry().get(fleet_id)


def get_rack(fleet_id: str, rack_id: str) -> Optional[Rack]:
    fleet = get_fleet(fleet_id)
    if not fleet:
        return None
    return fleet.rack(rack_id)


def get_tier(fleet_id: str, tier_id: str) -> Optional[Tier]:
    fleet = get_fleet(fleet_id)
    if not fleet:
        return None
    return fleet.tier(tier_id)


def bian_domains_for(fleet_id: str, rack_id: Optional[str] = None) -> List[str]:
    fleet = get_fleet(fleet_id)
    if not fleet:
        return []
    return fleet.bian_domains_for_rack(rack_id)
