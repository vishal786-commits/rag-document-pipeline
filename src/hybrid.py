"""
Hybrid retrieval primitives: full-corpus BM25 ranking and Reciprocal Rank Fusion.

Dense (Pinecone) retrieval is strong on meaning but can miss chunks whose relevance
comes from an exact term the embedding under-weights. Running BM25 over the *entire*
corpus (not just the dense candidates) produces an independent keyword ranking, and
Reciprocal Rank Fusion combines the two so a chunk ranked highly by *either* signal
surfaces — this is what lets keyword matches that dense drops re-enter the results.
"""

from typing import List
from rank_bm25 import BM25Okapi


def bm25_rank(query: str, corpus: List[str]) -> List[str]:
    """
    Rank the full corpus by BM25 keyword relevance to the query.
    Returns every chunk, ordered best-first.
    """
    if not corpus:
        return []
    tokenised_corpus = [c.lower().split() for c in corpus]
    tokenised_query = query.lower().split()
    bm25 = BM25Okapi(tokenised_corpus)
    scores = bm25.get_scores(tokenised_query)
    ranked = sorted(zip(scores, corpus), key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in ranked]


def reciprocal_rank_fusion(rankings: List[List[str]], k: int = 60, top_k: int | None = None) -> List[str]:
    """
    Fuse several ranked lists of items (chunk texts) with Reciprocal Rank Fusion.

    RRF score for an item d is sum over rankings r of 1 / (k + rank_r(d)), where
    rank_r(d) is d's 1-based position in ranking r (items absent from r contribute 0).
    k dampens the weight of low ranks; 60 is the value from the original RRF paper.

    Args:
        rankings: list of ranked lists (e.g. [dense_ranked, sparse_ranked]).
        k: RRF damping constant.
        top_k: if set, return only the top_k fused items.

    Returns:
        Items ordered by descending fused score.
    """
    scores: dict[str, float] = {}
    first_seen: dict[str, int] = {}
    order = 0
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
            if item not in first_seen:
                first_seen[item] = order
                order += 1

    # Sort by fused score desc; break ties by first appearance for stable, deterministic output.
    fused = sorted(scores.keys(), key=lambda it: (-scores[it], first_seen[it]))
    return fused[:top_k] if top_k is not None else fused
