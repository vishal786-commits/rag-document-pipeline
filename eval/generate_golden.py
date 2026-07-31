"""Build a draft golden set from the committed chunk snapshot.

    python -m eval.generate_golden            # writes eval/golden_set.draft.json
    python -m eval.generate_golden --counts   # show what would be generated

Output is a DRAFT. run_eval refuses it until a human has read it and promoted it
to eval/golden_set.json with review_status "approved". LLM-written questions
skew easy and single-hop, and that review is what makes the numbers trustworthy.

Every quote is checked to be a verbatim substring of the chunk it came from.
A question whose quote does not verify is dropped and reported, never repaired.
"""

import argparse
import json
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from eval.metrics import normalise
from rag import config
from rag.retriever import load_chunks

DRAFT_PATH = config.REPO_ROOT / "eval" / "golden_set.draft.json"

TARGET = {"factual": 25, "multi_hop": 12, "table": 7, "summarization": 6}
SEED = 7


class Generated(BaseModel):
    """One question written from one or more chunks."""

    question: str = Field(description="A natural question a housing officer or tenant would ask.")
    gold_answer: str = Field(description="A one or two sentence answer, from the extracts only.")
    quotes: list[str] = Field(
        description=(
            "EXACTLY ONE short VERBATIM quote per extract, in the same order as the "
            "extracts, copied exactly, 5-15 words. One extract means exactly one quote. "
            "Each must appear character for character in its extract."
        )
    )
    must_include: list[str] = Field(
        default_factory=list,
        description="Up to 2 exact strings any correct answer must contain (a number, a role).",
    )


def _llm():
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=config.CHAT_MODEL,
        temperature=0.3,  # a little variety, so 25 questions are not 25 rephrasings
        seed=config.LLM_SEED,
        api_key=config.OPENAI_API_KEY,
    ).with_structured_output(Generated)


def body(chunk) -> str:
    """The chunk without its contextual heading path."""
    return chunk.page_content.split("\n\n", 1)[-1]


# Sections every policy shares. They are real content, but pairing two of them
# produces questions joined by nothing but the template: "how are the Diversity
# & Inclusion Policy and the Smoke Alarm Policy both monitored?" is not a
# multi-hop question, it is two lookups in a trenchcoat.
TEMPLATE_SECTIONS = ("monitoring and review", "related policies", "governance")


def is_substantive(chunk) -> bool:
    path = chunk.metadata["heading_path"].lower()
    return not any(section in path for section in TEMPLATE_SECTIONS)


def extract_block(chunk, n: int) -> str:
    meta = chunk.metadata
    return f"[Extract {n}] {meta['source_file']} p.{meta['page']} -- {meta['heading_path']}\n{body(chunk)}"


def entry(chunk, quote: str, grade: int) -> dict:
    meta = chunk.metadata
    return {
        "chunk_id": meta["id"],
        "doc_id": meta["doc_id"],
        "page": meta["page"],
        "grade": grade,
        "quote": quote,
    }


def verify(chunks, generated: Generated) -> tuple[list[dict], str | None]:
    """Pair each quote with the chunk it came from. Fail loud, never repair.

    Uses the same normalisation the eval will use at scoring time, so a quote
    that verifies here cannot fail to match there.
    """
    # For a multi-extract question, one quote per extract in order -- otherwise
    # a question where the model quoted only the first extract becomes a
    # single-hop question wearing a multi_hop label. For a single extract,
    # several supporting quotes are fine; the first is the one recorded.
    if len(chunks) > 1 and len(generated.quotes) != len(chunks):
        return [], f"expected {len(chunks)} quotes, got {len(generated.quotes)}"
    quotes = generated.quotes[: len(chunks)]
    if not quotes:
        return [], "no quotes returned"

    entries = []
    for i, quote in enumerate(quotes):
        chunk = chunks[i]
        if normalise(quote) not in normalise(chunk.page_content):
            return [], f"quote not verbatim in extract {i + 1}: {quote[:60]!r}"
        grade = 3 if len(chunks) == 1 else (3 if i == 0 else 2)
        entries.append(entry(chunk, quote.strip(), grade))

    if len({e["doc_id"] for e in entries}) != len({c.metadata["doc_id"] for c in chunks}):
        return [], "quotes did not span the intended documents"
    return entries, None


def ask(prompt: str, chunks) -> tuple[dict | None, str | None]:
    extracts = "\n\n".join(extract_block(c, i + 1) for i, c in enumerate(chunks))
    try:
        generated = _llm().invoke([("system", prompt), ("human", extracts)])
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

    entries, problem = verify(chunks, generated)
    if problem:
        return None, problem
    return {
        "question": generated.question.strip(),
        "gold_answer": generated.gold_answer.strip(),
        "relevant": entries,
        "must_include": [s for s in generated.must_include if s][:2],
        "must_not_include": [],
    }, None


FACTUAL_PROMPT = (
    "Write one question answerable ONLY from this extract, as a housing officer or tenant "
    "would ask it. Do not mention 'the extract'. Give one verbatim quote that supports it."
)
MULTI_HOP_PROMPT = (
    "Write ONE question that requires BOTH extracts to answer -- neither alone is enough.\n"
    "It must be a question someone handling a real housing case would actually ask, joining "
    "the two SUBJECTS. Do not join them by both being policies, both being reviewed, or both "
    "being monitored -- that is not a real question.\n"
    "If the two subjects have no plausible connection, say so by returning an empty quotes "
    "list rather than forcing one.\n"
    "Give exactly one verbatim quote from each extract, in order."
)
TABLE_PROMPT = (
    "This extract is a table. Write one question answered by reading a specific value or row "
    "from it. Give one verbatim quote containing that value."
)
SUMMARY_PROMPT = (
    "Write one question asking what this policy covers or requires overall. "
    "Give one verbatim quote that a correct summary would draw on."
)


def generate(chunks) -> tuple[list[dict], list[str]]:
    random.seed(SEED)
    by_doc: dict[str, list] = defaultdict(list)
    for chunk in chunks:
        by_doc[chunk.metadata["doc_id"]].append(chunk)

    questions: list[dict] = []
    problems: list[str] = []
    next_id = [1]

    def add(kind: str, prompt: str, picked) -> None:
        record, problem = ask(prompt, picked)
        if problem:
            problems.append(f"[{kind}] {problem}")
            return
        record["id"] = f"q{next_id[0]:03d}"
        record["type"] = kind
        record["review_status"] = "draft"
        next_id[0] += 1
        questions.append(record)
        print(f"  {kind:<14} {record['question'][:66]}")

    # Factual: stratified so every document is represented at least once.
    print("Factual ...")
    docs = sorted(by_doc)
    prose = {d: [c for c in by_doc[d] if c.metadata["content_type"] == "prose" and len(body(c)) > 250]
             for d in docs}
    pool = [d for d in docs if prose[d]]
    for doc_id in random.sample(pool, min(TARGET["factual"], len(pool))):
        add("factual", FACTUAL_PROMPT, [random.choice(prose[doc_id])])

    # Multi-hop: pair substantive chunks from two DIFFERENT documents.
    print("Multi-hop ...")
    substantive = {d: [c for c in prose[d] if is_substantive(c)] for d in pool}
    hop_pool = [d for d in pool if substantive[d]]
    # A forced pairing is now rejected rather than written up, so attempt more
    # pairs than we need and stop once the quota is met.
    wanted = len(questions) + TARGET["multi_hop"]
    for _ in range(TARGET["multi_hop"] * 3):
        if len(questions) >= wanted:
            break
        a, b = random.sample(hop_pool, 2)
        add(
            "multi_hop",
            MULTI_HOP_PROMPT,
            [random.choice(substantive[a]), random.choice(substantive[b])],
        )

    # Table.
    print("Table ...")
    tables = [c for c in chunks if c.metadata["content_type"] == "table" and len(body(c)) > 200]
    for chunk in random.sample(tables, min(TARGET["table"], len(tables))):
        add("table", TABLE_PROMPT, [chunk])

    # Summarization.
    print("Summarization ...")
    for doc_id in random.sample(pool, min(TARGET["summarization"], len(pool))):
        add("summarization", SUMMARY_PROMPT, [random.choice(prose[doc_id])])

    return questions, problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a draft golden set.")
    parser.add_argument("--counts", action="store_true", help="show the plan and exit")
    args = parser.parse_args(argv)

    chunks = load_chunks(config.CHUNKS_PATH)
    if args.counts:
        kinds = defaultdict(int)
        for c in chunks:
            kinds[c.metadata["content_type"]] += 1
        print(f"chunks: {len(chunks)}  {dict(kinds)}")
        print(f"documents: {len({c.metadata['doc_id'] for c in chunks})}")
        print(f"target: {TARGET} = {sum(TARGET.values())} questions")
        return 0

    config.require("OPENAI_API_KEY", config.OPENAI_API_KEY)
    questions, problems = generate(chunks)

    payload = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator_model": config.CHAT_MODEL,
        "chunks_sha256": json.loads(config.CHUNKS_META_PATH.read_text(encoding="utf-8"))["sha256"],
        "review_status": "draft",
        "questions": questions,
    }
    DRAFT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    kinds = defaultdict(int)
    for q in questions:
        kinds[q["type"]] += 1
    print(f"\nWrote {DRAFT_PATH}")
    print(f"  {len(questions)} questions: {dict(kinds)}")
    if problems:
        print(f"  {len(problems)} dropped (quote did not verify):")
        for p in problems[:10]:
            print(f"    {p}")
    print("\nNow READ the draft, fix or delete weak questions, set review_status to")
    print("'approved' and save it as eval/golden_set.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
