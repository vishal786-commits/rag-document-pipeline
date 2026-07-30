"""Split Markdown pages into chunks that keep their document structure.

Three ideas do the work here:

1. Headings, not character counts, decide where chunks break. A section is a
   coherent unit of meaning; 900 characters is not.
2. Markdown tables are never split mid-table. An oversized one is broken by
   rows, repeating the header row in each part so every piece stays readable.
3. Every chunk is prefixed with its heading path before being embedded, so a
   chunk that says "they must attend within 14 days" carries which policy and
   which section it came from. Both the embedding and BM25 then see those terms.
"""

import hashlib
import re
from collections import defaultdict

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from rag.catalogue import DocMeta
from rag.config import (
    BOILERPLATE_MAX_CHARS,
    BOILERPLATE_PATTERNS,
    CHUNK_OVERLAP,
    DUPLICATE_REPORT_MIN_DOCS,
    HEADER_LEVELS,
    MAX_CHUNK_CHARS,
)

LEVEL_KEYS = [level[1] for level in HEADER_LEVELS]  # ["h1", ... "h5"]


def clean_heading(text: str) -> str:
    """'**1       Scope**' -> '1 Scope'."""
    text = text.replace("**", "").replace("__", "")
    return re.sub(r"\s+", " ", text).strip()


def merge_headers(carried: dict[str, str], new: dict[str, str]) -> dict[str, str]:
    """Carry the heading path across a page break.

    MarkdownHeaderTextSplitter only knows about headings inside the text it was
    given, so a section continuing onto the next page arrives with its outer
    levels missing (or with no headers at all). Merging keeps the levels above
    whatever the new page supplies, and clears the levels below it.
    """
    if not new:
        return carried
    merged = dict(carried)
    for level in LEVEL_KEYS:
        if level in new:
            merged[level] = clean_heading(new[level])
            merged = {k: v for k, v in merged.items() if k <= level}
    return merged


def heading_path(title: str, headers: dict[str, str]) -> str:
    """'Damp Policy > 4 Responsibilities > 4.2 Repairs Team'."""
    parts = [title]
    for level in LEVEL_KEYS:
        value = headers.get(level)
        # Skip a heading that just repeats the level above it (or the title).
        if value and value.lower() != parts[-1].lower():
            parts.append(value)
    return " > ".join(parts)


def split_prose_and_tables(text: str) -> list[tuple[str, str]]:
    """Cut text into alternating ('prose' | 'table') segments.

    A table run is any group of consecutive lines starting with '|'.
    """
    segments: list[tuple[str, str]] = []
    buf: list[str] = []
    in_table = False
    for line in text.split("\n"):
        is_row = line.lstrip().startswith("|")
        if is_row != in_table:
            if buf:
                segments.append(("\n".join(buf), "table" if in_table else "prose"))
            buf = []
            in_table = is_row
        buf.append(line)
    if buf:
        segments.append(("\n".join(buf), "table" if in_table else "prose"))
    return [(t, kind) for t, kind in segments if t.strip()]


def split_table_by_rows(md_table: str) -> list[str]:
    """Break an oversized table into row groups, repeating the header row."""
    lines = [line for line in md_table.split("\n") if line.strip()]
    if len(lines) <= 2:
        return ["\n".join(lines)]

    header, rows = lines[:2], lines[2:]
    parts: list[str] = []
    buf: list[str] = []
    for row in rows:
        buf.append(row)
        if len("\n".join(header + buf)) > MAX_CHUNK_CHARS and len(buf) > 1:
            parts.append("\n".join(header + buf[:-1]))
            buf = [row]
    if buf:
        parts.append("\n".join(header + buf))
    return parts


def chunk_document(pages: list[Document], meta: DocMeta) -> list[Document]:
    """Turn one document's pages into structure-aware chunks."""
    header_splitter = MarkdownHeaderTextSplitter(HEADER_LEVELS, strip_headers=True)
    size_guard = RecursiveCharacterTextSplitter(
        chunk_size=MAX_CHUNK_CHARS,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    carried: dict[str, str] = {}
    chunks: list[Document] = []

    for page in pages:
        page_no = page.metadata["page"]
        for section in header_splitter.split_text(page.page_content):
            carried = merge_headers(carried, section.metadata)
            path = heading_path(meta.title, carried)

            for body, kind in split_prose_and_tables(section.page_content):
                if len(body) <= MAX_CHUNK_CHARS:
                    parts = [body]
                elif kind == "table":
                    parts = split_table_by_rows(body)
                else:
                    parts = size_guard.split_text(body)

                for part in parts:
                    part = part.strip()
                    if not part:
                        continue
                    chunks.append(
                        Document(
                            page_content=f"{path}\n\n{part}",
                            metadata={
                                "doc_id": meta.doc_id,
                                "source_file": meta.file.name,
                                "title": meta.title,
                                "page": page_no,
                                "heading_path": path,
                                "content_type": kind,
                                "audience": meta.audience,
                                "origin": meta.origin,
                                "status": meta.status,
                                "version": meta.version,
                                "effective": meta.effective.isoformat() if meta.effective else "",
                                "expiry": meta.expiry.isoformat() if meta.expiry else "",
                            },
                        )
                    )
    return chunks


def _body_key(chunk: Document) -> str:
    """Hash of the chunk body, ignoring the heading path, digits and punctuation.

    Stripping digits collapses 'Page 3 of 12' style variants onto one key.
    """
    body = chunk.page_content.split("\n\n", 1)[-1]
    normalised = re.sub(r"[^a-z ]", "", body.lower())
    normalised = re.sub(r"\s+", " ", normalised).strip()
    return hashlib.sha1(normalised.encode()).hexdigest()


def drop_boilerplate(chunks: list[Document]) -> tuple[list[Document], list[dict]]:
    """Remove the Aster group-entity preamble that repeats across ~20 files.

    Matched by explicit pattern, not by repetition. An earlier version dropped
    any body repeated across five or more documents and took the shared
    "3.3 The effectiveness of this policy will be continuously monitored"
    clause with it -- which is a real answer to "how is the Fire Safety Policy
    reviewed?". Repetition is not the signal; carrying no answer value is, and
    that has to be stated rather than inferred.

    Every dropped chunk is returned so the ingest report can show what went.
    """
    patterns = [re.compile(p, re.IGNORECASE) for p in BOILERPLATE_PATTERNS]

    kept: list[Document] = []
    dropped: list[dict] = []
    for chunk in chunks:
        body = chunk.page_content.split("\n\n", 1)[-1]
        is_boilerplate = len(body) <= BOILERPLATE_MAX_CHARS and any(p.search(body) for p in patterns)
        if is_boilerplate:
            dropped.append(
                {
                    "doc_id": chunk.metadata["doc_id"],
                    "page": chunk.metadata["page"],
                    "preview": " ".join(body.split())[:120],
                }
            )
        else:
            kept.append(chunk)
    return kept, dropped


def find_duplicates(chunks: list[Document]) -> list[dict]:
    """Bodies repeated across many documents, for human review.

    Reported only -- never dropped. This is where the next piece of boilerplate
    will show up, and a person should decide whether it is one.
    """
    by_key: dict[str, list[Document]] = defaultdict(list)
    for chunk in chunks:
        by_key[_body_key(chunk)].append(chunk)

    out: list[dict] = []
    for group in by_key.values():
        doc_ids = {c.metadata["doc_id"] for c in group}
        if len(doc_ids) < DUPLICATE_REPORT_MIN_DOCS:
            continue
        body = group[0].page_content.split("\n\n", 1)[-1]
        out.append(
            {
                "docs": len(doc_ids),
                "chars": len(body),
                "preview": " ".join(body.split())[:110],
            }
        )
    return sorted(out, key=lambda d: -d["docs"])


def assign_chunk_ids(chunks: list[Document]) -> list[str]:
    """Deterministic '{doc_id}#{n}' ids, so re-ingesting overwrites in place."""
    counters: dict[str, int] = defaultdict(int)
    ids: list[str] = []
    for chunk in chunks:
        doc_id = chunk.metadata["doc_id"]
        index = counters[doc_id]
        counters[doc_id] += 1
        chunk.metadata["chunk_index"] = index
        chunk.metadata["id"] = f"{doc_id}#{index}"
        ids.append(chunk.metadata["id"])
    return ids
