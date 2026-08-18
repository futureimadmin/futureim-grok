"""Fleet / Rack / Tier domain models — 3D logical isolation for RAG."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class FleetStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"


class Tier(BaseModel):
    """Logical group of sub-domains (racks). Extend on need."""

    tier_id: str
    name: str
    description: str = ""
    rack_ids: List[str] = Field(default_factory=list)
    bian_service_domains: List[str] = Field(default_factory=list)


class Rack(BaseModel):
    rack_id: str
    name: str
    description: str = ""
    top_k: Optional[int] = None
    bian_service_domains: List[str] = Field(default_factory=list)
    tier_ids: List[str] = Field(default_factory=list)


class Fleet(BaseModel):
    fleet_id: str
    name: str
    description: str = ""
    icon: str = "📁"
    status: FleetStatus = FleetStatus.ACTIVE
    default_top_k: int = 6
    documents_prefix: str = ""
    system_prompt_hint: str = ""
    platform: str = "generic"  # bian | generic
    bian_version: Optional[str] = None
    is_reference: bool = False
    reference_fleet_id: Optional[str] = None
    racks: List[Rack] = Field(default_factory=list)
    tiers: List[Tier] = Field(default_factory=list)

    def rack(self, rack_id: Optional[str]) -> Optional[Rack]:
        if not rack_id:
            return None
        for r in self.racks:
            if r.rack_id == rack_id:
                return r
        return None

    def tier(self, tier_id: Optional[str]) -> Optional[Tier]:
        if not tier_id:
            return None
        for t in self.tiers:
            if t.tier_id == tier_id:
                return t
        return None

    def namespace(self, rack_id: Optional[str] = None) -> str:
        if rack_id:
            return f"{self.fleet_id}/{rack_id}"
        return self.fleet_id

    def bian_domains_for_rack(self, rack_id: Optional[str] = None) -> List[str]:
        if rack_id:
            r = self.rack(rack_id)
            if r and r.bian_service_domains:
                return list(r.bian_service_domains)
        # fleet-level: union of all rack domains
        seen = []
        for r in self.racks:
            for d in r.bian_service_domains:
                if d not in seen:
                    seen.append(d)
        return seen


class FleetRegistry(BaseModel):
    fleets: List[Fleet] = Field(default_factory=list)
    bian_version_default: str = "12"

    def get(self, fleet_id: str) -> Optional[Fleet]:
        for f in self.fleets:
            if f.fleet_id == fleet_id:
                return f
        return None

    def list_active(self) -> List[Fleet]:
        return [f for f in self.fleets if f.status == FleetStatus.ACTIVE]

    def list_banking(self) -> List[Fleet]:
        return [f for f in self.fleets if f.platform == "bian" and not f.is_reference]

    def reference_fleet(self) -> Optional[Fleet]:
        for f in self.fleets:
            if f.is_reference:
                return f
        return self.get("bian")
