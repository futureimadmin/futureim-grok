"""
Admin operations for Fleet / Rack registry.
Writes back to config/fleets/registry.yaml so changes survive restarts.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from src.fleet.models import Fleet, FleetRegistry, FleetStatus, Rack
from src.fleet.registry import DEFAULT_REGISTRY_PATH, get_registry

logger = logging.getLogger(__name__)


def _dump_registry(reg: FleetRegistry, path: Path) -> None:
    payload: Dict[str, Any] = {
        "bian_version_default": reg.bian_version_default,
        "fleets": [],
    }
    for f in reg.fleets:
        entry: Dict[str, Any] = {
            "fleet_id": f.fleet_id,
            "name": f.name,
            "description": f.description,
            "icon": f.icon,
            "status": f.status.value,
            "platform": f.platform,
            "bian_version": f.bian_version,
            "is_reference": f.is_reference,
            "reference_fleet_id": f.reference_fleet_id,
            "default_top_k": f.default_top_k,
            "documents_prefix": f.documents_prefix or f"fleets/{f.fleet_id}/",
            "system_prompt_hint": f.system_prompt_hint,
            "tiers": [
                {
                    "tier_id": t.tier_id,
                    "name": t.name,
                    "description": t.description,
                    "rack_ids": list(t.rack_ids),
                    "bian_service_domains": list(t.bian_service_domains),
                }
                for t in f.tiers
            ],
            "racks": [
                {
                    "rack_id": r.rack_id,
                    "name": r.name,
                    "description": r.description,
                    **({"top_k": r.top_k} if r.top_k is not None else {}),
                    "bian_service_domains": list(r.bian_service_domains),
                    "tier_ids": list(r.tier_ids),
                }
                for r in f.racks
            ],
        }
        payload["fleets"].append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(payload, fh, sort_keys=False, allow_unicode=True)
    get_registry.cache_clear()
    logger.info("Wrote fleet registry to %s (%d fleets)", path, len(reg.fleets))


def create_fleet(
    fleet_id: str,
    name: str,
    description: str = "",
    icon: str = "📚",
    default_top_k: int = 8,
    system_prompt_hint: str = "",
    path: Optional[Path] = None,
) -> Fleet:
    path = path or DEFAULT_REGISTRY_PATH
    reg = get_registry(str(path))
    if reg.get(fleet_id):
        raise ValueError(f"Fleet '{fleet_id}' already exists")
    fleet = Fleet(
        fleet_id=fleet_id,
        name=name,
        description=description,
        icon=icon,
        status=FleetStatus.ACTIVE,
        default_top_k=default_top_k,
        system_prompt_hint=system_prompt_hint,
        documents_prefix=f"fleets/{fleet_id}/",
        racks=[],
    )
    reg.fleets.append(fleet)
    _dump_registry(reg, path)
    return fleet


def update_fleet(fleet_id: str, **fields) -> Fleet:
    path = DEFAULT_REGISTRY_PATH
    reg = get_registry(str(path))
    fleet = reg.get(fleet_id)
    if not fleet:
        raise ValueError(f"Fleet '{fleet_id}' not found")
    data = fleet.model_dump()
    for k, v in fields.items():
        if v is not None and k in data and k not in {"fleet_id", "racks"}:
            data[k] = v
    if "status" in fields and fields["status"] is not None:
        data["status"] = FleetStatus(fields["status"])
    updated = Fleet(**data)
    reg.fleets = [updated if f.fleet_id == fleet_id else f for f in reg.fleets]
    _dump_registry(reg, path)
    return updated


def delete_fleet(fleet_id: str) -> None:
    path = DEFAULT_REGISTRY_PATH
    reg = get_registry(str(path))
    if not reg.get(fleet_id):
        raise ValueError(f"Fleet '{fleet_id}' not found")
    reg.fleets = [f for f in reg.fleets if f.fleet_id != fleet_id]
    _dump_registry(reg, path)


def add_rack(
    fleet_id: str,
    rack_id: str,
    name: str,
    description: str = "",
    top_k: Optional[int] = None,
) -> Rack:
    path = DEFAULT_REGISTRY_PATH
    reg = get_registry(str(path))
    fleet = reg.get(fleet_id)
    if not fleet:
        raise ValueError(f"Fleet '{fleet_id}' not found")
    if fleet.rack(rack_id):
        raise ValueError(f"Rack '{rack_id}' already exists in fleet '{fleet_id}'")
    rack = Rack(rack_id=rack_id, name=name, description=description, top_k=top_k)
    fleet.racks.append(rack)
    reg.fleets = [fleet if f.fleet_id == fleet_id else f for f in reg.fleets]
    _dump_registry(reg, path)
    return rack


def delete_rack(fleet_id: str, rack_id: str) -> None:
    path = DEFAULT_REGISTRY_PATH
    reg = get_registry(str(path))
    fleet = reg.get(fleet_id)
    if not fleet:
        raise ValueError(f"Fleet '{fleet_id}' not found")
    if not fleet.rack(rack_id):
        raise ValueError(f"Rack '{rack_id}' not found")
    fleet.racks = [r for r in fleet.racks if r.rack_id != rack_id]
    reg.fleets = [fleet if f.fleet_id == fleet_id else f for f in reg.fleets]
    _dump_registry(reg, path)
