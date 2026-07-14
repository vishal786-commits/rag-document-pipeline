"""
Retrieval evaluation harness for the DocMind RAG pipeline.

Measures retrieval quality on a labeled question set against the sample
insurance policy, comparing three retrieval strategies at a fixed cutoff k:

    A. Dense-only    : cosine top-k over text-embedding-3-small vectors
    B. Dense+rerank  : dense retrieves a candidate pool, BM25 reranks those candidates
    C. Hybrid (RRF)  : independent dense ranking and full-corpus BM25 ranking, fused with
                       Reciprocal Rank Fusion (this is the strategy the production pipeline uses)

Why local cosine instead of live Pinecone:
    Pinecone ranks the exact same embedding vectors by cosine similarity. Computing
    cosine locally reproduces that ranking faithfully while keeping the eval
    deterministic, offline-repeatable, and free of any writes to the shared index.

Reuses the real pipeline code (src.pdfreader / src.chunker / src.embedder /
src.query.rerank_with_bm25) so the reported numbers reflect the actual system.

Usage:
    python -m eval.retrieval_eval --validate     # offline: check gold phrases exist in chunks (no API key needed)
    python -m eval.retrieval_eval                # full eval (needs OPENAI_API_KEY)
    python -m eval.retrieval_eval --k 3 --k 5    # evaluate at multiple cutoffs
"""

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
from pathlib import Path

# Make `src` importable when run as a module or a script.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.pdfreader import read_pdf
from src.chunker import chunk_pages
from src.query import rerank_with_bm25
from src.hybrid import bm25_rank, reciprocal_rank_fusion

EVAL_DIR = Path(__file__).resolve().parent
CACHE_DIR = EVAL_DIR / ".cache"
EMBED_MODEL = "text-embedding-3-small"


# ----------------------------------------------------------------------------
# Relevance judging
# ----------------------------------------------------------------------------
def _norm(text: str) -> str:
    """Lowercase and collapse all whitespace so PDF line breaks don't break matching."""
    return re.sub(r"\s+", " ", text).strip().lower()


def is_relevant(chunk: str, gold: str) -> bool:
    return _norm(gold) in _norm(chunk)


# ----------------------------------------------------------------------------
# Data loading + chunking (offline, no API key required)
# ----------------------------------------------------------------------------
def load_eval_set() -> dict:
    with open(EVAL_DIR / "eval_set.json", encoding="utf-8") as f:
        return json.load(f)


async def build_chunks(pdf_path: str) -> list[str]:
    pages = await read_pdf(pdf_path)
    return await chunk_pages(pages)


def validate(chunks: list[str], questions: list[dict]) -> bool:
    """Confirm every gold phrase is present in at least one chunk. Offline sanity check."""
    ok = True
    for q in questions:
        hits = sum(is_relevant(c, q["gold"]) for c in chunks)
        status = "OK " if hits else "MISSING"
        if not hits:
            ok = False
        print(f"  [{status}] q{q['id']:>2}  ({hits} relevant chunk(s))  gold={q['gold']!r}")
    return ok


# ----------------------------------------------------------------------------
# Embeddings (with on-disk cache keyed by content + model)
# ----------------------------------------------------------------------------
def _cache_key(items: list[str]) -> str:
    h = hashlib.sha256()
    h.update(EMBED_MODEL.encode())
    for it in items:
        h.update(b"\x00")
        h.update(it.encode("utf-8"))
    return h.hexdigest()[:16]


def _load_cache(key: str):
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def _save_cache(key: str, vectors) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    with open(CACHE_DIR / f"{key}.json", "w", encoding="utf-8") as f:
        json.dump(vectors, f)


async def embed_all(chunks: list[str], questions: list[dict]):
    """Embed chunks and questions once; cache to disk so re-runs are free and deterministic."""
    from src.embedder import embed_chunks  # imported lazily so --validate needs no API key

    ckey = _cache_key(chunks)
    chunk_vecs = _load_cache("chunks_" + ckey)
    if chunk_vecs is None:
        print(f"  embedding {len(chunks)} chunks via {EMBED_MODEL} ...")
        chunk_vecs = await embed_chunks(chunks)
        _save_cache("chunks_" + ckey, chunk_vecs)
    else:
        print(f"  loaded {len(chunk_vecs)} chunk embeddings from cache")

    q_texts = [q["question"] for q in questions]
    qkey = _cache_key(q_texts)
    q_vecs = _load_cache("queries_" + qkey)
    if q_vecs is None:
        print(f"  embedding {len(q_texts)} queries ...")
        q_vecs = await embed_chunks(q_texts)  # same per-item embedding path as chunks
        _save_cache("queries_" + qkey, q_vecs)
    else:
        print(f"  loaded {len(q_vecs)} query embeddings from cache")

    return chunk_vecs, q_vecs


# ----------------------------------------------------------------------------
# Retrieval (pure-python cosine; mirrors Pinecone cosine ranking)
# ----------------------------------------------------------------------------
def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _norm2(a):
    return sum(x * x for x in a) ** 0.5


def cosine_rank(query_vec, chunk_vecs) -> list[int]:
    """Return chunk indices sorted by descending cosine similarity to the query."""
    qn = _norm2(query_vec) or 1e-12
    sims = []
    for i, cv in enumerate(chunk_vecs):
        cn = _norm2(cv) or 1e-12
        sims.append((_dot(query_vec, cv) / (qn * cn), i))
    sims.sort(reverse=True)
    return [i for _, i in sims]


# ----------------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------------
def score(chunks, gold, ranked_idx, k):
    """Return (hit, reciprocal_rank) for a ranked list of chunk indices at cutoff k."""
    hit = 0
    rr = 0.0
    for rank, idx in enumerate(ranked_idx[:k], start=1):
        if is_relevant(chunks[idx], gold):
            hit = 1
            rr = 1.0 / rank
            break
    return hit, rr


STRATEGIES = ("dense", "rerank", "hybrid_rrf")


def _score_ranked_texts(chunks, gold, ranked_texts, k):
    """Score a ranking given as chunk texts (map to indices, then score at k)."""
    idx = [chunks.index(t) for t in ranked_texts]
    return score(chunks, gold, idx, k)


def evaluate(chunks, chunk_vecs, q_vecs, questions, k, candidate_pool):
    """
    For each question, score three strategies at cutoff k:
      dense      : cosine top-k
      rerank     : cosine top-`candidate_pool` -> BM25 rerank of those candidates -> top-k
      hybrid_rrf : RRF( full cosine ranking , full-corpus BM25 ranking ) -> top-k  (production path)
    """
    agg = {s: {"hit": 0, "mrr": 0.0} for s in STRATEGIES}
    for q, qv in zip(questions, q_vecs):
        gold = q["gold"]
        dense_ranked_idx = cosine_rank(qv, chunk_vecs)
        dense_ranked_texts = [chunks[i] for i in dense_ranked_idx]

        # Dense-only
        d_hit, d_rr = score(chunks, gold, dense_ranked_idx, k)

        # Dense candidates -> BM25 rerank (the legacy two-stage path)
        pool_texts = dense_ranked_texts[:candidate_pool]
        rr_texts = rerank_with_bm25(q["question"], pool_texts, top_k=k)
        r_hit, r_rr = _score_ranked_texts(chunks, gold, rr_texts, k)

        # Hybrid RRF: fuse full dense ranking with full-corpus BM25 ranking (production path)
        sparse_ranked = bm25_rank(q["question"], chunks)[:candidate_pool]
        fused_texts = reciprocal_rank_fusion(
            [dense_ranked_texts[:candidate_pool], sparse_ranked], top_k=k
        )
        h_hit, h_rr = _score_ranked_texts(chunks, gold, fused_texts, k)

        for strat, (hit, rr) in zip(
            STRATEGIES, [(d_hit, d_rr), (r_hit, r_rr), (h_hit, h_rr)]
        ):
            agg[strat]["hit"] += hit
            agg[strat]["mrr"] += rr

    n = len(questions)
    for s in agg.values():
        s["hit"] /= n
        s["mrr"] /= n
    return agg


# ----------------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="RAG retrieval evaluation")
    ap.add_argument("--validate", action="store_true", help="offline: check gold phrases exist in chunks")
    ap.add_argument("--k", type=int, action="append", help="cutoff(s) to evaluate at (default 3 and 5)")
    ap.add_argument("--pool", type=int, default=None, help="dense candidate pool size for reranking (default: all chunks)")
    args = ap.parse_args()
    ks = args.k or [3, 5]

    data = load_eval_set()
    questions = data["questions"]
    pdf_path = str(ROOT / data["document"])

    print(f"Document: {data['document']}")
    chunks = asyncio.run(build_chunks(pdf_path))
    print(f"Chunks produced: {len(chunks)} (chunk_size=900, overlap=150)\n")

    print("Validating gold phrases against chunks (offline):")
    all_present = validate(chunks, questions)
    print(f"  -> {'all gold phrases found' if all_present else 'SOME GOLD PHRASES MISSING — fix eval_set.json'}\n")
    if args.validate:
        sys.exit(0 if all_present else 1)

    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set — cannot run the embedding stage.")
        print("Set it in your .env or environment, then re-run: python -m eval.retrieval_eval")
        sys.exit(2)

    print("Embedding (cached after first run):")
    chunk_vecs, q_vecs = asyncio.run(embed_all(chunks, questions))
    print()

    pool = args.pool or len(chunks)
    print(f"Retrieval: dense candidate pool = {pool} chunks, then BM25 rerank\n")

    print(f"{'k':>3} | {'strategy':<11} | {'Hit@k / Recall@k':>16} | {'MRR@k':>7}")
    print("-" * 52)
    results = {}
    for k in ks:
        agg = evaluate(chunks, chunk_vecs, q_vecs, questions, k, pool)
        results[k] = agg
        for strat in STRATEGIES:
            print(f"{k:>3} | {strat:<11} | {agg[strat]['hit']*100:>14.1f}% | {agg[strat]['mrr']:>7.3f}")
        gain = (agg["hybrid_rrf"]["hit"] - agg["dense"]["hit"]) * 100
        print(f"    -> hybrid RRF delta vs dense on Hit@{k}: {gain:+.1f} points\n")

    # Headline line for the resume, using the smallest k (fusion helps most at tight cutoffs).
    k0 = min(ks)
    d = results[k0]["dense"]["hit"] * 100
    h = results[k0]["hybrid_rrf"]["hit"] * 100
    dm = results[k0]["dense"]["mrr"]
    hm = results[k0]["hybrid_rrf"]["mrr"]
    print("Headline:")
    print(f"  Recall@{k0}: {d:.0f}% (dense) -> {h:.0f}% (hybrid dense+BM25 with RRF); "
          f"MRR@{k0} {dm:.2f} -> {hm:.2f}, on a {len(questions)}-question labeled set.")


if __name__ == "__main__":
    main()
