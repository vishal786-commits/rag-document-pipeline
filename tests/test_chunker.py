"""The chunker is pure, so all of this runs with no PDFs and no network."""

import pytest
from langchain_core.documents import Document

from rag.catalogue import DocMeta
from rag.chunker import (
    chunk_document,
    clean_heading,
    drop_boilerplate,
    find_duplicates,
    heading_path,
    merge_headers,
    split_prose_and_tables,
    split_table_by_rows,
)
from rag.config import MAX_CHUNK_CHARS


def meta(doc_id="damp-policy", title="Damp, Mould & Condensation Policy") -> DocMeta:
    from pathlib import Path

    return DocMeta(
        doc_id=doc_id,
        file=Path(f"{doc_id}.pdf"),
        title=title,
        audience="staff",
        origin="ASTER",
        status="current",
        effective=None,
        expiry=None,
        version="1.0",
        has_form=False,
        pages_expected=None,
    )


# ── Heading text ────────────────────────────────────────────────────────────
def test_clean_heading_strips_bold_and_collapses_whitespace():
    # pymupdf4llm emits headings like '# **1       Scope**'; the splitter hands
    # us the text without the '#' marker but with the bold and padding intact.
    assert clean_heading("**1       Scope**") == "1 Scope"
    assert clean_heading("  __4 Related Policies__  ") == "4 Related Policies"


# ── Carrying the heading path across page breaks ────────────────────────────
def test_merge_headers_keeps_outer_levels_when_page_supplies_only_inner():
    carried = {"h1": "Policy", "h2": "4 Responsibilities"}
    assert merge_headers(carried, {"h2": "5 Monitoring"}) == {"h1": "Policy", "h2": "5 Monitoring"}


def test_merge_headers_clears_deeper_levels_on_a_new_outer_heading():
    carried = {"h1": "Policy", "h2": "4 Responsibilities", "h3": "4.2 Repairs"}
    assert merge_headers(carried, {"h1": "Other Policy"}) == {"h1": "Other Policy"}


def test_merge_headers_carries_everything_when_page_has_no_headings():
    # A section continuing onto the next page emits no headers at all.
    carried = {"h1": "Policy", "h2": "4 Responsibilities"}
    assert merge_headers(carried, {}) == carried


def test_heading_path_skips_a_heading_that_repeats_the_title():
    assert heading_path("Fire Safety Policy", {"h1": "Fire Safety Policy", "h2": "1 Scope"}) == (
        "Fire Safety Policy > 1 Scope"
    )


# ── Tables ──────────────────────────────────────────────────────────────────
def test_split_prose_and_tables_separates_a_table_from_surrounding_prose():
    text = "Intro line.\n|a|b|\n|---|---|\n|1|2|\nClosing line."
    assert split_prose_and_tables(text) == [
        ("Intro line.", "prose"),
        ("|a|b|\n|---|---|\n|1|2|", "table"),
        ("Closing line.", "prose"),
    ]


def test_split_prose_and_tables_ignores_empty_segments():
    assert split_prose_and_tables("\n\n|a|b|\n\n") == [("|a|b|", "table")]


def test_split_table_by_rows_repeats_the_header_in_every_part():
    header = "|hazard|timescale|\n|---|---|"
    rows = "\n".join(f"|hazard {i}|{i} days|" for i in range(200))
    parts = split_table_by_rows(f"{header}\n{rows}")

    assert len(parts) > 1, "a 200-row table should be split"
    for part in parts:
        assert part.startswith("|hazard|timescale|\n|---|---|")


def test_split_table_by_rows_leaves_a_headerless_stub_alone():
    assert split_table_by_rows("|a|b|") == ["|a|b|"]


def test_a_table_is_never_split_mid_row():
    """The whole point: a chunk must never contain half a table row."""
    table = "|hazard|timescale|\n|---|---|\n" + "\n".join(
        f"|damp and mould stage {i}|{i} calendar days|" for i in range(300)
    )
    pages = [Document(page_content=f"# 4 Hazards\n\n{table}", metadata={"page": 1})]
    chunks = chunk_document(pages, meta())

    table_chunks = [c for c in chunks if c.metadata["content_type"] == "table"]
    assert table_chunks
    for chunk in table_chunks:
        body = chunk.page_content.split("\n\n", 1)[-1]
        for line in body.split("\n"):
            assert line.startswith("|") and line.endswith("|"), f"truncated row: {line!r}"


# ── Contextual headers ──────────────────────────────────────────────────────
def test_every_chunk_is_prefixed_with_its_heading_path():
    pages = [
        Document(
            page_content="# 4 Responsibilities\n\n## 4.2 Repairs Team\n\nAttend within 14 days.",
            metadata={"page": 3},
        )
    ]
    chunks = chunk_document(pages, meta())

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.page_content.startswith(
        "Damp, Mould & Condensation Policy > 4 Responsibilities > 4.2 Repairs Team"
    )
    assert "Attend within 14 days." in chunk.page_content
    assert chunk.metadata["page"] == 3


def test_heading_path_survives_a_page_break():
    pages = [
        Document(page_content="# 4 Responsibilities\n\nFirst part.", metadata={"page": 1}),
        Document(page_content="Continues here with no heading.", metadata={"page": 2}),
    ]
    chunks = chunk_document(pages, meta())

    assert len(chunks) == 2
    assert chunks[1].metadata["page"] == 2
    assert chunks[1].metadata["heading_path"].endswith("4 Responsibilities")


def test_oversized_prose_is_split_but_each_part_keeps_the_header():
    long_prose = "This sentence is repeated to overflow the size guard. " * 60
    pages = [Document(page_content=f"# 2 Policy Statement\n\n{long_prose}", metadata={"page": 1})]
    chunks = chunk_document(pages, meta())

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.page_content.startswith("Damp, Mould & Condensation Policy > 2 Policy Statement")
        assert len(chunk.page_content) <= MAX_CHUNK_CHARS + 200  # header + overlap headroom


def test_chunk_metadata_carries_the_document_fields():
    pages = [Document(page_content="# 1 Scope\n\nBody text.", metadata={"page": 1})]
    chunk = chunk_document(pages, meta())[0]

    assert chunk.metadata["doc_id"] == "damp-policy"
    assert chunk.metadata["audience"] == "staff"
    assert chunk.metadata["status"] == "current"
    assert chunk.metadata["origin"] == "ASTER"


# ── Boilerplate ─────────────────────────────────────────────────────────────
def _chunk(doc_id: str, body: str) -> Document:
    return Document(
        page_content=f"Some Policy > 4 Related\n\n{body}",
        metadata={"doc_id": doc_id, "page": 1},
    )


def test_drop_boilerplate_removes_the_group_entity_preamble():
    chunks = [
        _chunk("a", "Aster Group is the overarching brand name of Aster Group Ltd."),
        _chunk("b", "Report damp and mould within 14 calendar days."),
    ]
    kept, dropped = drop_boilerplate(chunks)

    assert len(kept) == 1
    assert "14 calendar days" in kept[0].page_content
    assert len(dropped) == 1
    assert dropped[0]["doc_id"] == "a"


def test_drop_boilerplate_keeps_the_shared_monitoring_clause():
    """This clause is repeated across five safety policies but answers a real
    question ('how is this policy reviewed?'), so repetition must not remove it."""
    clause = (
        "3.3 The effectiveness of this policy will be continuously monitored, "
        "and the embedding of the policy scrutinised after 12 months."
    )
    chunks = [_chunk(f"policy-{i}", clause) for i in range(5)]
    kept, dropped = drop_boilerplate(chunks)

    assert len(kept) == 5
    assert dropped == []


def test_drop_boilerplate_keeps_a_long_chunk_that_merely_mentions_the_brand():
    body = "overarching company brand " + ("substantive policy content follows. " * 40)
    kept, dropped = drop_boilerplate([_chunk("a", body)])

    assert len(kept) == 1, "a long chunk is content even if it mentions the preamble"
    assert dropped == []


def test_find_duplicates_reports_the_monitoring_clause_without_dropping_it():
    clause = "The effectiveness of this policy will be continuously monitored."
    chunks = [_chunk(f"policy-{i}", clause) for i in range(5)]

    duplicates = find_duplicates(chunks)
    assert len(duplicates) == 1
    assert duplicates[0]["docs"] == 5


def test_find_duplicates_ignores_repetition_inside_one_document():
    clause = "The effectiveness of this policy will be continuously monitored."
    chunks = [_chunk("same-doc", clause) for _ in range(9)]

    assert find_duplicates(chunks) == []
