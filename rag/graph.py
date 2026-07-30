"""The agent: route, retrieve, check, answer.

The graph is deliberately small. Every node earns its place by doing something
plain retrieval cannot:

    route        "hi" and "what is the capital of France?" should not cost an
                 embedding call, a Pinecone query, a BM25 scan and a generation.
    clarify      "what is the timescale?" is unanswerable -- ask, do not guess.
    decompose    a question spanning several policies is retrieved better as
                 two or three separate searches than as one.
    agent        questions ABOUT the corpus ("which policies are expired?") are
                 lookups over metadata, not retrieval problems.
    grade        judges the retrieved set as a whole; if it is not enough, one
                 rewritten retry often is.
    verify       drops citations whose markers point at nothing.

Exactly one retrieval retry, hard-capped, and at most MAX_TOOL_CALLS tool calls.
No self-reflection on the answer, no confidence loop, no checkpointer -- history
comes from the client.
"""

import time
from typing import Literal, TypedDict

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from rag import config
from rag.generate import NO_CONTEXT_ANSWER, answer as generate_answer, format_context
from rag.retriever import KBRetriever
from rag.tools import MAX_TOOL_CALLS, make_tools

MAX_ATTEMPTS = 2
MAX_SUBQUESTIONS = 3

SMALLTALK_REPLY = (
    "I answer questions about Aster Group's policy library -- repairs, tenancy, "
    "safety, complaints, safeguarding and so on. What would you like to know?"
)
OUT_OF_SCOPE_REPLY = (
    "That is outside the Aster policy library, so I have nothing to answer from. "
    "Ask me about an Aster policy and I will cite the document and page."
)
AGENT_SYSTEM = (
    "You answer questions about Aster Group's policy library using the tools provided. "
    "Use list_policies for questions about which policies exist or their status, "
    "policy_sections for what a policy covers, and search_policies for policy content. "
    "Answer only from tool results, and cite the source file and page."
)


class RagState(TypedDict, total=False):
    question: str
    route: str
    search_query: str
    sub_questions: list[str]
    audience: str | None
    status: str | None
    doc_id: str | None
    history: list[tuple[str, str]]
    hits: list[tuple[Document, float]]
    grounded: bool
    attempts: int
    messages: list
    tool_calls: int
    answer: str
    citations: list[dict]
    expired_warning: str | None
    needs_clarification: bool
    timings: dict[str, int]


class Route(BaseModel):
    """How to handle the question."""

    route: Literal["kb", "multi_policy", "corpus", "unclear", "smalltalk", "out_of_scope"] = Field(
        description=(
            "'kb' for a question answered by the content of one policy area -- the default "
            "for anything about housing, repairs, tenancies, safety, complaints or "
            "safeguarding.\n"
            "'multi_policy' when answering needs facts from two or more distinct policy "
            "areas, e.g. an end-to-end process spanning repairs, vulnerability and complaints.\n"
            "'corpus' for questions ABOUT the collection rather than its content: which "
            "policies exist, how many, which are expired, what sections a named policy has.\n"
            "'unclear' only when the question is too vague to search for at all, e.g. "
            "'what is the timescale?' with no subject.\n"
            "'smalltalk' for greetings and questions about you.\n"
            "'out_of_scope' when the subject is clearly unrelated to social housing."
        )
    )


class Grade(BaseModel):
    """Whether the retrieved extracts can answer the question."""

    sufficient: bool = Field(description="True if the extracts contain enough to answer.")


class SubQuestions(BaseModel):
    """The question broken into independently searchable parts."""

    questions: list[str] = Field(
        description=(
            f"Between 2 and {MAX_SUBQUESTIONS} self-contained sub-questions, each answerable "
            "from a single policy area. Each must stand alone without pronouns referring "
            "to the original question."
        )
    )


class Clarification(BaseModel):
    """A single question back to the user."""

    question: str = Field(description="One short question that would make the request searchable.")


def _llm():
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=config.CHAT_MODEL,
        temperature=0.0,
        seed=config.LLM_SEED,
        api_key=config.OPENAI_API_KEY,
    )


def verify_citations(text: str, citations: list[dict]) -> list[dict]:
    """Drop citations the answer does not actually support.

    The cheap deterministic half of citation checking: parse_citations already
    discards markers pointing outside the valid range, and this drops any that
    survived without appearing in the text. No LLM call, so it costs nothing and
    can always be on.
    """
    if not citations or citations[0].get("inferred"):
        return citations
    return [c for c in citations if f"[{c['n']}]" in text]


def build_graph(retriever: KBRetriever):
    """Compile the graph. The retriever is injected so nodes stay testable."""
    tools = make_tools(retriever)
    tool_node = ToolNode(tools)

    def timed(state: RagState, node: str, started: float) -> dict[str, int]:
        timings = dict(state.get("timings") or {})
        timings[node] = round((time.perf_counter() - started) * 1000)
        return timings

    # ── Routing ─────────────────────────────────────────────────────────────
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
            "tool_calls": 0,
            "needs_clarification": False,
            "timings": timed(state, "route", started),
        }

    def respond_direct(state: RagState) -> RagState:
        reply = SMALLTALK_REPLY if state["route"] == "smalltalk" else OUT_OF_SCOPE_REPLY
        return {"answer": reply, "citations": [], "expired_warning": None, "hits": []}

    def clarify(state: RagState) -> RagState:
        """Ask rather than guess. A vague question retrieves vague chunks."""
        started = time.perf_counter()
        result = _llm().with_structured_output(Clarification).invoke(
            [
                (
                    "system",
                    "The user's request is too vague to search a UK social housing policy "
                    "library for.\n"
                    "Write one short question back TO THE USER asking what they meant. "
                    "Offer two or three concrete housing possibilities to choose between "
                    "(repairs, damp and mould, complaints, tenancy, safety).\n"
                    "Do NOT restate their question with the missing detail filled in -- that "
                    "is guessing, not asking. Address them as 'you'.\n"
                    "Example: 'Which timescale did you mean -- for completing a repair, for "
                    "responding to damp and mould, or for handling a complaint?'",
                ),
                ("human", state["question"]),
            ]
        )
        return {
            "answer": result.question,
            "citations": [],
            "expired_warning": None,
            "needs_clarification": True,
            "timings": timed(state, "clarify", started),
        }

    # ── Retrieval ───────────────────────────────────────────────────────────
    def decompose(state: RagState) -> RagState:
        started = time.perf_counter()
        result = _llm().with_structured_output(SubQuestions).invoke(
            [
                (
                    "system",
                    "Break the question into self-contained sub-questions, each answerable "
                    "from one policy area of a UK social housing provider.",
                ),
                ("human", state["question"]),
            ]
        )
        return {
            "sub_questions": result.questions[:MAX_SUBQUESTIONS],
            "timings": timed(state, "decompose", started),
        }

    def retrieve(state: RagState) -> RagState:
        """One search, or one per sub-question, unioned and deduplicated by id."""
        started = time.perf_counter()
        queries = state.get("sub_questions") or [state["search_query"]]

        merged: dict[str, tuple[Document, float]] = {}
        for query in queries:
            for doc, score in retriever.search(
                query,
                audience=state.get("audience"),
                status=state.get("status"),
                doc_id=state.get("doc_id"),
            ):
                vid = doc.metadata["id"]
                # Keep the best score a chunk achieved across the sub-questions.
                if vid not in merged or score > merged[vid][1]:
                    merged[vid] = (doc, score)

        hits = sorted(merged.values(), key=lambda pair: -pair[1])[: config.FINAL_K]
        attempt = state.get("attempts", 0) + 1
        return {
            "hits": hits,
            "attempts": attempt,
            "timings": timed(state, f"retrieve_{attempt}", started),
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
            "sub_questions": [],  # the retry is a single search, not a re-decomposition
            "timings": timed(state, "rewrite", started),
        }

    def generate(state: RagState) -> RagState:
        started = time.perf_counter()
        # Reached with insufficient context only once the retry is exhausted;
        # the prompt already instructs the model to decline in that case.
        result = generate_answer(state["question"], state["hits"], history=state.get("history"))
        result["citations"] = verify_citations(result["answer"], result["citations"])
        return {**result, "timings": timed(state, "generate", started)}

    # ── Tool-calling branch ─────────────────────────────────────────────────
    def agent(state: RagState) -> RagState:
        started = time.perf_counter()
        messages = state.get("messages") or [
            SystemMessage(AGENT_SYSTEM),
            HumanMessage(state["question"]),
        ]
        reply = _llm().bind_tools(tools).invoke(messages)
        calls = state.get("tool_calls", 0) + len(reply.tool_calls or [])
        return {
            "messages": messages + [reply],
            "tool_calls": calls,
            "answer": reply.content or "",
            "citations": [],
            "expired_warning": None,
            "timings": timed(state, f"agent_{calls}", started),
        }

    def call_tools(state: RagState) -> RagState:
        result = tool_node.invoke({"messages": state["messages"]})
        return {"messages": state["messages"] + result["messages"]}

    # ── Edges ───────────────────────────────────────────────────────────────
    def after_route(state: RagState) -> str:
        return {
            "kb": "retrieve",
            "multi_policy": "decompose",
            "corpus": "agent",
            "unclear": "clarify",
        }.get(state["route"], "respond_direct")

    def after_grade(state: RagState) -> str:
        if state.get("grounded"):
            return "generate"
        if state.get("attempts", 0) < MAX_ATTEMPTS:
            return "rewrite"
        return "generate"  # answer with what we have; the prompt makes it decline

    def after_agent(state: RagState) -> str:
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None) and state.get("tool_calls", 0) <= MAX_TOOL_CALLS:
            return "call_tools"
        return END

    builder = StateGraph(RagState)
    builder.add_node("route_question", route_question)
    builder.add_node("respond_direct", respond_direct)
    builder.add_node("clarify", clarify)
    builder.add_node("decompose", decompose)
    builder.add_node("retrieve", retrieve)
    builder.add_node("grade", grade)
    builder.add_node("rewrite", rewrite)
    builder.add_node("generate", generate)
    builder.add_node("agent", agent)
    builder.add_node("call_tools", call_tools)

    builder.add_edge(START, "route_question")
    builder.add_conditional_edges(
        "route_question",
        after_route,
        ["retrieve", "decompose", "agent", "clarify", "respond_direct"],
    )
    builder.add_edge("respond_direct", END)
    builder.add_edge("clarify", END)
    builder.add_edge("decompose", "retrieve")
    builder.add_edge("retrieve", "grade")
    builder.add_conditional_edges("grade", after_grade, ["generate", "rewrite"])
    builder.add_edge("rewrite", "retrieve")
    builder.add_edge("generate", END)
    builder.add_conditional_edges("agent", after_agent, ["call_tools", END])
    builder.add_edge("call_tools", "agent")

    return builder.compile()


def run(graph, question: str, **kwargs) -> dict:
    """Invoke the graph and return the API-shaped result."""
    state = graph.invoke({"question": question, **kwargs})
    return {
        "answer": state.get("answer") or NO_CONTEXT_ANSWER,
        "citations": state.get("citations", []),
        "expired_warning": state.get("expired_warning"),
        "needs_clarification": state.get("needs_clarification", False),
        "route": state.get("route"),
        "attempts": state.get("attempts", 0),
        "tool_calls": state.get("tool_calls", 0),
        "timings": state.get("timings", {}),
    }
