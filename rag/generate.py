"""Turn retrieved chunks into a cited answer.

Three deliberate changes from the previous implementation:
  - gpt-3.5-turbo -> gpt-4.1-mini.
  - temperature 0.5 -> 0.0. A document assistant told to never use outside
    knowledge should be deterministic; 0.5 worked against its own prompt and
    made evaluation runs irreproducible.
  - Exceptions propagate. It used to return the string "Sorry, I couldn't
    process your request.", which looks like an answer to every caller and
    would quietly poison an eval run.
"""

import re

from langchain_core.documents import Document

from rag import config

SYSTEM_PROMPT = """You are a knowledge-base assistant for Aster Group, a UK social housing provider. \
You answer questions strictly from the policy extracts provided. Never use outside knowledge.

CITATIONS:
- Cite the block number in square brackets after each claim, e.g. [2].
- Cite only blocks you actually used.
- If the extracts do not answer the question, say so plainly and cite nothing.

RESPONSE FORMAT:
- Yes/no questions: start with a clear Yes or No, then 1-2 sentences explaining why.
- List and "top N" questions: bullet points only.
- Summary requests: bullet points, one key point per bullet, maximum 8 bullets.
- Multi-step processes: numbered list.
- Explanations: short paragraphs, one idea each.

RULES:
- Never write long dense paragraphs.
- Never invent facts, policy numbers, or timescales.
- If the answer is genuinely not in the extracts, say "The knowledge base does not cover this." \
Do not reason from general knowledge about UK housing law.
- Prefer the most specific policy. If two extracts disagree, say so and cite both.

Stay concise. The best answer is the shortest one that fully addresses the question."""

NO_CONTEXT_ANSWER = "The knowledge base does not cover this."


def format_context(hits: list[tuple[Document, float]]) -> str:
    """Numbered blocks, each tagged with its source so the model can cite it."""
    blocks = []
    for i, (doc, _score) in enumerate(hits, start=1):
        meta = doc.metadata
        tag = f"[{i}] {meta['source_file']} p.{meta['page']}"
        if meta.get("status") == "expired":
            tag += f" (EXPIRED {meta.get('expiry') or 'date unknown'})"
        blocks.append(f"{tag}\n{doc.page_content}")
    return "\n\n---\n\n".join(blocks)


def parse_citations(answer: str, hits: list[tuple[Document, float]]) -> list[dict]:
    """Map [n] markers in the answer back to their source metadata.

    Markers outside the valid range are hallucinated and dropped. If the model
    cited nothing, every source is returned marked inferred, rather than an
    empty list that would read as "grounded in nothing".
    """
    cited: list[int] = []
    for marker in re.findall(r"\[(\d+)\]", answer):
        n = int(marker)
        if 1 <= n <= len(hits) and n not in cited:
            cited.append(n)

    inferred = not cited
    indices = cited or list(range(1, len(hits) + 1))

    citations = []
    for n in indices:
        meta = hits[n - 1][0].metadata
        citations.append(
            {
                "n": n,
                "doc_id": meta["doc_id"],
                "title": meta["title"],
                "source_file": meta["source_file"],
                "page": meta["page"],
                "heading_path": meta["heading_path"],
                "status": meta["status"],
                "expiry": meta.get("expiry") or None,
                "inferred": inferred,
            }
        )
    return citations


def expired_warning(citations: list[dict]) -> str | None:
    """Deterministic banner for expired sources.

    Computed in code, not asked of the prompt, so it is testable and cannot be
    forgotten. Expired policies are still the operative documents staff are
    handed, so they are surfaced with a warning rather than hidden.
    """
    # Inferred citations mean the model cited nothing -- usually because it
    # declined to answer. Warning that a non-answer "draws on" an expired policy
    # is both false and alarming.
    expired = {
        (c["title"], c["expiry"])
        for c in citations
        if c["status"] == "expired" and not c["inferred"]
    }
    if not expired:
        return None
    parts = [f"{title} (expired {expiry or 'date unknown'})" for title, expiry in sorted(expired)]
    return (
        "This answer draws on " + "; ".join(parts) + ", which is past its stated review date. "
        "Verify the current version before acting on it."
    )


def answer(
    question: str,
    hits: list[tuple[Document, float]],
    history: list[tuple[str, str]] | None = None,
) -> dict:
    """Generate a cited answer. Returns {answer, citations, expired_warning}."""
    if not hits:
        return {"answer": NO_CONTEXT_ANSWER, "citations": [], "expired_warning": None}

    from langchain_openai import ChatOpenAI

    messages: list[tuple[str, str]] = [("system", SYSTEM_PROMPT)]
    for past_question, past_answer in history or []:
        messages.append(("human", past_question))
        messages.append(("ai", past_answer))
    messages.append(("human", f"Extracts:\n{format_context(hits)}\n\nQuestion:\n{question}"))

    # temperature=0 alone is not reproducible -- the same question can still
    # come back reworded. seed makes runs near-identical, which matters because
    # the evaluation suite compares answers across runs.
    llm = ChatOpenAI(
        model=config.CHAT_MODEL,
        temperature=0.0,
        seed=config.LLM_SEED,
        api_key=config.OPENAI_API_KEY,
    )
    text = llm.invoke(messages).content.strip()

    citations = parse_citations(text, hits)
    return {
        "answer": text,
        "citations": citations,
        "expired_warning": expired_warning(citations),
    }
