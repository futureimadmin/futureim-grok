"""
In-memory accuracy telemetry store for the Dashboard.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional


class AccuracyStore:
    def __init__(self, maxlen: int = 500):
        self._lock = threading.Lock()
        self._runs: Deque[Dict[str, Any]] = deque(maxlen=maxlen)

    def record(self, run: Dict[str, Any]) -> None:
        entry = {
            "ts": time.time(),
            "query": (run.get("query") or "")[:200],
            "fleet_id": run.get("fleet_id"),
            "rack_id": run.get("rack_id"),
            "ragas_score": run.get("ragas", {}).get("ragas_score", 0.0),
            "faithfulness": run.get("ragas", {}).get("faithfulness", 0.0),
            "answer_relevance": run.get("ragas", {}).get("answer_relevance", 0.0),
            "context_precision": run.get("ragas", {}).get("context_precision", 0.0),
            "context_recall": run.get("ragas", {}).get("context_recall", 0.0),
            "passed": run.get("threshold_met", False),
            "latency_ms": run.get("latency_ms", 0.0),
            "attempts": run.get("attempts", 1),
            "sources_used": run.get("sources_used", 0),
            "threshold": run.get("ragas", {}).get("threshold", 0.80),
        }
        with self._lock:
            self._runs.appendleft(entry)

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            runs = list(self._runs)
        n = len(runs)
        if n == 0:
            return {
                "total_runs": 0,
                "pass_rate": 0.0,
                "avg_ragas": 0.0,
                "avg_faithfulness": 0.0,
                "avg_answer_relevance": 0.0,
                "avg_context_precision": 0.0,
                "avg_context_recall": 0.0,
                "avg_latency_ms": 0.0,
                "avg_attempts": 0.0,
                "threshold": 0.80,
                "overall_accuracy_pct": 0.0,
                "by_fleet": {},
                "recent": [],
            }

        def avg(key: str) -> float:
            return sum(r[key] for r in runs) / n

        passed = sum(1 for r in runs if r["passed"])
        by_fleet: Dict[str, Dict[str, float]] = {}
        for r in runs:
            fid = r.get("fleet_id") or "unscoped"
            bucket = by_fleet.setdefault(fid, {"n": 0, "ragas_sum": 0.0, "pass": 0})
            bucket["n"] += 1
            bucket["ragas_sum"] += r["ragas_score"]
            if r["passed"]:
                bucket["pass"] += 1

        fleet_stats = {
            fid: {
                "runs": b["n"],
                "avg_ragas": round(b["ragas_sum"] / b["n"], 4),
                "pass_rate": round(b["pass"] / b["n"], 4),
            }
            for fid, b in by_fleet.items()
        }

        avg_ragas = avg("ragas_score")
        return {
            "total_runs": n,
            "pass_rate": round(passed / n, 4),
            "avg_ragas": round(avg_ragas, 4),
            "avg_faithfulness": round(avg("faithfulness"), 4),
            "avg_answer_relevance": round(avg("answer_relevance"), 4),
            "avg_context_precision": round(avg("context_precision"), 4),
            "avg_context_recall": round(avg("context_recall"), 4),
            "avg_latency_ms": round(avg("latency_ms"), 1),
            "avg_attempts": round(avg("attempts"), 2),
            "threshold": runs[0]["threshold"] if runs else 0.80,
            "overall_accuracy_pct": round(avg_ragas * 100, 1),
            "by_fleet": fleet_stats,
            "recent": runs[:25],
        }

    def clear(self) -> None:
        with self._lock:
            self._runs.clear()


accuracy_store = AccuracyStore()
