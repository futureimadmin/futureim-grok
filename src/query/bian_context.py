"""
BIAN dual-context resolution for banking fleets.

Policy:
  1. Always retrieve product fleet / rack / tier content.
  2. When platform == bian, also retrieve matching BIAN reference domains
     from the reference fleet (default: fleet_id=bian).
  3. Volume is unlimited at the design layer — filters constrain relevance, not capacity.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from src.fleet.models import Fleet, Rack
from src.fleet.registry import get_fleet, get_registry

logger = logging.getLogger(__name__)


def resolve_bian_domains(
    fleet: Optional[Fleet],
    rack: Optional[Rack] = None,
    tier_id: Optional[str] = None,
) -> List[str]:
    """BIAN service domain names for this scope."""
    if not fleet or fleet.platform != "bian":
        return []
    if rack and rack.bian_service_domains:
        domains = list(rack.bian_service_domains)
    else:
        domains = fleet.bian_domains_for_rack(rack.rack_id if rack else None)
    if tier_id and fleet.tiers:
        tier = fleet.tier(tier_id)
        if tier and tier.bian_service_domains:
            tier_set = set(tier.bian_service_domains)
            if domains:
                domains = [d for d in domains if d in tier_set] or list(tier.bian_service_domains)
            else:
                domains = list(tier.bian_service_domains)
    return domains


def product_filters(
    *,
    fleet_id: Optional[str],
    rack_id: Optional[str] = None,
    tier_id: Optional[str] = None,
    tenant_id: str = "default",
    access_level: str = "public",
    namespace: Optional[str] = None,
) -> Dict:
    f: Dict = {
        "tenant_id": tenant_id,
        "access_level": access_level,
        "fleet_id": fleet_id,
        "rack_id": rack_id,
        "tier_id": tier_id,
    }
    if namespace:
        f["namespace"] = namespace
    return {k: v for k, v in f.items() if v is not None}


def bian_reference_filters(
    domains: List[str],
    *,
    tenant_id: str = "default",
    access_level: str = "public",
    bian_version: Optional[str] = None,
) -> List[Dict]:
    """One filter dict per BIAN domain (OR via parallel retrieve + merge)."""
    reg = get_registry()
    ref = reg.reference_fleet()
    ref_id = ref.fleet_id if ref else "bian"
    version = bian_version or (ref.bian_version if ref else reg.bian_version_default)
    filters: List[Dict] = []
    if not domains:
        filters.append(
            {
                "tenant_id": tenant_id,
                "access_level": access_level,
                "fleet_id": ref_id,
                "is_bian_reference": True,
                "bian_version": version,
            }
        )
        return filters
    for domain in domains:
        filters.append(
            {
                "tenant_id": tenant_id,
                "access_level": access_level,
                "fleet_id": ref_id,
                "bian_service_domain": domain,
                "bian_version": version,
            }
        )
    return filters


def should_dual_pull(fleet: Optional[Fleet]) -> bool:
    if not fleet:
        return False
    if fleet.is_reference:
        return False
    return fleet.platform == "bian"


def describe_scope(
    fleet: Optional[Fleet],
    rack: Optional[Rack] = None,
    tier_id: Optional[str] = None,
) -> str:
    parts = []
    if fleet:
        parts.append(f"fleet={fleet.fleet_id} platform={fleet.platform}")
    if rack:
        parts.append(f"rack={rack.rack_id}")
    if tier_id:
        parts.append(f"tier={tier_id}")
    domains = resolve_bian_domains(fleet, rack, tier_id)
    if domains:
        parts.append("bian=[" + ", ".join(domains) + "]")
    return " ".join(parts) if parts else "unscoped"
