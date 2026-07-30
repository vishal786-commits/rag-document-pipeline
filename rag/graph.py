"""The agent: route, retrieve, check, answer.

The graph is deliberately small. Every node earns its place by doing something
plain retrieval cannot:

    route      "hi" and "what is the capital of France?" should not cost an
               embedding call, a Pinecone query, a BM25 scan and a generation.
    grade      judges the retrieved set as a whole. If it is not enough to
               answer, one rewritten retry often is.
    rewrite    reformulates using terms seen in the near-miss chunks.

There is exactly one retry, hard-capped. No self-reflection on the answer, no
confidence loops, no checkpointer -- history comes from the client.
"""

import time
from typing import Literal, TypedDict

from langchain_core.documents import Document
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from rag import config
from rag.generate import NO_CONTEXT_ANSWER, answer as generate_answer, format_context
from rag.retriever import KBRetriever

MAX_ATTEMPTS = 2

SMALLTALK_REPLY = (
    "I answer questions about Aster Group's policy library -- repairs, tenancy, "
    "safety, complaints, safeguarding and so on. What would you like to know?"
)
OUT_OF_SCOPE_REPLY = (
    "That is outside the Aster policy library, so I have nothing to answer from. "
    "Ask me about an Aster policy and I will cite the document and page."
)


class RagState(TypedDict, total=False):
    question: str
    route: str
    search_query: str
    audience: str | None
    status: str | None
    doc_id: str | None
    history: list[tuple[str, str]]
    hits: list[tuple[Document, float]]
    grounded: bool
    attempts: int
    answer: str
    citations: list[dict]
    expired_warning: str | None
    timings: dict[str, int]


class Route(BaseModel):
    """How to handle the question."""

    route: Literal["kb", "smalltalk", "out_of_scope"] = Field(
        description=(
            "'kb' for anything about UK social housing policy, tenancies, repairs, "
            "safety, complaints or safeguarding -- assume 'kb' when unsure. "
            "'smalltalk' for greetings and questions about you. "
            "'out_of_scope' only when the question is clearly about an unrelated subject."
        )
    )


class Grade(BaseModel):
    """Whether the retrieved extracts can answer the question."""

    sufficient: bool = Field(description="True if the extracts contain enough to answer.")
    missing: str = Field(
        default="",
        description="If insufficient, the specific information that is absent, in a few words.",
    )


def _llm():
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=config.CHAT_MODEL,
        temperature=0.0,
        seed=config.LLM_SEED,
        api_key=config.OPENAI_API_KEY,
    )


def build_graph(retriever: KBRetriever):
    """Compile the graph. The retriever is injected so nodes stay testable."""

    def timed(state: RagState, node: str, started: float) -> dict[str, int]:
        timings = dict(state.get("timings") or {})
        timings[node] = round((time.perf_counter() - started) * 1000)
        return timings

    # ── Nodes ───────────────────────────────────────────────────────────────
    def route_question(state: RagState) -> RagState:
        started = time.perf_counter()
        result = _llm().with_structured_output(Route).invoke(
            [
                ("system", "Classify the user's question. Answer with the route only."),
                ("human", state["question"]),
            ]
        )
        return {
            "route": result.route,
            "search_query": state["question"],
            "attempts": 0,
            "timings": timed(state, "route", started),
        }

    def respond_direct(state: RagState) -> RagState:
        reply = SMALLTALK_REPLY if state["route"] == "smalltalk" else OUT_OF_SCOPE_REPLY
        return {"answer": reply, "citations": [], "expired_warning": None, "hits": []}

    def retrieve(state: RagState) -> RagState:
        started = time.perf_counter()
        hits = retriever.search(
            state["search_query"],
            audience=state.get("audience"),
            status=state.get("status"),
            doc_id=state.get("doc_id"),
        )
        return {
            "hits": hits,
            "attempts": state.get("attempts", 0) + 1,
            "timings": timed(state, f"retrieve_{state.get('attempts', 0) + 1}", started),
        }

    def grade(state: RagState) -> RagState:
        started = time.perf_counter()
        if not state["hits"]:
            return {"grounded": False, "timings": timed(state, "grade", started)}

        # One call judging the whole set, not one call per document.
        result = _llm().with_structured_output(Grade).invoke(
            [
                (
                    "system",
                    # Calibration matters more than it looks. An earlier version said
                    # "be strict: partial topical overlap is not sufficient" and fired
                    # the retry on 30% of well-covered questions, doubling their
                    # latency to reach the same answer. The bar is "can a useful
                    # grounded answer be given", not "are these extracts complete".
                    "Decide whether a useful answer can be given from these policy extracts "
                    "alone.\n"
                    "Answer true if they contain the substance of an answer, even a partial "
                    "one.\n"
                    "Answer false only if they are off-topic, or discuss the general subject "
                    "without containing the specific facts asked for.\n"
                    "Do not use outside knowledge, and do not require the extracts to be "
                    "complete or tidy.",
                ),
                (
                    "human",
                    f"Question: {state['question']}\n\nExtracts:\n{format_context(state['hits'])}",
                ),
            ]
        )
        return {"grounded": result.sufficient, "timings": timed(state, "grade", started)}

    def rewrite(state: RagState) -> RagState:
        started = time.perf_counter()
        result = _llm().invoke(
            [
                (
                    "system",
                    "Rewrite the question as a search query for a UK social housing policy "
                    "library. Use the vocabulary such policies use. Return the query only.",
                ),
                ("human", state["question"]),
            ]
        )
        return {
            "search_query": result.content.strip(),
            "timings": timed(state, "rewrite", started),
        }

    def generate(state: RagState) -> RagState:
        started = time.perf_counter()
        # Reached with insufficient context only after the retry is exhausted;
        # the prompt already instructs the model to decline in that case.
        result = generate_answer(state["question"], state["hits"], history=state.get("history"))
        return {**result, "timings": timed(state, "generate", started)}

    # ── Edges ───────────────────────────────────────────────────────────────
    def after_route(state: RagState) -> str:
        return "retrieve" if state["route"] == "kb" else "respond_direct"

    def after_grade(state: RagState) -> str:
        if state.get("grounded"):
            return "generate"
        if state.get("attempts", 0) < MAX_ATTEMPTS:
            return "rewrite"
        return "generate"  # answer with what we have; the prompt makes it decline

    builder = StateGraph(RagState)
    builder.add_node("route_question", route_question)
    builder.add_node("respond_direct", respond_direct)
    builder.add_node("retrieve", retrieve)
    builder.add_node("grade", grade)
    builder.add_node("rewrite", rewrite)
    builder.add_node("generate", generate)

    builder.add_edge(START, "route_question")
    builder.add_conditional_edges("route_question", after_route, ["retrieve", "respond_direct"])
    builder.add_edge("respond_direct", END)
    builder.add_edge("retrieve", "grade")
    builder.add_conditional_edges("grade", after_grade, ["generate", "rewrite"])
    builder.add_edge("rewrite", "retrieve")
    builder.add_edge("generate", END)

    return builder.compile()


def run(graph, question: str, **kwargs) -> dict:
    """Invoke the graph and return the API-shaped result."""
    state = graph.invoke({"question": question, **kwargs})
    return {
        "answer": state.get("answer", NO_CONTEXT_ANSWER),
        "citations": state.get("citations", []),
        "expired_warning": state.get("expired_warning"),
        "route": state.get("route"),
        "attempts": state.get("attempts", 0),
        "timings": state.get("timings", {}),
    }
