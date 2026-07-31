"""Fusion and filtering are pure, so these run with no network and no index."""

import json

import pytest
from langchain_core.documents import Document

from rag.retriever import (
    RetrieverError,
    build_filter,
    fuse,
    load_chunks,
    normalise,
    passes,
    tokenize,
)


def doc(vid: str, **meta) -> Document:
    base = {"id": vid, "audience": "staff", "status": "current", "doc_id": vid.split("#")[0]}
    base.update(meta)
    return Document(page_content=f"body of {vid}", metadata=base)


# ── Fusion ──────────────────────────────────────────────────────────────────
def test_fuse_ranks_a_document_found_by_both_retrievers_first():
    a, b, c = doc("p#1"), doc("p#2"), doc("p#3")
    # 'b' is second on both lists; 'a' is first on one and absent from the other.
    fused = fuse([[a, b], [c, b]], k=3)

    assert fused[0][0].metadata["id"] == "p#2"
    assert fused[0][1] > fused[1][1]


def test_fuse_preserves_metadata():
    """The whole reason fusion is keyed on the id rather than the text: this is
    what makes '[source_file p.N]' citations possible."""
    a = doc("p#1", page=7, source_file="Fire Safety Policy.pdf")
    fused = fuse([[a]], k=1)

    assert fused[0][0].metadata["page"] == 7
    assert fused[0][0].metadata["source_file"] == "Fire Safety Policy.pdf"


def test_fuse_does_not_collide_chunks_with_identical_text():
    """Two chunks can share a body (a templated clause) but are distinct
    documents. Keying on text would merge them; keying on id does not."""
    a = Document(page_content="same body", metadata={"id": "policy-a#1"})
    b = Document(page_content="same body", metadata={"id": "policy-b#1"})

    fused = fuse([[a, b]], k=5)
    assert len(fused) == 2


def test_fuse_is_deterministic_for_tied_scores():
    a, b, c = doc("p#1"), doc("p#2"), doc("p#3")
    first = fuse([[a, b, c]], k=3)
    second = fuse([[a, b, c]], k=3)

    assert [d.metadata["id"] for d, _ in first] == [d.metadata["id"] for d, _ in second]


def test_fuse_respects_k():
    docs = [doc(f"p#{i}") for i in range(10)]
    assert len(fuse([docs], k=4)) == 4


def test_fuse_of_nothing_is_empty():
    assert fuse([[], []], k=5) == []


# ── Filters ─────────────────────────────────────────────────────────────────
def test_build_filter_is_none_when_nothing_is_filtered():
    assert build_filter(None, None, None) is None


def test_build_filter_includes_reference_material_for_any_audience():
    """Statutory context is useful to staff and tenants alike."""
    assert build_filter("tenant", None, None) == {"audience": {"$in": ["tenant", "reference"]}}


def test_build_filter_combines_clauses():
    assert build_filter("staff", "current", "fire-safety-policy") == {
        "audience": {"$in": ["staff", "reference"]},
        "status": {"$eq": "current"},
        "doc_id": {"$eq": "fire-safety-policy"},
    }


@pytest.mark.parametrize(
    "meta,audience,expected",
    [
        ({"audience": "staff"}, "staff", True),
        ({"audience": "reference"}, "tenant", True),  # reference passes for everyone
        ({"audience": "staff"}, "tenant", False),
        ({"audience": "staff"}, None, True),  # no filter
    ],
)
def test_passes_mirrors_the_pinecone_audience_filter(meta, audience, expected):
    assert passes(Document(page_content="", metadata=meta), audience, None, None) is expected


def test_passes_filters_on_status_and_doc_id():
    d = doc("fire-safety-policy#1", status="expired")
    assert not passes(d, None, "current", None)
    assert passes(d, None, "expired", None)
    assert passes(d, None, None, "fire-safety-policy")
    assert not passes(d, None, None, "pets-policy")


# ── Snapshot loading ────────────────────────────────────────────────────────
def test_load_chunks_reads_the_jsonl_snapshot(tmp_path):
    path = tmp_path / "chunks.jsonl"
    path.write_text(
        json.dumps({"id": "a#0", "text": "hello", "metadata": {"id": "a#0", "page": 1}}) + "\n",
        encoding="utf-8",
    )
    docs = load_chunks(path)

    assert len(docs) == 1
    assert docs[0].page_content == "hello"
    assert docs[0].metadata["page"] == 1


def test_load_chunks_raises_a_useful_message_when_missing(tmp_path):
    with pytest.raises(RetrieverError, match="Run `python -m rag.ingest`"):
        load_chunks(tmp_path / "absent.jsonl")


def test_tokenize_is_lowercase_whitespace_split():
    assert tokenize("Damp AND Mould") == ["damp", "and", "mould"]


# ── Metadata normalisation ──────────────────────────────────────────────────
def test_normalise_converts_pinecone_floats_back_to_ints():
    """Pinecone stores every number as a float, so a page comes back as 2.0 and
    a citation renders as 'p.2.0'."""
    d = Document(page_content="", metadata={"page": 2.0, "chunk_index": 15.0})
    normalise(d)

    assert d.metadata["page"] == 2
    assert isinstance(d.metadata["page"], int)
    assert d.metadata["chunk_index"] == 15


def test_normalise_leaves_ints_and_missing_keys_alone():
    d = Document(page_content="", metadata={"page": 3})
    normalise(d)

    assert d.metadata["page"] == 3
    assert "chunk_index" not in d.metadata
