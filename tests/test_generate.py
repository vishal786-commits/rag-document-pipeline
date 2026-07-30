"""Citation parsing and the expiry banner are pure -- no LLM call involved."""

from langchain_core.documents import Document

from rag.generate import expired_warning, format_context, parse_citations


def hit(n: int, **meta) -> tuple[Document, float]:
    base = {
        "id": f"policy#{n}",
        "doc_id": "fire-safety-policy",
        "title": "Fire Safety Policy",
        "source_file": "Fire Safety Policy.pdf",
        "page": n,
        "heading_path": "Fire Safety Policy > 1 Scope",
        "status": "current",
        "expiry": "2027-01-01",
    }
    base.update(meta)
    return Document(page_content=f"body {n}", metadata=base), 0.5


def test_format_context_numbers_blocks_and_tags_the_source():
    context = format_context([hit(1), hit(2)])

    assert "[1] Fire Safety Policy.pdf p.1" in context
    assert "[2] Fire Safety Policy.pdf p.2" in context


def test_format_context_marks_expired_sources_for_the_model():
    context = format_context([hit(1, status="expired", expiry="2026-05-31")])
    assert "(EXPIRED 2026-05-31)" in context


def test_parse_citations_maps_markers_back_to_sources():
    citations = parse_citations("Yes [2]. See also [1].", [hit(1), hit(2), hit(3)])

    assert [c["n"] for c in citations] == [2, 1]
    assert all(not c["inferred"] for c in citations)


def test_parse_citations_drops_hallucinated_markers():
    """[9] does not exist; it must not become a citation."""
    citations = parse_citations("Answer [9] and [1].", [hit(1), hit(2)])

    assert [c["n"] for c in citations] == [1]


def test_parse_citations_deduplicates_repeated_markers():
    citations = parse_citations("[1] and again [1].", [hit(1)])
    assert len(citations) == 1


def test_parse_citations_falls_back_to_all_sources_marked_inferred():
    """An uncited answer is still grounded in something; an empty list would
    read as grounded in nothing."""
    citations = parse_citations("No markers here.", [hit(1), hit(2)])

    assert len(citations) == 2
    assert all(c["inferred"] for c in citations)


def test_expired_warning_is_none_when_every_cited_source_is_current():
    citations = parse_citations("[1]", [hit(1)])
    assert expired_warning(citations) is None


def test_expired_warning_names_the_expired_policy():
    citations = parse_citations(
        "[1]", [hit(1, status="expired", expiry="2026-05-31", title="Asbestos Management Policy")]
    )
    warning = expired_warning(citations)

    assert warning is not None
    assert "Asbestos Management Policy" in warning
    assert "2026-05-31" in warning


def test_expired_warning_ignores_an_expired_source_that_was_not_cited():
    """The banner reflects what the answer actually used."""
    hits = [hit(1), hit(2, status="expired", expiry="2026-05-31")]
    citations = parse_citations("Only [1] here.", hits)

    assert expired_warning(citations) is None


def test_expired_warning_is_silent_when_the_model_declined_to_answer():
    """A refusal cites nothing, so every source comes back inferred. Warning
    that 'this answer draws on an expired policy' would be false and alarming."""
    hits = [hit(1, status="expired", expiry="2026-05-31")]
    citations = parse_citations("The knowledge base does not cover this.", hits)

    assert all(c["inferred"] for c in citations)
    assert expired_warning(citations) is None
