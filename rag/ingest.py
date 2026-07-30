"""Build the knowledge-base index.

    python -m rag.ingest --dry-run      parse, chunk and report; no API calls
    python -m rag.ingest                embed and upsert
    python -m rag.ingest --fresh        clear the namespace first
    python -m rag.ingest --only <id>    restrict to one doc_id (debugging)

Output is deliberately ASCII-only: the Windows console defaults to cp1252 and
a stray arrow or bullet crashes the run half way through.
"""

import argparse
import hashlib
import json
import sys
import time
from datetime import date, datetime, timezone

from rag import config
from rag.catalogue import CatalogueError, load_catalogue
from rag.chunker import assign_chunk_ids, chunk_document, drop_boilerplate, find_duplicates
from rag.loader import LoaderError, drop_form_tail, load_pages


def prepare(only: str | None = None) -> tuple[list, list[dict], list[dict], list[dict]]:
    """Parse and chunk every document.

    Returns (chunks, per-doc stats, boilerplate dropped, duplicate candidates).
    """
    catalogue = load_catalogue(config.KB_DIR, config.SUMMARY_PATH, today=date.today())
    if only:
        catalogue = [m for m in catalogue if m.doc_id == only]
        if not catalogue:
            raise CatalogueError(f"No document with doc_id {only!r}.")

    all_chunks = []
    stats: list[dict] = []
    for meta in catalogue:
        pages, blank = load_pages(meta.file)
        pages, form_pages = drop_form_tail(pages, meta.has_form, meta.file.name)
        chunks = chunk_document(pages, meta)
        all_chunks.extend(chunks)
        stats.append(
            {
                "doc_id": meta.doc_id,
                "file": meta.file.name,
                "audience": meta.audience,
                "status": meta.status,
                "pages_kept": len(pages),
                "pages_blank": blank,
                "pages_form": form_pages,
                "chunks": len(chunks),
                "tables": sum(1 for c in chunks if c.metadata["content_type"] == "table"),
            }
        )
        print(
            f"  {meta.file.name[:48]:<48} {len(pages):>3}pp -> {len(chunks):>4} chunks"
            f"  ({stats[-1]['tables']} table)"
        )

    kept, dropped = drop_boilerplate(all_chunks)
    duplicates = find_duplicates(kept)
    assign_chunk_ids(kept)
    return kept, stats, dropped, duplicates


def embed_and_upsert(chunks: list, fresh: bool) -> None:
    from langchain_openai import OpenAIEmbeddings
    from langchain_pinecone import PineconeVectorStore
    from pinecone import Pinecone

    config.require("OPENAI_API_KEY", config.OPENAI_API_KEY)
    config.require("PINECONE_API_KEY", config.PINECONE_API_KEY)
    index_name = config.require("PINECONE_INDEX_NAME", config.PINECONE_INDEX_NAME)

    embeddings = OpenAIEmbeddings(
        model=config.EMBED_MODEL,
        api_key=config.OPENAI_API_KEY,
        chunk_size=config.EMBED_BATCH,
    )

    # One explicit dimension check, so a model-name typo cannot silently fill
    # the index with vectors of the wrong width.
    probe = embeddings.embed_query("dimension probe")
    if len(probe) != config.EMBED_DIM:
        raise RuntimeError(
            f"{config.EMBED_MODEL} returned {len(probe)}-dim vectors, expected {config.EMBED_DIM}."
        )

    index = Pinecone(api_key=config.PINECONE_API_KEY).Index(index_name)
    namespace = config.PINECONE_NAMESPACE

    if fresh:
        print(f"\nClearing namespace {namespace!r} ...")
        try:
            index.delete(delete_all=True, namespace=namespace)
        except Exception as e:
            # A namespace that does not exist yet is not an error.
            print(f"  (nothing to clear: {type(e).__name__})")
        _wait_for_count(index, namespace, 0, timeout=60)

    store = PineconeVectorStore(index=index, embedding=embeddings, namespace=namespace)
    ids = [c.metadata["id"] for c in chunks]

    print(f"Embedding and upserting {len(chunks)} chunks ...")
    store.add_documents(chunks, ids=ids, batch_size=100)

    print("Verifying vector count ...")
    actual = _wait_for_count(index, namespace, len(chunks), timeout=120)
    if actual != len(chunks):
        raise RuntimeError(
            f"Upsert verification failed: namespace {namespace!r} holds {actual} vectors, "
            f"expected {len(chunks)}."
        )
    print(f"  confirmed {actual} vectors in namespace {namespace!r}")


def _wait_for_count(index, namespace: str, expected: int, timeout: int) -> int:
    """Poll describe_index_stats until the count matches. Stats are eventually
    consistent, so a single check would produce false failures."""
    deadline = time.time() + timeout
    actual = -1
    while time.time() < deadline:
        stats = index.describe_index_stats()
        ns = stats.get("namespaces", {}).get(namespace)
        actual = ns["vector_count"] if ns else 0
        if actual == expected:
            return actual
        time.sleep(3)
    return actual


def write_chunks(chunks: list) -> str:
    """Write the chunk snapshot used by BM25 at runtime, the eval, and CI."""
    config.CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(
            {"id": c.metadata["id"], "text": c.page_content, "metadata": c.metadata},
            ensure_ascii=False,
        )
        for c in chunks
    ]
    payload = "\n".join(lines) + "\n"
    config.CHUNKS_PATH.write_text(payload, encoding="utf-8")

    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    config.CHUNKS_META_PATH.write_text(
        json.dumps(
            {
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "namespace": config.PINECONE_NAMESPACE,
                "chunk_count": len(chunks),
                "embed_model": config.EMBED_MODEL,
                "sha256": digest,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return digest


def write_report(
    chunks: list, stats: list[dict], dropped: list[dict], duplicates: list[dict], executed: bool
) -> None:
    total_tables = sum(s["tables"] for s in stats)
    blank = [(s["file"], s["pages_blank"]) for s in stats if s["pages_blank"]]
    forms = [(s["file"], s["pages_form"]) for s in stats if s["pages_form"]]

    lines = [
        "# Ingest Result",
        "",
        f"> Run: {datetime.now(timezone.utc).isoformat()} · "
        f"{'executed' if executed else 'DRY RUN (no vectors written)'}",
        f"> Parser: pymupdf4llm · Chunking: heading-aware, max {config.MAX_CHUNK_CHARS} chars",
        f"> Namespace: `{config.PINECONE_NAMESPACE}` · Embeddings: `{config.EMBED_MODEL}`",
        "",
        "## Totals",
        "",
        f"- Documents: **{len(stats)}**",
        f"- Chunks: **{len(chunks)}**",
        f"- Table chunks: **{total_tables}**",
        f"- Boilerplate chunks dropped: **{len(dropped)}**",
        f"- Blank pages skipped: **{sum(len(s['pages_blank']) for s in stats)}**",
        f"- Form pages dropped: **{sum(len(s['pages_form']) for s in stats)}**",
        "",
        "## Per document",
        "",
        "| doc_id | audience | status | pages | chunks | tables |",
        "|--------|----------|--------|------:|-------:|-------:|",
    ]
    for s in stats:
        lines.append(
            f"| {s['doc_id']} | {s['audience']} | {s['status']} | "
            f"{s['pages_kept']} | {s['chunks']} | {s['tables']} |"
        )

    lines += ["", "## Pages skipped", ""]
    lines += [f"- blank/image-only: `{f}` pages {p}" for f, p in blank] or ["- blank/image-only: none"]
    lines += [f"- form tail: `{f}` pages {p}" for f, p in forms] or ["- form tail: none"]

    lines += [
        "",
        "## Boilerplate dropped",
        "",
        f"Chunks matching {config.BOILERPLATE_PATTERNS} and no longer than "
        f"{config.BOILERPLATE_MAX_CHARS} characters. Every drop is listed so the rule can be "
        "audited; if anything substantive appears here, tighten the pattern.",
        "",
    ]
    if dropped:
        lines += ["| doc_id | page | preview |", "|--------|-----:|---------|"]
        lines += [f"| {d['doc_id']} | {d['page']} | {d['preview']} |" for d in dropped]
    else:
        lines.append("_Nothing dropped._")

    lines += [
        "",
        "## Duplicate review candidates",
        "",
        f"Bodies repeated verbatim across at least {config.DUPLICATE_REPORT_MIN_DOCS} distinct "
        "documents that were **kept**. These are templated clauses; some carry real answer value "
        "(a monitoring or review commitment) and some do not. Nothing here is dropped "
        "automatically -- if one of these is pure boilerplate, add a pattern to "
        "`BOILERPLATE_PATTERNS` in `rag/config.py`.",
        "",
    ]
    if duplicates:
        lines += ["| docs | chars | preview |", "|-----:|------:|---------|"]
        lines += [f"| {d['docs']} | {d['chars']} | {d['preview']} |" for d in duplicates]
    else:
        lines.append("_No cross-document duplicates above the threshold._")

    config.INGEST_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest the knowledge base.")
    parser.add_argument("--dry-run", action="store_true", help="parse and chunk only, no API calls")
    parser.add_argument("--fresh", action="store_true", help="clear the namespace before upserting")
    parser.add_argument("--only", metavar="DOC_ID", help="restrict to one document")
    args = parser.parse_args(argv)

    try:
        print("Parsing and chunking ...")
        chunks, stats, dropped, duplicates = prepare(only=args.only)
    except (CatalogueError, LoaderError) as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        return 1

    tables = sum(s["tables"] for s in stats)
    print(
        f"\n{len(stats)} documents -> {len(chunks)} chunks "
        f"({tables} table, {len(dropped)} boilerplate dropped, "
        f"{len(duplicates)} duplicate candidates to review)"
    )

    if not args.dry_run:
        embed_and_upsert(chunks, fresh=args.fresh)
        digest = write_chunks(chunks)
        print(f"Wrote {config.CHUNKS_PATH} (sha256 {digest[:12]})")

    write_report(chunks, stats, dropped, duplicates, executed=not args.dry_run)
    print(f"Wrote {config.INGEST_REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
