"""Retrieval metrics. Pure functions -- no I/O, no network, no LLM.

Relevance is graded, not binary:

    3  fully answers the question
    2  substantial supporting evidence
    1  related context
    0  irrelevant

Recall@K and Precision@K count grade >= RELEVANT_GRADE as relevant. nDCG@K uses
the raw grades as gains, which is the point of grading them at all -- the
previous eval had one verbatim phrase per question and could express neither.
"""

import math
import re

RELEVANT_GRADE = 2


def normalise(text: str) -> str:
    """Compare content, not markup.

    Markdown table pipes and emphasis markers are formatting, so a quote of a
    table row reads "Effective From: 24/10/2024 Expires: 24/10/2027" while the
    chunk holds "|**Effective From:**|24/10/2024|**Expires:**|24/10/2027|".
    Without stripping them, no table quote can ever verify.
    """
    text = re.sub(r"[|*_`#>]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def match_grade(doc_meta: dict, doc_text: str, relevant: list[dict]) -> int:
    """The grade this retrieved chunk earns, or 0.

    A chunk matches a gold entry by EITHER route:

      1. its vector id equals the recorded chunk_id, or
      2. the recorded quote appears verbatim in its text, on the same page.

    Route 2 is what lets a golden set survive re-chunking. Chunk ids embed a
    chunk_index, so any change to the chunker invalidates every id in the file
    and the eval would silently report zero recall -- exactly when the numbers
    matter most, because the chunker is what changed.
    """
    text = normalise(doc_text)
    page = doc_meta.get("page")
    best = 0
    for entry in relevant:
        by_id = doc_meta.get("id") == entry.get("chunk_id")
        quote = entry.get("quote") or ""
        by_quote = bool(quote) and normalise(quote) in text and page == entry.get("page")
        if by_id or by_quote:
            best = max(best, entry.get("grade", 0))
    return best


def grades_at_k(retrieved: list[tuple[dict, str]], relevant: list[dict], k: int) -> list[int]:
    """Grade for each of the top k retrieved chunks, in rank order."""
    return [match_grade(meta, text, relevant) for meta, text in retrieved[:k]]


def recall_at_k(retrieved, relevant, k: int) -> float:
    """Fraction of the relevant chunks that appear in the top k.

    True recall, not the hit-rate the previous eval called recall: with several
    gold passages per question this is a fraction, not a 0/1.
    """
    total = sum(1 for e in relevant if e.get("grade", 0) >= RELEVANT_GRADE)
    if total == 0:
        return 0.0
    found = sum(1 for g in grades_at_k(retrieved, relevant, k) if g >= RELEVANT_GRADE)
    return min(found / total, 1.0)


def precision_at_k(retrieved, relevant, k: int) -> float:
    """Fraction of the top k that are relevant."""
    top = grades_at_k(retrieved, relevant, k)
    if not top:
        return 0.0
    return sum(1 for g in top if g >= RELEVANT_GRADE) / len(top)


def reciprocal_rank(retrieved, relevant, k: int) -> float:
    """1 / rank of the first relevant chunk, or 0."""
    for rank, grade in enumerate(grades_at_k(retrieved, relevant, k), start=1):
        if grade >= RELEVANT_GRADE:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved, relevant, k: int) -> float:
    """Normalised discounted cumulative gain, using the grades as gains."""
    gains = grades_at_k(retrieved, relevant, k)
    dcg = sum(g / math.log2(i + 1) for i, g in enumerate(gains, start=1) if g)

    ideal = sorted((e.get("grade", 0) for e in relevant), reverse=True)[:k]
    idcg = sum(g / math.log2(i + 1) for i, g in enumerate(ideal, start=1) if g)

    return dcg / idcg if idcg else 0.0


def precision_ceiling_at_k(relevant: list[dict], k: int) -> float:
    """Nominal best precision@k, counting only the LABELLED gold chunks.

    A question with one labelled relevant chunk gives a nominal precision@5 of
    0.2, however good the retriever is. Without this, raw precision invites the
    conclusion that precision is terrible and a reranker is needed, when the
    retriever may already be at its ceiling.

    It is a lower bound, not a hard limit: chunks overlap by CHUNK_OVERLAP
    characters, so a gold quote can legitimately appear in two adjacent chunks
    and both score as relevant. Measured precision above 100% of nominal means
    retrieval found relevant text the golden set did not label -- informative,
    not an error.
    """
    total = sum(1 for e in relevant if e.get("grade", 0) >= RELEVANT_GRADE)
    return min(total, k) / k if k else 0.0


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
