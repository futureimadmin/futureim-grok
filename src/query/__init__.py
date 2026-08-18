"""Query package — lazy imports so preview/seed work without Vertex."""

__all__ = [
    "HybridRetriever",
    "reciprocal_rank_fusion",
    "CrossEncoderReranker",
    "SemanticCache",
    "build_prompt",
    "post_process",
    "Generator",
]


def __getattr__(name: str):
    if name in ("HybridRetriever", "reciprocal_rank_fusion"):
        from .retrieval import HybridRetriever, reciprocal_rank_fusion
        return HybridRetriever if name == "HybridRetriever" else reciprocal_rank_fusion
    if name == "CrossEncoderReranker":
        from .reranker import CrossEncoderReranker
        return CrossEncoderReranker
    if name == "SemanticCache":
        from .cache import SemanticCache
        return SemanticCache
    if name == "build_prompt":
        from .prompt import build_prompt
        return build_prompt
    if name == "post_process":
        from .postprocess import post_process
        return post_process
    if name == "Generator":
        from .generator import Generator
        return Generator
    raise AttributeError(name)
