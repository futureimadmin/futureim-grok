"""
Fleet / Rack domain model.

Fleet  = a business domain RAG system (e.g. Insurance, Consumer Lending)
Rack   = a subdomain / specialty knowledge area inside a fleet
         (e.g. Insurance → claims | underwriting | policies)

Maps onto metadata filters:
  fleet_id  → domain boundary
  rack_id   → subdomain filter
  tenant_id → customer isolation
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


class Rack(BaseModel):
    rack_id: str = Field(..., description="Stable id, e.g. claims")
    name: str
    description: str = ""
    top_k: Optional[int] = None
    embedding_namespace: Optional[str] = None


class Fleet(BaseModel):
    fleet_id: str = Field(..., description="Stable id, e.g. insurance")
    name: str
    description: str = ""
    icon: str = "📚"
    status: FleetStatus = FleetStatus.ACTIVE
    racks: List[Rack] = Field(default_factory=list)
    default_top_k: int = 8
    system_prompt_hint: str = ""
    documents_prefix: str = ""

    def rack(self, rack_id: str) -> Optional[Rack]:
        for r in self.racks:
            if r.rack_id == rack_id:
                return r
        return None

    def namespace(self, rack_id: Optional[str] = None) -> str:
        if rack_id:
            return f"{self.fleet_id}/{rack_id}"
        return self.fleet_id


class FleetRegistry(BaseModel):
    fleets: List[Fleet] = Field(default_factory=list)

    def get(self, fleet_id: str) -> Optional[Fleet]:
        for f in self.fleets:
            if f.fleet_id == fleet_id:
                return f
        return None

    def list_active(self) -> List[Fleet]:
        return [f for f in self.fleets if f.status == FleetStatus.ACTIVE]
