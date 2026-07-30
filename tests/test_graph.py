"""Graph wiring: routing and the retry loop, with a fake retriever and fake LLM.

These assert control flow, not answer quality -- no network calls involved.
"""

import pytest
from langchain_core.documents import Document

import rag.graph as graph_module
from rag.graph import MAX_ATTEMPTS, OUT_OF_SCOPE_REPLY, SMALLTALK_REPLY, build_graph, run


class FakeRetriever:
    def __init__(self, hits=None):
        self._hits = hits if hits is not None else [_hit()]
        self.queries: list[str] = []

    def search(self, query, **kwargs):
        self.queries.append(query)
        return self._hits


def _hit(page=1):
    return (
        Document(
            page_content="body",
            metadata={
                "id": f"p#{page}",
                "doc_id": "fire-safety-policy",
                "title": "Fire Safety Policy",
                "source_file": "Fire Safety Policy.pdf",
                "page": page,
                "heading_path": "Fire Safety Policy > 1 Scope",
                "status": "current",
                "expiry": "2027-01-01",
            },
        ),
        0.5,
    )


class FakeLLM:
    """Returns whatever the test scripts, per structured-output schema."""

    def __init__(self, route="kb", sufficient=True):
        self.route = route
        self.sufficient = sufficient
        self._schema = None

    def with_structured_output(self, schema):
        clone = FakeLLM(self.route, self.sufficient)
        clone._schema = schema
        return clone

    def invoke(self, messages):
        if self._schema is None:
            return type("Msg", (), {"content": "rewritten query"})()
        if self._schema.__name__ == "Route":
            return self._schema(route=self.route)
        return self._schema(sufficient=self.sufficient, missing="" if self.sufficient else "gap")


@pytest.fixture
def patch_llm(monkeypatch):
    def _apply(route="kb", sufficient=True):
        monkeypatch.setattr(graph_module, "_llm", lambda: FakeLLM(route, sufficient))

    return _apply


@pytest.fixture
def patch_generate(monkeypatch):
    calls = []

    def fake_answer(question, hits, history=None):
        calls.append({"question": question, "hits": hits})
        return {"answer": "generated", "citations": [], "expired_warning": None}

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
    retriever = FakeRetriever()

    result = run(build_graph(retriever), "how do we handle damp and mould?")

    assert result["answer"] == "generated"
    assert result["route"] == "kb"
    assert result["attempts"] == 1
    assert len(patch_generate) == 1


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
    retriever = FakeRetriever(hits=[])

    result = run(build_graph(retriever), "nothing matches this")

    assert result["attempts"] == MAX_ATTEMPTS
    assert len(patch_generate) == 1


# ── Observability ───────────────────────────────────────────────────────────
def test_per_node_timings_are_recorded(patch_llm, patch_generate):
    patch_llm(route="kb", sufficient=True)

    result = run(build_graph(FakeRetriever()), "a question")

    assert {"route", "retrieve_1", "grade", "generate"} <= set(result["timings"])
    assert all(isinstance(v, int) for v in result["timings"].values())


def test_filters_are_passed_through_to_the_retriever(patch_llm, patch_generate, monkeypatch):
    patch_llm(route="kb", sufficient=True)
    seen = {}

    class RecordingRetriever(FakeRetriever):
        def search(self, query, **kwargs):
            seen.update(kwargs)
            return super().search(query, **kwargs)

    run(build_graph(RecordingRetriever()), "a question", doc_id="pets-policy", status="current")

    assert seen["doc_id"] == "pets-policy"
    assert seen["status"] == "current"
