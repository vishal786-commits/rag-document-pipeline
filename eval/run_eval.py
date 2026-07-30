"""Run the evaluation and write a comparable, timestamped report.

    python -m eval.run_eval --offline                 no API keys; BM25 only
    python -m eval.run_eval --mode retrieval          hybrid retrieval metrics
    python -m eval.run_eval --mode all --tag baseline retrieval + generation
    python -m eval.run_eval --compare eval/runs/<file>.json
    python -m eval.run_eval --offline --fail-under "recall@5=0.55"

--offline is the CI gate: it scores BM25 over the committed chunk snapshot, so
it needs no network and still produces real Recall/nDCG numbers. It catches a
broken chunker, a corrupted snapshot, or a mangled golden set -- a genuine test,
not a smoke test.
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from eval.metrics import (
    mean,
    ndcg_at_k,
    normalise,
    precision_at_k,
    precision_ceiling_at_k,
    recall_at_k,
    reciprocal_rank,
)
from rag import config
from rag.retriever import load_chunks, tokenize

GOLDEN_PATH = config.REPO_ROOT / "eval" / "golden_set.json"
RUNS_DIR = config.REPO_ROOT / "eval" / "runs"
REPORTS_DIR = config.REPO_ROOT / "eval" / "reports"
CUTOFFS = (3, 5, 10)


def load_golden(allow_draft: bool) -> dict:
    if not GOLDEN_PATH.exists():
        raise SystemExit(f"No golden set at {GOLDEN_PATH}. Run `python -m eval.generate_golden`.")
    data = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    drafts = [q for q in data["questions"] if q.get("review_status") != "approved"]
    if drafts and not allow_draft:
        raise SystemExit(
            f"{len(drafts)} questions are still 'draft'. Review them and set review_status to "
            "'approved', or pass --allow-draft to score them anyway."
        )
    return data


# ── Retrieval ───────────────────────────────────────────────────────────────
class OfflineRetriever:
    """BM25 over the committed snapshot. No network, no API key."""

    def __init__(self):
        from rank_bm25 import BM25Okapi

        self.docs = load_chunks(config.CHUNKS_PATH)
        self.bm25 = BM25Okapi([tokenize(d.page_content) for d in self.docs])

    def search(self, query: str, k: int):
        scores = self.bm25.get_scores(tokenize(query))
        order = sorted(range(len(self.docs)), key=lambda i: -scores[i])[:k]
        return [(self.docs[i].metadata, self.docs[i].page_content) for i in order]


class HybridRetriever:
    """The production path: Pinecone dense + BM25, fused with RRF."""

    def __init__(self):
        from rag.retriever import KBRetriever

        self.inner = KBRetriever()

    def search(self, query: str, k: int):
        hits = self.inner.search(query, k=k)
        return [(doc.metadata, doc.page_content) for doc, _score in hits]


def score_retrieval(retriever, questions: list[dict], top_k: int) -> list[dict]:
    records = []
    for i, q in enumerate(questions, start=1):
        retrieved = retriever.search(q["question"], k=top_k)
        record = {
            "id": q["id"],
            "type": q["type"],
            "question": q["question"],
            "retrieved": [
                {"id": m.get("id"), "page": m.get("page"), "source": m.get("source_file")}
                for m, _ in retrieved
            ],
            "metrics": {},
        }
        for k in CUTOFFS:
            record["metrics"][f"recall@{k}"] = recall_at_k(retrieved, q["relevant"], k)
            record["metrics"][f"precision@{k}"] = precision_at_k(retrieved, q["relevant"], k)
            record["metrics"][f"ndcg@{k}"] = ndcg_at_k(retrieved, q["relevant"], k)
            # Most questions have a single relevant chunk, so precision@5 cannot
            # exceed 0.2 for them. Carried alongside so the raw number is readable.
            record["ceilings"] = record.get("ceilings", {})
            record["ceilings"][f"precision@{k}"] = precision_ceiling_at_k(q["relevant"], k)
        record["metrics"]["mrr"] = reciprocal_rank(retrieved, q["relevant"], max(CUTOFFS))
        record["_retrieved"] = retrieved
        records.append(record)
        print(f"  [{i}/{len(questions)}] {q['id']} recall@5={record['metrics']['recall@5']:.2f}")
    return records


# ── Generation ──────────────────────────────────────────────────────────────
def score_generation(records: list[dict], questions: dict[str, dict]) -> None:
    """Deterministic string checks plus an LLM judge, per question."""
    from langchain_core.documents import Document
    from langchain_openai import ChatOpenAI
    from pydantic import BaseModel, Field

    from rag.generate import answer as generate_answer

    class Judgement(BaseModel):
        grounded: int = Field(description="1-5: is every claim supported by the extracts?")
        complete: int = Field(description="1-5: does it address the whole question?")
        correct: int = Field(description="1-5: does it agree with the reference answer?")
        citations: int = Field(description="1-5: are the citations present and apt?")
        comment: str = Field(description="One sentence on the weakest aspect.")

    judge = ChatOpenAI(
        model=config.CHAT_MODEL, temperature=0.0, seed=config.LLM_SEED,
        api_key=config.OPENAI_API_KEY,
    ).with_structured_output(Judgement)

    for i, record in enumerate(records, start=1):
        gold = questions[record["id"]]
        hits = [(Document(page_content=t, metadata=m), 1.0) for m, t in record["_retrieved"]]
        result = generate_answer(gold["question"], hits[: config.FINAL_K])
        answer_text = result["answer"]

        # Free, deterministic, and catches the worst failures without a judge.
        norm = normalise(answer_text)
        must = gold.get("must_include") or []
        hit_count = sum(1 for s in must if normalise(s) in norm)

        judgement = judge.invoke(
            [
                (
                    "system",
                    "You grade a RAG answer against reference material. Score 1-5 on each "
                    "axis. Be exacting about grounding: a claim not in the extracts scores "
                    "low even if it is true.",
                ),
                (
                    "human",
                    f"Question: {gold['question']}\n\n"
                    f"Reference answer: {gold['gold_answer']}\n\n"
                    f"Extracts given to the model:\n"
                    + "\n---\n".join(t for _, t in record["_retrieved"][: config.FINAL_K])
                    + f"\n\nAnswer to grade:\n{answer_text}",
                ),
            ]
        )

        record["answer"] = answer_text
        record["citations"] = len(result["citations"])
        record["metrics"].update(
            {
                "must_include": hit_count / len(must) if must else 1.0,
                "grounded": judgement.grounded / 5,
                "complete": judgement.complete / 5,
                "correct": judgement.correct / 5,
                "citation_quality": judgement.citations / 5,
            }
        )
        record["judge_comment"] = judgement.comment
        print(f"  [{i}/{len(records)}] {record['id']} grounded={judgement.grounded}/5")


# ── Aggregation and reporting ───────────────────────────────────────────────
def aggregate(records: list[dict]) -> dict:
    names = sorted({name for r in records for name in r["metrics"]})
    overall = {n: mean([r["metrics"][n] for r in records if n in r["metrics"]]) for n in names}

    ceilings = {
        n: mean([r["ceilings"][n] for r in records if n in r.get("ceilings", {})])
        for n in {c for r in records for c in r.get("ceilings", {})}
    }

    by_type: dict[str, dict] = {}
    grouped = defaultdict(list)
    for r in records:
        grouped[r["type"]].append(r)
    for kind, group in sorted(grouped.items()):
        by_type[kind] = {
            "count": len(group),
            **{n: mean([r["metrics"][n] for r in group if n in r["metrics"]]) for n in names},
        }
    return {"overall": overall, "ceilings": ceilings, "by_type": by_type}


def write_report(path: Path, payload: dict) -> None:
    agg = payload["aggregates"]
    lines = [
        "# Evaluation Report",
        "",
        f"> {payload['started_at']} · mode `{payload['mode']}` · tag `{payload['tag']}`",
        f"> {payload['question_count']} questions · retriever `{payload['retriever']}` · "
        f"chat `{payload['chat_model']}`",
        "",
        "## Overall",
        "",
        "`nominal max` is the best precision achievable if exactly one retrieved chunk matched "
        "each labelled gold chunk. Most questions have a single relevant chunk, so precision@5 "
        "cannot meaningfully exceed 0.2 for them -- read precision against this, not against "
        "1.0. Above 100% is possible and fine: chunks overlap, so one gold quote can appear in "
        "two adjacent chunks and both are genuinely relevant.",
        "",
        "| metric | score | nominal max | % of nominal |",
        "|--------|------:|------------:|-------------:|",
    ]
    for name, value in agg["overall"].items():
        ceiling = agg.get("ceilings", {}).get(name)
        if ceiling:
            lines.append(f"| {name} | {value:.3f} | {ceiling:.3f} | {value / ceiling:.0%} |")
        else:
            lines.append(f"| {name} | {value:.3f} | | |")

    lines += ["", "## By question type", "", "This is the breakdown that says whether a change "
              "helped the thing it was meant to help.", ""]
    names = [n for n in agg["overall"]]
    lines.append("| type | n | " + " | ".join(names) + " |")
    lines.append("|------|--:|" + "|".join(["--:"] * len(names)) + "|")
    for kind, stats in agg["by_type"].items():
        row = " | ".join(f"{stats[n]:.3f}" for n in names)
        lines.append(f"| {kind} | {stats['count']} | {row} |")

    weakest = sorted(payload["records"], key=lambda r: r["metrics"].get("recall@5", 0))[:8]
    lines += ["", "## Weakest retrievals", "", "| id | type | recall@5 | question |",
              "|----|------|---------:|----------|"]
    for r in weakest:
        lines.append(
            f"| {r['id']} | {r['type']} | {r['metrics'].get('recall@5', 0):.2f} | "
            f"{r['question'][:70]} |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def compare(current: dict, baseline_path: Path, tolerance: float) -> int:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    cur, base = current["aggregates"]["overall"], baseline["aggregates"]["overall"]

    print(f"\nComparing against {baseline_path.name} (tolerance {tolerance})")
    print(f"{'metric':<20} {'baseline':>9} {'current':>9} {'delta':>9}")
    regressions = []
    for name in sorted(set(cur) & set(base)):
        delta = cur[name] - base[name]
        flag = ""
        if delta < -tolerance:
            flag = "  REGRESSION"
            regressions.append(name)
        print(f"{name:<20} {base[name]:>9.3f} {cur[name]:>9.3f} {delta:>+9.3f}{flag}")

    if regressions:
        print(f"\nFAIL: {len(regressions)} metric(s) dropped by more than {tolerance}.")
        return 1
    print("\nOK: no regression beyond tolerance.")
    return 0


def check_thresholds(aggregates: dict, thresholds: list[str]) -> int:
    failed = []
    for spec in thresholds:
        name, _, target = spec.partition("=")
        actual = aggregates["overall"].get(name.strip())
        if actual is None:
            failed.append(f"{name}: not measured in this mode")
        elif actual < float(target):
            failed.append(f"{name}: {actual:.3f} < {float(target):.3f}")
    for message in failed:
        print(f"FAIL {message}")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate retrieval and generation.")
    parser.add_argument("--mode", choices=["retrieval", "all"], default="retrieval")
    parser.add_argument("--offline", action="store_true", help="BM25 only; no API keys")
    parser.add_argument("--tag", default="run", help="label for the output files")
    parser.add_argument("--top-k", type=int, default=max(CUTOFFS))
    parser.add_argument("--limit", type=int, help="score only the first N questions")
    parser.add_argument("--allow-draft", action="store_true")
    parser.add_argument("--compare", metavar="RUN_JSON", help="fail if metrics regress")
    parser.add_argument("--tolerance", type=float, default=0.02)
    parser.add_argument("--fail-under", action="append", default=[], metavar="METRIC=VALUE")
    args = parser.parse_args(argv)

    golden = load_golden(args.allow_draft)
    questions = golden["questions"][: args.limit] if args.limit else golden["questions"]

    if args.offline and args.mode == "all":
        raise SystemExit("--offline cannot score generation; use --mode retrieval.")

    retriever = OfflineRetriever() if args.offline else HybridRetriever()
    name = "bm25-offline" if args.offline else "hybrid-rrf"
    started = datetime.now(timezone.utc)

    print(f"Scoring retrieval ({name}, {len(questions)} questions) ...")
    records = score_retrieval(retriever, questions, args.top_k)

    if args.mode == "all":
        print("\nScoring generation ...")
        score_generation(records, {q["id"]: q for q in questions})

    for record in records:
        record.pop("_retrieved", None)

    payload = {
        "started_at": started.isoformat(),
        "tag": args.tag,
        "mode": args.mode,
        "retriever": name,
        "chat_model": config.CHAT_MODEL,
        "embed_model": config.EMBED_MODEL,
        "question_count": len(questions),
        "golden_generated_at": golden.get("generated_at"),
        "aggregates": aggregate(records),
        "records": records,
    }

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    run_path = RUNS_DIR / f"{stamp}_{args.tag}.json"
    run_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_report(REPORTS_DIR / f"{stamp}_{args.tag}.md", payload)

    print("\nOverall:")
    ceilings = payload["aggregates"].get("ceilings", {})
    for metric, value in payload["aggregates"]["overall"].items():
        ceiling = ceilings.get(metric)
        suffix = f"   (nominal max {ceiling:.3f}, {value / ceiling:.0%})" if ceiling else ""
        print(f"  {metric:<18} {value:.3f}{suffix}")
    print(f"\nWrote {run_path}")
    print(f"Wrote {REPORTS_DIR / f'{stamp}_{args.tag}.md'}")

    status = 0
    if args.fail_under:
        status |= check_thresholds(payload["aggregates"], args.fail_under)
    if args.compare:
        status |= compare(payload, Path(args.compare), args.tolerance)
    return status


if __name__ == "__main__":
    sys.exit(main())
