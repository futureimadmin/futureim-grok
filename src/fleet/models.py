"""
Fleet / Rack / Tier domain model — 3-dimensional logical structure.

  Fleet  = logical domain          (e.g. Consumer Lending)
  Rack   = logical sub-domain      (e.g. Personal Loans)
  Tier   = logical group of sub-domains (e.g. Originations, Servicing)

BIAN is the base platform for banking fleets.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class FleetStatus(str, Enum):
    ACTIVE = "active"
    PROVISIONING = "provisioning"
    MAINTENANCE = "maintenance"
    DISABLED = "disabled"


class Tier(BaseModel):
    tier_id: str = Field(..., description="Stable id, e.g. originations")
    name: str
    description: str = ""
    rack_ids: List[str] = Field(default_factory=list)
    bian_service_domains: List[str] = Field(default_factory=list)


class Rack(BaseModel):
    rack_id: str = Field(..., description="Stable id, e.g. claims")
    name: str
    description: str = ""
    top_k: Optional[int] = None
    embedding_namespace: Optional[str] = None
    bian_service_domains: List[str] = Field(default_factory=list)
    tier_ids: List[str] = Field(default_factory=list)


class Fleet(BaseModel):
    fleet_id: str = Field(..., description="Stable id, e.g. insurance")
    name: str
    description: str = ""
    icon: str = "📚"
    status: FleetStatus = FleetStatus.ACTIVE
    racks: List[Rack] = Field(default_factory=list)
    tiers: List[Tier] = Field(default_factory=list)
    default_top_k: int = 8
    system_prompt_hint: str = ""
    documents_prefix: str = ""
    platform: str = "generic"  # "bian" | "generic"
    bian_version: str = "12"
    is_reference: bool = False
    reference_fleet_id: Optional[str] = "bian"

    def rack(self, rack_id: str) -> Optional[Rack]:
        for r in self.racks:
            if r.rack_id == rack_id:
                return r
        return None

    def tier(self, tier_id: str) -> Optional[Tier]:
        for t in self.tiers:
            if t.tier_id == tier_id:
                return t
        return None

    def namespace(
        self,
        rack_id: Optional[str] = None,
        tier_id: Optional[str] = None,
    ) -> str:
        parts = [self.fleet_id]
        if rack_id:
            parts.append(rack_id)
        if tier_id:
            parts.append(tier_id)
        return "/".join(parts)

    def bian_domains_for_rack(self, rack_id: Optional[str] = None) -> List[str]:
        if not rack_id:
            domains: List[str] = []
            for r in self.racks:
                domains.extend(r.bian_service_domains)
            return sorted(set(domains))
        r = self.rack(rack_id)
        return list(r.bian_service_domains) if r else []


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
        return [f for f in self.list_active() if f.platform == "bian" and not f.is_reference]

    def reference_fleet(self) -> Optional[Fleet]:
        for f in self.fleets:
            if f.is_reference or f.fleet_id == "bian":
                return f
        return None
