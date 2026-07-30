"""Hybrid retrieval: Pinecone dense + BM25 sparse, fused with Reciprocal Rank Fusion.

Dense retrieval is strong on meaning but can miss a chunk whose relevance comes
from an exact term the embedding under-weights ("Section 20", "LOLER", "HHSRS").
BM25 over the whole corpus produces an independent keyword ranking, and RRF
combines the two so a chunk ranked highly by *either* signal surfaces.

Two things this fixes versus the previous implementation:

  - BM25 is fitted once, at startup. It used to be re-fitted over every chunk in
    the corpus on every single query.
  - Fusion is keyed on the stable vector id rather than on raw chunk text, so
    metadata survives fusion. That is what makes '[source_file p.N]' citations
    possible at all; the old version returned bare strings and threw away the
    page, the source file, and the score.
"""

import json
from pathlib import Path

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from rag import config


class RetrieverError(RuntimeError):
    """Raised when the retriever cannot be built."""


def tokenize(text: str) -> list[str]:
    return text.lower().split()


def normalise(doc: Document) -> Document:
    """Coerce numeric metadata back to int.

    Pinecone stores every number as a float, so a page comes back as 2.0 and
    citations render as "p.2.0". The BM25 half reads the same chunks from JSON
    and gets real ints, so without this the two halves disagree on type.
    """
    for key in ("page", "chunk_index"):
        value = doc.metadata.get(key)
        if isinstance(value, float):
            doc.metadata[key] = int(value)
    return doc


def load_chunks(path: Path) -> list[Document]:
    """Read the committed chunk snapshot written by rag.ingest.

    Pinecone cannot cheaply enumerate a namespace, so BM25 needs its own copy
    of the corpus. This file is that copy.
    """
    if not path.exists():
        raise RetrieverError(
            f"Chunk snapshot not found: {path}. Run `python -m rag.ingest` first."
        )
    docs: list[Document] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        docs.append(Document(page_content=record["text"], metadata=record["metadata"]))
    if not docs:
        raise RetrieverError(f"{path} is empty.")
    return docs


def fuse(
    rankings: list[list[Document]], k: int, damping: int = config.RRF_DAMPING
) -> list[tuple[Document, float]]:
    """Reciprocal Rank Fusion over Documents, keyed on the stable vector id.

    score(d) = sum over rankings r of 1 / (damping + rank_r(d)).
    Ties break by first appearance, so the output is deterministic.
    """
    scores: dict[str, float] = {}
    keep: dict[str, Document] = {}
    order: dict[str, int] = {}
    for ranking in rankings:
        for rank, doc in enumerate(ranking, start=1):
            vid = doc.metadata["id"]
            scores[vid] = scores.get(vid, 0.0) + 1.0 / (damping + rank)
            keep.setdefault(vid, doc)
            order.setdefault(vid, len(order))

    ranked = sorted(scores, key=lambda vid: (-scores[vid], order[vid]))
    return [(keep[vid], scores[vid]) for vid in ranked[:k]]


def build_filter(audience: str | None, status: str | None, doc_id: str | None) -> dict | None:
    """Pinecone metadata filter, or None when nothing is being filtered."""
    clauses: dict[str, dict] = {}
    if audience:
        # Reference material is statutory context and is useful to everyone.
        clauses["audience"] = {"$in": [audience, "reference"]}
    if status:
        clauses["status"] = {"$eq": status}
    if doc_id:
        clauses["doc_id"] = {"$eq": doc_id}
    return clauses or None


def passes(doc: Document, audience: str | None, status: str | None, doc_id: str | None) -> bool:
    """The same filter, applied client-side for the BM25 half."""
    meta = doc.metadata
    if audience and meta.get("audience") not in (audience, "reference"):
        return False
    if status and meta.get("status") != status:
        return False
    if doc_id and meta.get("doc_id") != doc_id:
        return False
    return True


class KBRetriever:
    """Build once, at application startup. Never per request."""

    def __init__(self, chunks_path: Path | None = None):
        from langchain_openai import OpenAIEmbeddings
        from langchain_pinecone import PineconeVectorStore
        from pinecone import Pinecone

        config.require("OPENAI_API_KEY", config.OPENAI_API_KEY)
        config.require("PINECONE_API_KEY", config.PINECONE_API_KEY)
        index_name = config.require("PINECONE_INDEX_NAME", config.PINECONE_INDEX_NAME)

        self.docs = load_chunks(chunks_path or config.CHUNKS_PATH)
        self.bm25 = BM25Okapi([tokenize(d.page_content) for d in self.docs])

        embeddings = OpenAIEmbeddings(model=config.EMBED_MODEL, api_key=config.OPENAI_API_KEY)
        index = Pinecone(api_key=config.PINECONE_API_KEY).Index(index_name)
        self.store = PineconeVectorStore(
            index=index, embedding=embeddings, namespace=config.PINECONE_NAMESPACE
        )
        self._index = index

    def search(
        self,
        query: str,
        k: int = config.FINAL_K,
        audience: str | None = None,
        status: str | None = None,
        doc_id: str | None = None,
    ) -> list[tuple[Document, float]]:
        dense = [
            normalise(d)
            for d in self.store.similarity_search(
                query,
                k=config.CANDIDATE_K,
                filter=build_filter(audience, status, doc_id),
            )
        ]

        scores = self.bm25.get_scores(tokenize(query))
        ranked_idx = sorted(range(len(self.docs)), key=lambda i: -scores[i])
        sparse: list[Document] = []
        for i in ranked_idx:
            if len(sparse) >= config.CANDIDATE_K:
                break
            if passes(self.docs[i], audience, status, doc_id):
                sparse.append(self.docs[i])

        return fuse([dense, sparse], k=k)

    def policies(self) -> list[dict]:
        """One row per document, from the chunk metadata already in memory."""
        by_doc: dict[str, dict] = {}
        for doc in self.docs:
            meta = doc.metadata
            entry = by_doc.setdefault(
                meta["doc_id"],
                {
                    "doc_id": meta["doc_id"],
                    "title": meta["title"],
                    "source_file": meta["source_file"],
                    "audience": meta["audience"],
                    "origin": meta["origin"],
                    "status": meta["status"],
                    "version": meta["version"],
                    "effective": meta.get("effective") or None,
                    "expiry": meta.get("expiry") or None,
                    "pages": 0,
                    "chunks": 0,
                },
            )
            entry["chunks"] += 1
            entry["pages"] = max(entry["pages"], meta["page"])
        return sorted(by_doc.values(), key=lambda d: d["title"])

    def audience_counts(self) -> dict[str, int]:
        """Documents per audience. Checked at startup because an audience with
        no documents makes filtering on it silently return almost nothing."""
        counts: dict[str, int] = {}
        for policy in self.policies():
            counts[policy["audience"]] = counts.get(policy["audience"], 0) + 1
        return counts

    def namespace_count(self) -> int | None:
        """Live vector count, for the startup consistency check."""
        try:
            stats = self._index.describe_index_stats()
            ns = (stats.get("namespaces") or {}).get(config.PINECONE_NAMESPACE)
            return ns["vector_count"] if ns else 0
        except Exception:
            return None
