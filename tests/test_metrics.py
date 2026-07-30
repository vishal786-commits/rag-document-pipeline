"""Metrics checked against hand-computed values, so the numbers mean something."""

import math

import pytest

from eval.metrics import (
    match_grade,
    mean,
    ndcg_at_k,
    precision_at_k,
    precision_ceiling_at_k,
    recall_at_k,
    reciprocal_rank,
)


def chunk(vid, text="some policy text about damp", page=1):
    return ({"id": vid, "page": page}, text)


GOLD = [
    {"chunk_id": "damp#1", "page": 1, "grade": 3, "quote": "within 10 working days"},
    {"chunk_id": "repairs#4", "page": 9, "grade": 2, "quote": "Head of Property Services"},
    {"chunk_id": "vuln#2", "page": 3, "grade": 1, "quote": "additional support"},
]


# ── Dual matching ───────────────────────────────────────────────────────────
def test_match_by_chunk_id():
    assert match_grade({"id": "damp#1", "page": 1}, "anything", GOLD) == 3


def test_match_ignores_markdown_table_markup():
    """A quote of a table row reads as prose; the chunk holds pipes and bold
    markers. Without stripping them no table question could ever score."""
    gold = [{"chunk_id": "pets#9", "page": 5, "grade": 3,
             "quote": "Effective From: 24/10/2024 Expires: 24/10/2027"}]
    meta = {"id": "pets#other", "page": 5}
    text = "|**Effective From:**|24/10/2024|**Expires:**|24/10/2027|"

    assert match_grade(meta, text, gold) == 3


def test_match_by_verbatim_quote_when_the_chunk_id_has_changed():
    """The reason the golden set survives re-chunking: ids embed a chunk_index,
    so any change to the chunker invalidates every one of them."""
    meta = {"id": "damp#77", "page": 1}  # re-chunked: different index
    text = "We will attend WITHIN 10 WORKING DAYS of the report."

    assert match_grade(meta, text, GOLD) == 3


def test_quote_match_requires_the_page_to_agree():
    """Same text, wrong page, is a different passage."""
    meta = {"id": "other#1", "page": 5}
    assert match_grade(meta, "within 10 working days", GOLD) == 0


def test_no_match_scores_zero():
    assert match_grade({"id": "unrelated#1", "page": 2}, "about pets", GOLD) == 0


def test_match_takes_the_best_grade_when_several_entries_apply():
    gold = [
        {"chunk_id": "a#1", "page": 1, "grade": 1, "quote": ""},
        {"chunk_id": "a#1", "page": 1, "grade": 3, "quote": ""},
    ]
    assert match_grade({"id": "a#1", "page": 1}, "text", gold) == 3


# ── Recall ──────────────────────────────────────────────────────────────────
def test_recall_counts_only_grade_2_and_above():
    """GOLD has two relevant entries (grades 3 and 2); the grade-1 one is context."""
    retrieved = [chunk("damp#1"), chunk("vuln#2", page=3)]
    assert recall_at_k(retrieved, GOLD, k=5) == pytest.approx(0.5)


def test_recall_is_one_when_every_relevant_chunk_is_found():
    retrieved = [chunk("damp#1"), chunk("repairs#4", page=9)]
    assert recall_at_k(retrieved, GOLD, k=5) == pytest.approx(1.0)


def test_recall_respects_the_cutoff():
    retrieved = [chunk("noise#1"), chunk("noise#2"), chunk("damp#1")]
    assert recall_at_k(retrieved, GOLD, k=2) == 0.0
    assert recall_at_k(retrieved, GOLD, k=3) == pytest.approx(0.5)


def test_recall_with_no_relevant_gold_is_zero_not_a_crash():
    assert recall_at_k([chunk("a#1")], [{"grade": 1, "chunk_id": "x", "page": 1}], k=3) == 0.0


# ── Precision ───────────────────────────────────────────────────────────────
def test_precision_is_relevant_over_retrieved():
    retrieved = [chunk("damp#1"), chunk("noise#1"), chunk("noise#2"), chunk("noise#3")]
    assert precision_at_k(retrieved, GOLD, k=4) == pytest.approx(0.25)


def test_precision_divides_by_what_was_actually_returned():
    """Two results at k=5 is 2 results, not 5."""
    retrieved = [chunk("damp#1"), chunk("noise#1")]
    assert precision_at_k(retrieved, GOLD, k=5) == pytest.approx(0.5)


def test_precision_of_nothing_is_zero():
    assert precision_at_k([], GOLD, k=5) == 0.0


# ── MRR ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("position,expected", [(0, 1.0), (1, 0.5), (2, 1 / 3)])
def test_reciprocal_rank_is_one_over_the_first_relevant_position(position, expected):
    retrieved = [chunk("noise#1"), chunk("noise#2"), chunk("noise#3")]
    retrieved[position] = chunk("damp#1")

    assert reciprocal_rank(retrieved, GOLD, k=5) == pytest.approx(expected)


def test_reciprocal_rank_is_zero_when_nothing_relevant_is_found():
    assert reciprocal_rank([chunk("noise#1")], GOLD, k=5) == 0.0


# ── nDCG ────────────────────────────────────────────────────────────────────
def test_ndcg_is_one_for_the_ideal_ordering():
    """Grades 3, 2, 1 retrieved in that order is by definition ideal."""
    retrieved = [chunk("damp#1"), chunk("repairs#4", page=9), chunk("vuln#2", page=3)]
    assert ndcg_at_k(retrieved, GOLD, k=3) == pytest.approx(1.0)


def test_ndcg_penalises_a_worse_ordering():
    ideal = [chunk("damp#1"), chunk("repairs#4", page=9), chunk("vuln#2", page=3)]
    reversed_order = [chunk("vuln#2", page=3), chunk("repairs#4", page=9), chunk("damp#1")]

    assert ndcg_at_k(reversed_order, GOLD, k=3) < ndcg_at_k(ideal, GOLD, k=3)


def test_ndcg_matches_a_hand_computed_value():
    # Retrieved: grade 2 at rank 1, grade 3 at rank 2.
    #   DCG  = 2/log2(2) + 3/log2(3) = 2.0 + 1.8927 = 3.8927
    #   IDCG = 3/log2(2) + 2/log2(3) = 3.0 + 1.2619 = 4.2619
    retrieved = [chunk("repairs#4", page=9), chunk("damp#1")]
    expected = (2 / math.log2(2) + 3 / math.log2(3)) / (3 / math.log2(2) + 2 / math.log2(3))

    assert ndcg_at_k(retrieved, GOLD, k=2) == pytest.approx(expected)


def test_ndcg_is_zero_when_nothing_relevant_is_retrieved():
    assert ndcg_at_k([chunk("noise#1")], GOLD, k=3) == 0.0


def test_ndcg_with_no_gold_grades_is_zero_not_a_division_error():
    assert ndcg_at_k([chunk("a#1")], [], k=3) == 0.0


# ── Precision ceiling ───────────────────────────────────────────────────────
def test_precision_ceiling_reflects_how_few_relevant_chunks_exist():
    """One relevant chunk means precision@5 is capped at 0.2, however good the
    retriever is. Reading 0.2 as a failure without this is the trap."""
    one_gold = [{"chunk_id": "a#1", "page": 1, "grade": 3, "quote": ""}]
    assert precision_ceiling_at_k(one_gold, 5) == pytest.approx(0.2)


def test_precision_ceiling_rises_with_more_relevant_chunks():
    assert precision_ceiling_at_k(GOLD, 5) == pytest.approx(0.4)  # two at grade >= 2


def test_precision_ceiling_ignores_grade_one_context():
    assert precision_ceiling_at_k([{"grade": 1, "chunk_id": "x", "page": 1}], 5) == 0.0


def test_precision_can_legitimately_exceed_the_nominal_ceiling():
    """Chunks overlap, so one gold quote can appear in two adjacent chunks and
    both are genuinely relevant. The ceiling is a lower bound, not a limit."""
    gold = [{"chunk_id": "a#1", "page": 1, "grade": 3, "quote": "within 10 working days"}]
    overlapping = [
        ({"id": "a#1", "page": 1}, "... within 10 working days ..."),
        ({"id": "a#2", "page": 1}, "within 10 working days of the report"),
    ]
    assert precision_at_k(overlapping, gold, k=2) > precision_ceiling_at_k(gold, k=2)


# ── mean ────────────────────────────────────────────────────────────────────
def test_mean_of_nothing_is_zero():
    assert mean([]) == 0.0
    assert mean([1.0, 2.0]) == pytest.approx(1.5)
