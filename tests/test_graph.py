"""Graph wiring: routing, the retry loop, decomposition, clarification.

A fake retriever and a fake LLM, so these assert control flow rather than answer
quality -- no network calls involved.
"""

import pytest
from langchain_core.documents import Document

import rag.graph as graph_module
from rag.graph import (
    MAX_ATTEMPTS,
    MAX_SUBQUESTIONS,
    OUT_OF_SCOPE_REPLY,
    SMALLTALK_REPLY,
    build_graph,
    run,
    verify_citations,
)


def _hit(page=1, doc_id="fire-safety-policy"):
    return (
        Document(
            page_content="body",
            metadata={
                "id": f"{doc_id}#{page}",
                "doc_id": doc_id,
                "title": "Fire Safety Policy",
                "source_file": "Fire Safety Policy.pdf",
                "page": page,
                "heading_path": "Fire Safety Policy > 1 Scope",
                "audience": "staff",
                "status": "current",
                "version": "1.0",
                "expiry": "2027-01-01",
            },
        ),
        0.5,
    )


class FakeRetriever:
    def __init__(self, hits=None):
        self._hits = hits if hits is not None else [_hit()]
        self.queries: list[str] = []
        self.docs = [doc for doc, _ in self._hits]

    def search(self, query, **kwargs):
        self.queries.append(query)
        return self._hits

    def policies(self):
        return []


class FakeLLM:
    """Returns whatever the test scripts, per structured-output schema."""

    def __init__(self, route="kb", sufficient=True, sub_questions=None):
        self.route = route
        self.sufficient = sufficient
        self.sub_questions = sub_questions or ["sub one", "sub two"]
        self._schema = None

    def with_structured_output(self, schema):
        clone = FakeLLM(self.route, self.sufficient, self.sub_questions)
        clone._schema = schema
        return clone

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        if self._schema is None:
            # Either the rewrite node or the tool-calling agent.
            return type("Msg", (), {"content": "rewritten query", "tool_calls": []})()
        name = self._schema.__name__
        if name == "Route":
            return self._schema(route=self.route)
        if name == "Grade":
            return self._schema(sufficient=self.sufficient)
        if name == "SubQuestions":
            return self._schema(questions=self.sub_questions)
        return self._schema(question="Which policy did you mean?")


@pytest.fixture
def patch_llm(monkeypatch):
    def _apply(**kwargs):
        monkeypatch.setattr(graph_module, "_llm", lambda: FakeLLM(**kwargs))

    return _apply


@pytest.fixture
def patch_generate(monkeypatch):
    calls = []

    def fake_answer(question, hits, history=None):
        calls.append({"question": question, "hits": hits})
        return {"answer": "generated [1]", "citations": [{"n": 1, "inferred": False}],
                "expired_warning": None}

    monkeypatch.setattr(graph_module, "generate_answer", fake_answer)
    monkeypatch.setattr(graph_module, "format_context", lambda hits: "ctx")
    return calls


# ── Routing ─────────────────────────────────────────────────────────────────
def test_smalltalk_skips_retrieval_entirely(patch_llm, patch_generate):
    patch_llm(route="smalltalk")
    retriever = FakeRetriever()

    result = run(build_graph(retriever), "hello there")

    assert result["answer"] == SMALLTALK_REPLY
    assert retriever.queries == [], "smalltalk must not cost a retrieval"
    assert patch_generate == [], "smalltalk must not cost a generation"


def test_out_of_scope_skips_retrieval_entirely(patch_llm, patch_generate):
    patch_llm(route="out_of_scope")
    retriever = FakeRetriever()

    result = run(build_graph(retriever), "what is the capital of France?")

    assert result["answer"] == OUT_OF_SCOPE_REPLY
    assert retriever.queries == []


def test_a_kb_question_retrieves_and_generates(patch_llm, patch_generate):
    patch_llm(route="kb", sufficient=True)

    result = run(build_graph(FakeRetriever()), "how do we handle damp and mould?")

    assert result["answer"] == "generated [1]"
    assert result["route"] == "kb"
    assert result["attempts"] == 1
    assert len(patch_generate) == 1


# ── Clarification ───────────────────────────────────────────────────────────
def test_a_vague_question_is_asked_back_rather_than_guessed_at(patch_llm, patch_generate):
    patch_llm(route="unclear")
    retriever = FakeRetriever()

    result = run(build_graph(retriever), "what is the timescale?")

    assert result["needs_clarification"] is True
    assert result["answer"] == "Which policy did you mean?"
    assert retriever.queries == [], "a vague question must not be searched for"
    assert patch_generate == []


def test_answered_questions_are_not_flagged_as_needing_clarification(patch_llm, patch_generate):
    patch_llm(route="kb", sufficient=True)
    assert run(build_graph(FakeRetriever()), "a clear question")["needs_clarification"] is False


# ── Multi-hop decomposition ─────────────────────────────────────────────────
def test_a_multi_policy_question_is_split_and_each_part_retrieved(patch_llm, patch_generate):
    patch_llm(route="multi_policy", sufficient=True, sub_questions=["part a", "part b"])
    retriever = FakeRetriever()

    result = run(build_graph(retriever), "what happens end to end when a vulnerable tenant "
                                         "reports damp?")

    assert retriever.queries == ["part a", "part b"]
    assert result["attempts"] == 1, "the sub-questions are one retrieval round, not two"
    assert len(patch_generate) == 1, "sub-questions are merged, then generated once"


def test_decomposition_is_capped(patch_llm, patch_generate):
    patch_llm(route="multi_policy", sufficient=True,
              sub_questions=[f"q{i}" for i in range(10)])
    retriever = FakeRetriever()

    run(build_graph(retriever), "a sprawling question")

    assert len(retriever.queries) == MAX_SUBQUESTIONS


def test_merged_subquestion_hits_are_deduplicated_by_id(patch_llm, patch_generate):
    """Both sub-questions return the same chunk; it must appear once."""
    patch_llm(route="multi_policy", sufficient=True, sub_questions=["a", "b"])
    retriever = FakeRetriever(hits=[_hit(1), _hit(1)])

    run(build_graph(retriever), "a question")

    assert len(patch_generate[0]["hits"]) == 1


# ── The retry loop ──────────────────────────────────────────────────────────
def test_insufficient_context_triggers_exactly_one_rewritten_retry(patch_llm, patch_generate):
    patch_llm(route="kb", sufficient=False)
    retriever = FakeRetriever()

    result = run(build_graph(retriever), "an obscure question")

    assert result["attempts"] == MAX_ATTEMPTS == 2, "the retry must be hard-capped"
    assert retriever.queries == ["an obscure question", "rewritten query"]
    assert len(patch_generate) == 1, "generate runs once, after the retry is exhausted"


def test_sufficient_context_does_not_retry(patch_llm, patch_generate):
    patch_llm(route="kb", sufficient=True)
    retriever = FakeRetriever()

    run(build_graph(retriever), "a well covered question")
    assert len(retriever.queries) == 1


def test_empty_retrieval_still_terminates(patch_llm, patch_generate):
    """No hits means the grader is skipped; the loop must not spin."""
    patch_llm(route="kb", sufficient=True)

    result = run(build_graph(FakeRetriever(hits=[])), "nothing matches this")

    assert result["attempts"] == MAX_ATTEMPTS
    assert len(patch_generate) == 1


def test_the_retry_of_a_multi_policy_question_is_a_single_search(patch_llm, patch_generate):
    patch_llm(route="multi_policy", sufficient=False, sub_questions=["a", "b"])
    retriever = FakeRetriever()

    run(build_graph(retriever), "a question")

    assert retriever.queries == ["a", "b", "rewritten query"]


# ── Citation verification ───────────────────────────────────────────────────
def test_verify_citations_drops_one_the_answer_never_mentions():
    citations = [{"n": 1, "inferred": False}, {"n": 2, "inferred": False}]
    assert verify_citations("Grounded in [1] only.", citations) == [{"n": 1, "inferred": False}]


def test_verify_citations_leaves_inferred_citations_alone():
    """An uncited answer lists everything retrieved; that is not a hallucination."""
    citations = [{"n": 1, "inferred": True}, {"n": 2, "inferred": True}]
    assert verify_citations("No markers here.", citations) == citations


def test_verify_citations_handles_an_empty_list():
    assert verify_citations("anything", []) == []


# ── Observability ───────────────────────────────────────────────────────────
def test_per_node_timings_are_recorded(patch_llm, patch_generate):
    patch_llm(route="kb", sufficient=True)

    result = run(build_graph(FakeRetriever()), "a question")

    assert {"route", "retrieve_1", "grade", "generate"} <= set(result["timings"])
    assert all(isinstance(v, int) for v in result["timings"].values())


def test_filters_are_passed_through_to_the_retriever(patch_llm, patch_generate):
    patch_llm(route="kb", sufficient=True)
    seen = {}

    class RecordingRetriever(FakeRetriever):
        def search(self, query, **kwargs):
            seen.update(kwargs)
            return super().search(query, **kwargs)

    run(build_graph(RecordingRetriever()), "a question", doc_id="pets-policy", status="current")

    assert seen["doc_id"] == "pets-policy"
    assert seen["status"] == "current"
