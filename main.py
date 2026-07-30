"""FastAPI service over the Aster policy knowledge base.

There is no upload endpoint. The previous version ingested each uploaded PDF
into a namespace keyed by a per-session UUID, while the knowledge base lived in
a fixed namespace that nothing ever queried -- so no request could reach it.
One corpus, one namespace, one metadata schema.

Conversation history is supplied by the client rather than held in process, so
the service is stateless and works behind more than one replica.
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from rag import config
from rag.generate import answer as generate_answer
from rag.retriever import KBRetriever

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("docmind")

state: dict[str, KBRetriever | None] = {"retriever": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build the retriever once. Fitting BM25 per request was the old behaviour."""
    try:
        retriever = KBRetriever()
        state["retriever"] = retriever
        log.info("Loaded %d chunks for BM25.", len(retriever.docs))

        counts = retriever.audience_counts()
        log.info("Audience distribution: %s", counts)
        if not counts.get("tenant"):
            log.warning(
                "No document is tenant-facing, so audience='tenant' returns only the %d "
                "reference documents. The one tenant-facing document was removed from the "
                "corpus; treat this filter as inactive until one is added.",
                counts.get("reference", 0),
            )

        live = retriever.namespace_count()
        if live is None:
            log.warning("Could not read Pinecone stats; skipping the consistency check.")
        elif live != len(retriever.docs):
            log.warning(
                "MISMATCH: %d chunks on disk but %d vectors in namespace %r. "
                "Re-run `python -m rag.ingest --fresh`.",
                len(retriever.docs),
                live,
                config.PINECONE_NAMESPACE,
            )
        else:
            log.info("Index consistent: %d vectors in %r.", live, config.PINECONE_NAMESPACE)
    except Exception as e:
        # /health must keep answering so the container health check still passes
        # and the failure is visible in logs rather than as a crash loop.
        log.error("Retriever unavailable: %s: %s", type(e).__name__, e)
    yield


app = FastAPI(title="Aster Policy Assistant", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    audience: str | None = Field(default=None, description="staff | tenant")
    status: str | None = Field(default=None, description="current | expired")
    doc_id: str | None = Field(default=None, description="restrict to one policy")
    history: list[tuple[str, str]] = Field(default_factory=list)


def get_retriever() -> KBRetriever:
    retriever = state["retriever"]
    if retriever is None:
        raise HTTPException(503, "Knowledge base unavailable; check the service logs.")
    return retriever


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "docmind",
        "knowledge_base": "ready" if state["retriever"] else "unavailable",
        "timestamp": time.time(),
    }


@app.get("/")
async def root():
    return {"message": "Aster Policy Assistant. POST /ask, GET /policies."}


@app.get("/policies")
async def policies():
    """What the knowledge base contains -- questions retrieval cannot answer."""
    return {"policies": get_retriever().policies()}


@app.post("/ask")
async def ask(request: AskRequest):
    retriever = get_retriever()
    started = time.perf_counter()

    hits = retriever.search(
        request.question,
        audience=request.audience,
        status=request.status,
        doc_id=request.doc_id,
    )
    result = generate_answer(request.question, hits, history=request.history)
    result["latency_ms"] = round((time.perf_counter() - started) * 1000)
    return result
