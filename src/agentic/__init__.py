"""Agentic RAG – multi-step plan → act → observe → reflect → retry with RAGAS metrics."""

from .metrics import AccuracyMetrics, evaluate_accuracy

__all__ = ["AccuracyMetrics", "evaluate_accuracy", "AgenticRAG"]


def __getattr__(name: str):
    if name == "AgenticRAG":
        from .agent import AgenticRAG
        return AgenticRAG
    raise AttributeError(name)
