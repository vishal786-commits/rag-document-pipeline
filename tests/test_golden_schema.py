"""The golden set is the measuring instrument, so it gets checked like one.

These run offline against the committed chunk snapshot -- no API keys.
"""

import json
from collections import Counter

import pytest

from eval.metrics import normalise
from rag import config
from rag.retriever import load_chunks

GOLDEN_PATH = config.REPO_ROOT / "eval" / "golden_set.json"
REQUIRED_TYPES = {"factual", "multi_hop", "table", "summarization"}


@pytest.fixture(scope="module")
def golden():
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def chunks_by_id():
    return {c.metadata["id"]: c for c in load_chunks(config.CHUNKS_PATH)}


# ── Shape ───────────────────────────────────────────────────────────────────
def test_the_golden_set_exists_and_is_approved(golden):
    assert golden["review_status"] == "approved"
    assert all(q["review_status"] == "approved" for q in golden["questions"])


def test_there_are_enough_questions(golden):
    assert len(golden["questions"]) >= 40


def test_every_question_type_is_represented(golden):
    counts = Counter(q["type"] for q in golden["questions"])
    assert set(counts) == REQUIRED_TYPES
    for kind in REQUIRED_TYPES:
        assert counts[kind] >= 5, f"only {counts[kind]} {kind} questions"


def test_ids_are_unique(golden):
    ids = [q["id"] for q in golden["questions"]]
    assert len(set(ids)) == len(ids)


def test_every_question_has_the_required_fields(golden):
    for q in golden["questions"]:
        assert q["question"].strip()
        assert q["gold_answer"].strip()
        assert q["relevant"], f"{q['id']} has no relevant chunks"
        for entry in q["relevant"]:
            assert entry["chunk_id"]
            assert entry["doc_id"]
            assert isinstance(entry["page"], int)
            assert entry["grade"] in (0, 1, 2, 3)
            assert entry["quote"].strip()


# ── Substance ───────────────────────────────────────────────────────────────
def test_every_quote_is_verbatim_in_the_chunk_it_names(golden, chunks_by_id):
    """The check that keeps the whole thing honest. A quote that does not appear
    in its chunk silently scores zero for a retrieval that was actually right."""
    missing = []
    for q in golden["questions"]:
        for entry in q["relevant"]:
            chunk = chunks_by_id.get(entry["chunk_id"])
            if chunk is None:
                missing.append(f"{q['id']}: no chunk {entry['chunk_id']}")
            elif normalise(entry["quote"]) not in normalise(chunk.page_content):
                missing.append(f"{q['id']}: quote not in {entry['chunk_id']}")
    assert not missing, missing[:10]


def test_the_page_recorded_matches_the_chunk(golden, chunks_by_id):
    """Quote matching falls back to quote-plus-page, so a wrong page breaks it."""
    for q in golden["questions"]:
        for entry in q["relevant"]:
            chunk = chunks_by_id.get(entry["chunk_id"])
            if chunk:
                assert entry["page"] == chunk.metadata["page"], q["id"]


def test_multi_hop_questions_really_span_two_documents(golden):
    """Otherwise they are single-hop questions wearing a multi_hop label, and
    the per-type breakdown stops meaning anything."""
    for q in golden["questions"]:
        if q["type"] == "multi_hop":
            docs = {e["doc_id"] for e in q["relevant"]}
            assert len(docs) >= 2, f"{q['id']} spans only {docs}"


def test_no_question_refers_to_the_extract_it_came_from(golden):
    for q in golden["questions"]:
        lowered = q["question"].lower()
        assert "extract" not in lowered, q["id"]
        assert "this document" not in lowered, q["id"]


def test_questions_cover_a_reasonable_spread_of_documents(golden):
    docs = {e["doc_id"] for q in golden["questions"] for e in q["relevant"]}
    assert len(docs) >= 25, f"only {len(docs)} of 36 documents are represented"


def test_the_snapshot_the_set_was_built_from_is_recorded(golden):
    """If this drifts from the current snapshot, chunk_ids may have moved and
    scoring quietly falls back to quote matching."""
    assert golden.get("chunks_sha256")
    current = json.loads(config.CHUNKS_META_PATH.read_text(encoding="utf-8"))["sha256"]
    if golden["chunks_sha256"] != current:
        pytest.skip("chunk snapshot has changed since the golden set was built")
