"""
BIAN-aligned (Semantic API action terms; scaffolding only) code generation for a Fleet / Rack scope.

Emits service stubs that map only to active BIAN service domains for the
selected rack (and optional tier). Product policy stays in RAG context;
structure must follow BIAN control-record style operations.

Canonical operation patterns (BIAN-inspired):
  Initiate · Update · Control · Retrieve · Execute · Request · Notify
"""

from __future__ import annotations

BIAN_API_HINT = (
    "Map each domain to BIAN Semantic API action terms (Initiate/Update/Control/Execute/Retrieve). "
    "Prefer ISO20022-oriented field names for payment-related domains. "
    "Stubs are scaffolding only — require authZ, audit, and human review before production."
)

import re
from typing import Dict, List, Optional, Sequence

from src.common.models import RetrievedChunk
from src.fleet.models import Fleet, Rack, Tier
from src.query.bian_context import resolve_bian_domains

DOMAIN_OPERATIONS: Dict[str, List[str]] = {
    "Loan": ["Initiate", "Update", "Control", "Retrieve", "Execute", "Request"],
    "Credit Management": ["Initiate", "Update", "Control", "Retrieve", "Evaluate"],
    "Collateral Asset Administration": ["Initiate", "Update", "Control", "Retrieve", "Evaluate"],
    "Customer Offer": ["Initiate", "Update", "Control", "Retrieve", "Execute"],
    "Customer Agreement": ["Initiate", "Update", "Control", "Retrieve", "Execute"],
    "Party Reference Data Management": ["Initiate", "Update", "Retrieve", "Control"],
    "Payment Order": ["Initiate", "Update", "Control", "Retrieve", "Execute"],
    "Payment Execution": ["Initiate", "Update", "Control", "Retrieve", "Execute", "Notify"],
    "Card Transaction": ["Initiate", "Update", "Control", "Retrieve", "Authorize", "Clear"],
    "Sales Product": ["Initiate", "Update", "Retrieve", "Control"],
    "Corporate Loan": ["Initiate", "Update", "Control", "Retrieve", "Execute", "Request"],
    "Syndicated Loan": ["Initiate", "Update", "Control", "Retrieve", "Execute", "Notify"],
    "Credit Facility": ["Initiate", "Update", "Control", "Retrieve", "Evaluate"],
    "Project Finance": ["Initiate", "Update", "Control", "Retrieve", "Evaluate", "Execute"],
    "Limit And Exposure Management": ["Initiate", "Update", "Control", "Retrieve", "Evaluate"],
    "Investment Portfolio Planning": ["Initiate", "Update", "Control", "Retrieve", "Evaluate"],
    "Investment Portfolio Analysis": ["Initiate", "Update", "Retrieve", "Evaluate"],
    "Investment Portfolio Management": ["Initiate", "Update", "Control", "Retrieve", "Execute", "Evaluate"],
    "Investment Account": ["Initiate", "Update", "Control", "Retrieve"],
    "eTrading Workbench": ["Initiate", "Update", "Control", "Retrieve", "Execute"],
    "Current Account": ["Initiate", "Update", "Control", "Retrieve", "Execute"],
    "Corporate Current Account": ["Initiate", "Update", "Control", "Retrieve", "Execute"],
    "Savings Account": ["Initiate", "Update", "Control", "Retrieve"],
    "Term Deposit": ["Initiate", "Update", "Control", "Retrieve", "Execute"],
    "Virtual Account": ["Initiate", "Update", "Control", "Retrieve"],
    "Standing Order": ["Initiate", "Update", "Control", "Retrieve", "Execute"],
    "Letter of Credit": ["Initiate", "Update", "Control", "Retrieve", "Execute", "Notify"],
    "Bank Guarantee": ["Initiate", "Update", "Control", "Retrieve", "Execute", "Notify"],
    "Trade Finance": ["Initiate", "Update", "Control", "Retrieve", "Execute"],
}

DEFAULT_OPS = ["Initiate", "Update", "Control", "Retrieve", "Execute"]


def _slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip()).strip("_")
    return s.lower() or "service"


def _class_name(domain: str) -> str:
    parts = re.split(r"[^a-zA-Z0-9]+", domain)
    return "".join(p.capitalize() for p in parts if p) or "Service"


def operations_for(domain: str) -> List[str]:
    return list(DOMAIN_OPERATIONS.get(domain, DEFAULT_OPS))


def build_codegen_system_prompt(
    fleet: Optional[Fleet] = None,
    rack: Optional[Rack] = None,
    tier: Optional[Tier] = None,
    domains: Optional[Sequence[str]] = None,
    language: str = "python",
) -> str:
    domains = list(domains or resolve_bian_domains(fleet, rack, tier.tier_id if tier else None))
    scope = []
    if fleet:
        scope.append(f"Fleet: {fleet.name} ({fleet.fleet_id})")
    if rack:
        scope.append(f"Rack: {rack.name} ({rack.rack_id})")
    if tier:
        scope.append(f"Tier: {tier.name} ({tier.tier_id})")
    domain_lines = "\n".join(f"  - {d}: ops = {', '.join(operations_for(d))}" for d in domains) or "  - (none resolved)"

    return f"""You are a BIAN-aligned code generator for banking systems.
Generate ONLY service stubs that map to the active BIAN service domains below.
Do NOT invent domains outside this list. Do NOT include product pricing policy
unless it appears in the provided context — structure must stay BIAN-pure.

Scope:
  {chr(10).join(scope) if scope else "  (unscoped)"}

Active BIAN service domains and allowed operations:
{domain_lines}

Rules:
1. One module (or package section) per BIAN service domain.
2. Use control-record style method names: Initiate, Update, Control, Retrieve, Execute, Request, Notify, Evaluate, Authorize, Clear — only those listed for the domain.
3. Each operation accepts a typed request DTO and returns a typed response DTO (or Result envelope).
4. Include brief docstring referencing the BIAN domain name.
5. Language: {language}. Prefer clear interfaces over full implementations.
6. Mark extension points with `# EXTENSION: bank-specific policy` comments — never fork BIAN semantics silently.
7. If context is insufficient for a domain, still emit the structural stub from BIAN operations list.
8. Output code only (markdown fenced blocks per domain), no marketing prose."""


def build_codegen_user_prompt(
    query: str,
    chunks: Optional[List[RetrievedChunk]] = None,
    domains: Optional[Sequence[str]] = None,
) -> str:
    ctx_parts = []
    for i, c in enumerate(chunks or [], start=1):
        path = c.metadata.source_path if c.metadata else "unknown"
        tag = ""
        if c.metadata and getattr(c.metadata, "bian_service_domain", None):
            tag = f" [BIAN:{c.metadata.bian_service_domain}]"
        ctx_parts.append(f"[Source {i}] {path}{tag}\n{c.text}")
    context = "\n\n".join(ctx_parts) if ctx_parts else "(no extra product context — emit pure BIAN stubs)"
    domain_hint = ", ".join(domains or []) or "resolved domains"
    return (
        f"Generate BIAN-aligned service stubs for: {domain_hint}\n\n"
        f"Developer request: {query}\n\n"
        f"Context:\n{context}"
    )


def render_stub_module(
    domain: str,
    language: str = "python",
    fleet_id: Optional[str] = None,
    rack_id: Optional[str] = None,
) -> str:
    ops = operations_for(domain)
    cls = _class_name(domain)
    mod = _slug(domain)
    scope = f"{fleet_id or 'fleet'}/{rack_id or 'rack'}"

    if language.lower() in ("typescript", "ts"):
        methods = "\n".join(
            f"  async {op.lower()}(req: {cls}{op}Request): Promise<{cls}{op}Response> {{\n"
            f"    // BIAN {domain} · {op} — scope {scope}\n"
            f"    throw new Error('Not implemented');\n"
            f"  }}"
            for op in ops
        )
        types = "\n".join(
            f"export interface {cls}{op}Request {{ /* EXTENSION: bank-specific */ }}\n"
            f"export interface {cls}{op}Response {{ status: string; /* EXTENSION */ }}"
            for op in ops
        )
        return (
            f"/**\n * BIAN Service Domain: {domain}\n"
            f" * Scope: {scope}\n"
            f" * Generated as structural stub — align implementations to BIAN control records.\n */\n"
            f"{types}\n\n"
            f"export class {cls}Service {{\n{methods}\n}}\n"
        )

    if language.lower() in ("java",):
        methods = "\n".join(
            f"    // BIAN {domain} · {op}\n"
            f"    public {cls}{op}Response {op[0].lower() + op[1:]}({cls}{op}Request request) {{\n"
            f"        throw new UnsupportedOperationException(\"Not implemented\");\n"
            f"    }}\n"
            for op in ops
        )
        return (
            f"/** BIAN Service Domain: {domain} | scope {scope} */\n"
            f"public class {cls}Service {{\n{methods}}}\n"
        )

    methods = "\n".join(
        f"    def {op.lower()}(self, request: {cls}{op}Request) -> {cls}{op}Response:\n"
        f"        \"\"\"BIAN {domain} · {op}. Scope: {scope}.\"\"\"\n"
        f"        # EXTENSION: bank-specific policy\n"
        f"        raise NotImplementedError\n"
        for op in ops
    )
    dataclasses = "\n\n".join(
        f"@dataclass\nclass {cls}{op}Request:\n    # EXTENSION: bank-specific fields\n    correlation_id: str = \"\"\n\n"
        f"@dataclass\nclass {cls}{op}Response:\n    status: str = \"not_implemented\"\n    # EXTENSION"
        for op in ops
    )
    return (
        f'"""BIAN Service Domain: {domain}\n'
        f"Scope: {scope}\n"
        f'Structural stub — do not fork BIAN semantics without explicit extension markers."""\n\n'
        f"from __future__ import annotations\nfrom dataclasses import dataclass\n\n"
        f"{dataclasses}\n\n"
        f"class {cls}Service:\n"
        f'    """BIAN domain service: {domain}."""\n\n'
        f"{methods}"
    )


def generate_stubs(
    domains: Sequence[str],
    *,
    language: str = "python",
    fleet_id: Optional[str] = None,
    rack_id: Optional[str] = None,
) -> str:
    if not domains:
        return "# No BIAN service domains resolved for this scope.\n"
    parts = []
    for d in domains:
        fence = "python" if language.lower() == "python" else language.lower()
        body = render_stub_module(d, language=language, fleet_id=fleet_id, rack_id=rack_id)
        parts.append(f"### BIAN · {d}\n\n```{fence}\n{body}\n```")
    header = (
        f"# BIAN-aligned service stubs\n"
        f"# fleet={fleet_id or '-'} rack={rack_id or '-'} language={language}\n"
        f"# domains: {', '.join(domains)}\n\n"
    )
    return header + "\n\n".join(parts)
