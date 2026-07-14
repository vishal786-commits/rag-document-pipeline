"""
Per-namespace corpus store.

Hybrid retrieval needs the *full* set of chunk texts for a document so BM25 can
score every chunk — not just the ones dense retrieval already surfaced. Pinecone
holds the vectors but is not a convenient store for "give me every chunk in this
namespace", so we keep the chunk texts here, keyed by the same namespace used for
Pinecone (the upload session id).

The store is an in-process cache backed by a small JSON file per namespace, so the
corpus survives a container restart even though Pinecone is the source of truth for
vectors. For a single-replica deployment this is sufficient; a multi-replica setup
would back this with a shared store (Redis / S3 / Pinecone metadata scan).
"""

import json
import os
from pathlib import Path
from typing import List

_CORPUS_DIR = Path(os.getenv("CORPUS_DIR", ".corpus"))
_cache: dict[str, List[str]] = {}


def _path(namespace: str) -> Path:
    # Namespaces are uuids, but sanitize defensively so they're always valid filenames.
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in namespace) or "default"
    return _CORPUS_DIR / f"{safe}.json"


def save_corpus(namespace: str, chunks: List[str]) -> None:
    """Persist the full chunk list for a namespace (called once at ingest time)."""
    _cache[namespace] = chunks
    try:
        _CORPUS_DIR.mkdir(parents=True, exist_ok=True)
        with open(_path(namespace), "w", encoding="utf-8") as f:
            json.dump(chunks, f)
    except Exception as e:
        # Disk persistence is best-effort; the in-memory cache still serves this process.
        print(f"[corpus_store] Could not persist corpus for '{namespace}': {e}")


def get_corpus(namespace: str) -> List[str]:
    """Return the full chunk list for a namespace, or [] if it isn't available."""
    if namespace in _cache:
        return _cache[namespace]
    path = _path(namespace)
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                chunks = json.load(f)
            _cache[namespace] = chunks
            return chunks
        except Exception as e:
            print(f"[corpus_store] Could not load corpus for '{namespace}': {e}")
    return []
