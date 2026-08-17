"""
Agent Memory — short-term scratchpad + optional long-term vector notes.

Architecture:
  short-term: scratchpad (this turn's thoughts, tool results, critiques)
  long-term:  vector store (persisted across turns — optional)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ScratchEntry:
    role: str  # thought | action | observation | critique | plan
    content: str
    tool: Optional[str] = None
    ts: float = field(default_factory=time.time)
    meta: Dict[str, Any] = field(default_factory=dict)


class AgentMemory:
    def __init__(self, max_entries: int = 50):
        self.max_entries = max_entries
        self.scratchpad: List[ScratchEntry] = []
        self.sub_goals: List[str] = []
        self.tool_calls: List[Dict[str, Any]] = []

    def think(self, content: str) -> None:
        self._add("thought", content)

    def plan(self, goals: List[str]) -> None:
        self.sub_goals = list(goals)
        self._add("plan", " | ".join(goals))

    def act(self, tool: str, content: str, meta: Optional[Dict] = None) -> None:
        self._add("action", content, tool=tool, meta=meta or {})
        self.tool_calls.append({"tool": tool, "detail": content, "meta": meta or {}})

    def observe(self, content: str, tool: Optional[str] = None) -> None:
        self._add("observation", content, tool=tool)

    def critique(self, content: str, meta: Optional[Dict] = None) -> None:
        self._add("critique", content, meta=meta or {})

    def _add(
        self,
        role: str,
        content: str,
        tool: Optional[str] = None,
        meta: Optional[Dict] = None,
    ) -> None:
        self.scratchpad.append(
            ScratchEntry(role=role, content=content, tool=tool, meta=meta or {})
        )
        if len(self.scratchpad) > self.max_entries:
            self.scratchpad = self.scratchpad[-self.max_entries :]

    def reasoning_trace(self) -> List[Dict[str, Any]]:
        return [
            {
                "role": e.role,
                "content": e.content,
                "tool": e.tool,
                "meta": e.meta,
            }
            for e in self.scratchpad
        ]

    def summary(self) -> str:
        lines = []
        for e in self.scratchpad[-12:]:
            prefix = e.role.upper()
            if e.tool:
                prefix += f"[{e.tool}]"
            lines.append(f"{prefix}: {e.content[:200]}")
        return "\n".join(lines)
