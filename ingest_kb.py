"""
ingest_kb.py — Knowledge-base batch ingestion.

  * PHASE 1 (default): Step 0 preflight + a DRY-RUN report only. No embedding,
    no Pinecone writes, no corpus writes. Writes docs/INGEST_DRYRUN.md.
  * PHASE 2 (--execute / --prepare-only): the real ingest into a single shared
    Pinecone namespace. Per-page read → skip blank pages → drop form tails →
    per-page chunk (carries page numbers) → batched embed → verified upsert →
    save corpus. Writes docs/INGEST_RESULT.md.

  main.py and the /upload, /ask request paths are NOT touched by either phase.

SOURCE OF TRUTH for per-document metadata is docs/CORPUS_SUMMARY.md (its
"Step 1 — Per-document catalogue" table). This script reconciles that table
against the PDFs actually present in kowledgebase/, applies the ingestion
rules (audience, effective/expiry dates, dropped forms, skipped pages), and
carries the resolved metadata onto every chunk written to Pinecone.

DESIGN RULE — no silent sentinels. Every failure is either raised loudly or
collected into an explicit "needs attention" section of the report. Nothing is
swallowed into an empty list / default value. This is a deliberate move away
from the catch-everything-return-empty pattern in the existing src/ modules
(read_pdf→[], embed_chunks→[], store_in_pinecone swallowing exceptions).

Usage:
    python ingest_kb.py                    # Step 0 + dry-run report (phase 1)
    python ingest_kb.py --no-pdf-check     # dry-run, skip opening PDFs
    python ingest_kb.py --prepare-only     # phase 2 offline: read/chunk/plan, no API calls
    python ingest_kb.py --execute          # phase 2 live: embed + upsert to Pinecone
    python ingest_kb.py --execute --fresh  # clear the KB namespace first, then ingest
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

try:  # load .env so keys are available when this script is run standalone
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # phase-1 dry-run does not need it
    pass

# Windows consoles default to cp1252, which can't encode the ·/⚠/emoji used in
# progress output. Reports are always written UTF-8; make stdout match too.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001 - cosmetic only
            pass

# ── Paths (repo-relative, overridable via CLI) ──────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_KB_DIR = REPO_ROOT / "kowledgebase"
DEFAULT_SUMMARY = REPO_ROOT / "docs" / "CORPUS_SUMMARY.md"
DEFAULT_OUT = REPO_ROOT / "docs" / "INGEST_DRYRUN.md"
DEFAULT_RESULT_OUT = REPO_ROOT / "docs" / "INGEST_RESULT.md"

# ── Phase-2 ingest config ───────────────────────────────────────────────────
DEFAULT_NAMESPACE = "knowledgebase"  # single shared namespace for the whole KB
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536                 # must match the Pinecone index (cosine, 1536)
EMBED_BATCH = 128                    # texts per OpenAI embeddings call
UPSERT_BATCH = 100                   # vectors per Pinecone upsert call
CHUNK_SIZE = 900
CHUNK_OVERLAP = 150

# Markers that identify the start of an internal form tail (content-verified on
# Section 20 Policy.pdf, where the S20 Consultation Request form is pp.5-8).
# NB: "consultation request & business case" is deliberately NOT a marker — the
# policy *body* names the form, so it matches too early; "complete this form" is
# the instruction that only appears on the fillable form itself.
FORM_START_MARKERS = (
    "complete this form",
    "send copy of completed form",
)

# ── Reconstructed ingestion rules (shown in the report) ─────────────────────
RULES_DOC = """\
- **Audience** is resolved from the summary's `Doc type` / `Flags`:
  - a `Flags` note of *tenant-facing* → **tenant** (highest priority);
  - `Doc type` of `Policy`, `Policy + form`, or `Landlord policy` → **staff**
    (landlord-facing operational procedure);
  - `Doc type` of `Legislation`, `Govt guidance`, `Govt operating guidance`,
    or `Presentation slides` → **reference** (statutory / external reference);
  - anything else → **UNRESOLVED** and listed explicitly (never defaulted).
- **Dates**: the `Effective → Expiry` cell is parsed as `<effective> → <expiry>`.
  `dd/mm/yyyy`, `d Mon yyyy`, and `d Month yyyy` are accepted; `UNKNOWN` and any
  unparseable value become an explicit issue (never a silent `None`).
- **Status**: `expiry < today` → **expired**; a valid future expiry → **current**;
  no expiry → **unknown** (reported, not assumed current).
- **Forms dropped**: a `Doc type` containing `form`, or a `Flags` note naming a
  workflow/approval *form*, marks the document's form section for dropping.
- **Pages skipped**: the count of `N image/blank page(s)` parsed from `Flags`.
- **Exclusion candidate**: carried through from a `Flags` note of *exclusion
  candidate* (a human decision, surfaced not acted on).
"""

# doc_type -> audience (before the tenant-facing override)
_STAFF_TYPES = {"policy", "policy + form", "landlord policy"}
_REFERENCE_TYPES = {
    "legislation",
    "govt guidance",
    "govt operating guidance",
    "presentation slides",
}

# tokens dropped when fuzzy-matching a summary row title to a filename
_MATCH_STOPWORDS = {"the", "and", "for", "of", "a", "an", "to", "in", "policy"}
_MATCH_THRESHOLD = 0.45


# ── Data model ──────────────────────────────────────────────────────────────
@dataclass
class SummaryRow:
    """One parsed row of the Step 1 catalogue table."""

    idx: str
    title: str
    pages: Optional[int]
    origin: str
    doc_type: str
    dates_raw: str
    version: str
    flags: str


@dataclass
class DocPlan:
    """The resolved ingestion plan for one matched (row, file) pair."""

    row: SummaryRow
    file: Path
    audience: str
    audience_issue: Optional[str]
    effective: Optional[date]
    effective_issue: Optional[str]
    expiry: Optional[date]
    expiry_issue: Optional[str]
    status: str  # current | expired | unknown
    forms_dropped: bool
    pages_skipped: int
    exclusion_candidate: bool
    pdf_pages: Optional[int]  # from opening the PDF (None if not checked/failed)
    pdf_error: Optional[str]
    page_count_mismatch: Optional[str]

    @property
    def issues(self) -> list[str]:
        out: list[str] = []
        if self.audience_issue:
            out.append(f"audience: {self.audience_issue}")
        if self.effective_issue:
            out.append(f"effective date: {self.effective_issue}")
        if self.expiry_issue:
            out.append(f"expiry date: {self.expiry_issue}")
        if self.pdf_error:
            out.append(f"PDF parse: {self.pdf_error}")
        if self.page_count_mismatch:
            out.append(f"page count: {self.page_count_mismatch}")
        return out


@dataclass
class Reconciliation:
    matched: list[tuple[SummaryRow, Path]] = field(default_factory=list)
    unmatched_rows: list[SummaryRow] = field(default_factory=list)
    unmatched_files: list[Path] = field(default_factory=list)


class DryRunError(RuntimeError):
    """Raised for preflight failures that must stop the run loudly."""


# ── Step 0a: load the summary table ─────────────────────────────────────────
def load_summary_rows(summary_path: Path) -> list[SummaryRow]:
    if not summary_path.exists():
        raise DryRunError(f"Summary file not found: {summary_path}")

    text = summary_path.read_text(encoding="utf-8")

    # The catalogue is the markdown table whose header names '# | File | Pages'.
    lines = text.splitlines()
    header_i = None
    for i, line in enumerate(lines):
        norm = line.lower().replace(" ", "")
        if norm.startswith("|#|file|pages|"):
            header_i = i
            break
    if header_i is None:
        raise DryRunError(
            f"Could not locate the Step 1 catalogue table (header '| # | File | Pages | ...') "
            f"in {summary_path}. The summary format may have changed."
        )

    rows: list[SummaryRow] = []
    # data rows start two lines after the header (skip the |---|---| separator)
    for line in lines[header_i + 2 :]:
        if not line.strip().startswith("|"):
            break  # table ended
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 9:
            continue
        idx, title, pages_raw, origin, doc_type, _subject, dates_raw, ver, flags = cells[:9]
        rows.append(
            SummaryRow(
                idx=_strip_md(idx),
                title=_strip_md(title),
                pages=_parse_int(pages_raw),
                origin=_strip_md(origin).upper(),
                doc_type=_strip_md(doc_type),
                dates_raw=_strip_md(dates_raw),
                version=_strip_md(ver),
                flags=_strip_md(flags),
            )
        )

    if not rows:
        raise DryRunError(f"Located the catalogue header but parsed zero rows in {summary_path}.")
    return rows


def _strip_md(s: str) -> str:
    return s.replace("**", "").strip()


def _parse_int(s: str) -> Optional[int]:
    m = re.search(r"\d+", s)
    return int(m.group()) if m else None


# ── Step 0b: list PDFs on disk ──────────────────────────────────────────────
def list_pdfs(kb_dir: Path) -> list[Path]:
    if not kb_dir.exists():
        raise DryRunError(f"Knowledge-base directory not found: {kb_dir}")
    pdfs = sorted(p for p in kb_dir.glob("*.pdf") if p.is_file())
    if not pdfs:
        raise DryRunError(f"No PDF files found in {kb_dir}")
    return pdfs


# ── Step 0c: reconcile rows <-> files by fuzzy title match ──────────────────
def _tokens(name: str) -> set[str]:
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", " ", name)
    return {t for t in name.split() if t and t not in _MATCH_STOPWORDS}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def reconcile(rows: list[SummaryRow], files: list[Path]) -> Reconciliation:
    """Greedy one-to-one match: highest-scoring (row, file) pairs first."""
    scored: list[tuple[float, int, int]] = []
    row_tokens = [_tokens(r.title) for r in rows]
    file_tokens = [_tokens(f.stem) for f in files]
    for ri in range(len(rows)):
        for fi in range(len(files)):
            s = _jaccard(row_tokens[ri], file_tokens[fi])
            if s >= _MATCH_THRESHOLD:
                scored.append((s, ri, fi))
    scored.sort(key=lambda t: (-t[0], t[1], t[2]))

    used_rows: set[int] = set()
    used_files: set[int] = set()
    recon = Reconciliation()
    for s, ri, fi in scored:
        if ri in used_rows or fi in used_files:
            continue
        used_rows.add(ri)
        used_files.add(fi)
        recon.matched.append((rows[ri], files[fi]))

    recon.unmatched_rows = [rows[i] for i in range(len(rows)) if i not in used_rows]
    recon.unmatched_files = [files[i] for i in range(len(files)) if i not in used_files]
    # stable order for the report
    recon.matched.sort(key=lambda pair: _row_sort_key(pair[0]))
    return recon


def _row_sort_key(r: SummaryRow):
    m = re.search(r"\d+", r.idx)
    return (int(m.group()) if m else 9999, r.title)


# ── Date parsing (deliberately explicit about failures) ─────────────────────
_DATE_FORMATS = ("%d/%m/%Y", "%d %b %Y", "%d %B %Y")


def _parse_date_token(tok: str) -> tuple[Optional[date], Optional[str]]:
    tok = tok.replace("**", "").strip()
    if not tok:
        return None, "empty"
    if tok.upper().startswith("UNKNOWN"):
        return None, f"marked UNKNOWN in summary ({tok!r})"
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(tok, fmt).date(), None
        except ValueError:
            pass
    # embedded dd/mm/yyyy, e.g. "Version 1.0 eff 02/03/2026"
    m = re.search(r"\d{1,2}/\d{1,2}/\d{4}", tok)
    if m:
        try:
            return datetime.strptime(m.group(), "%d/%m/%Y").date(), None
        except ValueError:
            pass
    # embedded "d Mon yyyy", e.g. "Updated 4 Dec 2025", "Enacted 20 Dec 2018"
    m = re.search(r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}", tok)
    if m:
        for fmt in ("%d %b %Y", "%d %B %Y"):
            try:
                return datetime.strptime(m.group(), fmt).date(), None
            except ValueError:
                pass
    return None, f"could not parse a date from {tok!r}"


def parse_effective_expiry(dates_raw: str):
    cell = dates_raw.replace("**", "").strip()
    if "→" in cell:  # '→'
        left, right = cell.split("→", 1)
        eff, eff_issue = _parse_date_token(left)
        exp, exp_issue = _parse_date_token(right)
        return eff, eff_issue, exp, exp_issue
    # no arrow: at most a single structured date, no expiry
    eff, eff_issue = _parse_date_token(cell)
    return eff, eff_issue, None, "no expiry given in summary"


# ── Rule application ────────────────────────────────────────────────────────
def resolve_audience(row: SummaryRow) -> tuple[str, Optional[str]]:
    flags = row.flags.lower()
    if "tenant-facing" in flags or "tenant facing" in flags:
        return "tenant", None
    dt = row.doc_type.lower().strip()
    if dt in _STAFF_TYPES:
        return "staff", None
    if dt in _REFERENCE_TYPES:
        return "reference", None
    return "UNRESOLVED", f"doc type {row.doc_type!r} maps to no audience rule"


def parse_skipped_pages(flags: str) -> int:
    m = re.search(r"(\d+)\s+image/blank page", flags.lower())
    return int(m.group(1)) if m else 0


def has_form(row: SummaryRow) -> bool:
    if re.search(r"\bform\b", row.doc_type, re.IGNORECASE):
        return True
    return bool(re.search(r"\bform\b", row.flags, re.IGNORECASE))


def check_pdf(path: Path) -> tuple[Optional[int], Optional[str]]:
    """Open the PDF just enough to confirm it parses and count pages."""
    try:
        from pypdf import PdfReader
    except ImportError as e:
        return None, f"pypdf unavailable ({e})"
    try:
        reader = PdfReader(str(path))
        return len(reader.pages), None
    except Exception as e:  # noqa: BLE001 - reported, not swallowed
        return None, f"{type(e).__name__}: {e}"


def build_plan(row: SummaryRow, file: Path, today: date, do_pdf_check: bool) -> DocPlan:
    audience, audience_issue = resolve_audience(row)
    eff, eff_issue, exp, exp_issue = parse_effective_expiry(row.dates_raw)

    if exp is None:
        status = "unknown"
    elif exp < today:
        status = "expired"
    else:
        status = "current"

    pdf_pages: Optional[int] = None
    pdf_error: Optional[str] = None
    mismatch: Optional[str] = None
    if do_pdf_check:
        pdf_pages, pdf_error = check_pdf(file)
        if pdf_pages is not None and row.pages is not None and pdf_pages != row.pages:
            mismatch = f"PDF has {pdf_pages} pages, summary says {row.pages}"

    return DocPlan(
        row=row,
        file=file,
        audience=audience,
        audience_issue=audience_issue,
        effective=eff,
        effective_issue=eff_issue,
        expiry=exp,
        expiry_issue=exp_issue,
        status=status,
        forms_dropped=has_form(row),
        pages_skipped=parse_skipped_pages(row.flags),
        exclusion_candidate="exclusion candidate" in row.flags.lower(),
        pdf_pages=pdf_pages,
        pdf_error=pdf_error,
        page_count_mismatch=mismatch,
    )


# ── Report rendering ────────────────────────────────────────────────────────
def _fmt_date(d: Optional[date]) -> str:
    return d.isoformat() if d else "—"


def render_report(
    plans: list[DocPlan],
    recon: Reconciliation,
    today: date,
    kb_dir: Path,
    summary_path: Path,
    pdf_checked: bool,
) -> str:
    n = len(plans)
    by_aud: dict[str, int] = {}
    for p in plans:
        by_aud[p.audience] = by_aud.get(p.audience, 0) + 1
    expired = [p for p in plans if p.status == "expired"]
    unknown_status = [p for p in plans if p.status == "unknown"]
    forms = [p for p in plans if p.forms_dropped]
    skipped = [p for p in plans if p.pages_skipped > 0]
    total_skipped = sum(p.pages_skipped for p in plans)
    date_fail = [p for p in plans if p.effective_issue or p.expiry_issue]
    aud_fail = [p for p in plans if p.audience_issue]
    pdf_fail = [p for p in plans if p.pdf_error]
    mism = [p for p in plans if p.page_count_mismatch]
    excl = [p for p in plans if p.exclusion_candidate]

    L: list[str] = []
    w = L.append

    w("# Knowledge-Base Ingestion — Dry-Run Report")
    w("")
    w(f"> Generated: {datetime.now().isoformat(timespec='seconds')} · "
      f"\"Today\" for expiry checks: **{today.isoformat()}**")
    w("> **Dry run — report only.** No embeddings, no Pinecone writes, no corpus writes. "
      "`main.py` and the `/upload`, `/ask` paths were not touched. No secrets are read or printed.")
    w("")
    w(f"- **Source of truth:** `{summary_path.relative_to(REPO_ROOT)}` (Step 1 catalogue)")
    w(f"- **PDF directory:** `{kb_dir.relative_to(REPO_ROOT)}`")
    w(f"- **PDF parse check:** {'enabled (each PDF opened)' if pdf_checked else 'skipped (--no-pdf-check)'}")
    w("")

    # Rules
    w("## Rules applied")
    w("")
    w("> Reconstructed from the corpus summary (original spec was truncated). "
      "Review and correct in `ingest_kb.py`.")
    w("")
    w(RULES_DOC)
    w("")

    # Headline
    w("## Summary")
    w("")
    w(f"- **Documents planned for ingestion:** {n} "
      f"(matched to {n} of {len(recon.matched) + len(recon.unmatched_files)} PDFs on disk)")
    w(f"- **Audience mix:** " + ", ".join(f"{v} {k}" for k, v in sorted(by_aud.items())))
    w(f"- **Status:** {len(expired)} expired · "
      f"{n - len(expired) - len(unknown_status)} current · {len(unknown_status)} unknown")
    w(f"- **Forms dropped:** {len(forms)} document(s)")
    w(f"- **Pages skipped (image/blank):** {total_skipped} page(s) across {len(skipped)} document(s)")
    w(f"- **Exclusion candidates flagged:** {len(excl)}")
    w("")
    total_issues = len(recon.unmatched_rows) + len(recon.unmatched_files) + len(date_fail) + len(aud_fail) + len(pdf_fail) + len(mism)
    w(f"- **⚠ Needs attention:** {total_issues} item(s) — see [Needs attention](#needs-attention).")
    w("")

    # Per-document table
    w("## Per-document plan")
    w("")
    w("| # | Document | Audience | Effective | Expiry | Status | Forms | Skip pg | Origin | Ver |")
    w("|---|----------|----------|-----------|--------|--------|-------|--------:|--------|-----|")
    for p in plans:
        aud = p.audience if not p.audience_issue else f"**{p.audience}**"
        status_cell = {"expired": "🔴 expired", "current": "🟢 current", "unknown": "⚪ unknown"}[p.status]
        eff = _fmt_date(p.effective) + (" ⚠" if p.effective_issue else "")
        exp = _fmt_date(p.expiry) + (" ⚠" if p.expiry_issue else "")
        w(f"| {p.row.idx} | {p.file.name} | {aud} | {eff} | {exp} | {status_cell} | "
          f"{'drop' if p.forms_dropped else '—'} | {p.pages_skipped or '—'} | {p.row.origin} | {p.row.version or '—'} |")
    w("")

    # Needs attention
    w('<a id="needs-attention"></a>')
    w("## Needs attention")
    w("")
    if total_issues == 0:
        w("_Nothing flagged — every row matched a file, every date and audience resolved, "
          "and every PDF parsed._")
        w("")
    else:
        _section(w, "Summary rows with no matching PDF", [r.title for r in recon.unmatched_rows])
        _section(w, "PDFs with no matching summary row", [f.name for f in recon.unmatched_files])
        _section(w, "Audience could not be resolved",
                 [f"{p.file.name} — {p.audience_issue}" for p in aud_fail])
        _section(w, "Date parse issues",
                 [f"{p.file.name} — raw `{p.row.dates_raw}` — "
                  + "; ".join(x for x in [p.effective_issue and f'effective: {p.effective_issue}',
                                          p.expiry_issue and f'expiry: {p.expiry_issue}'] if x)
                  for p in date_fail])
        _section(w, "PDF parse failures", [f"{p.file.name} — {p.pdf_error}" for p in pdf_fail])
        _section(w, "Page-count mismatch (PDF vs summary)",
                 [f"{p.file.name} — {p.page_count_mismatch}" for p in mism])

    # Informational rollups
    w("## Forms dropped")
    w("")
    if forms:
        for p in forms:
            w(f"- **{p.file.name}** — {p.row.flags}")
    else:
        w("_None._")
    w("")

    w("## Pages skipped (image/blank)")
    w("")
    if skipped:
        for p in skipped:
            w(f"- **{p.file.name}** — {p.pages_skipped} page(s)")
        w("")
        w(f"_Total: {total_skipped} page(s). Counts come from the summary's `Flags` "
          "(`N image/blank page`); slide-sparse pages not tagged that way are not counted here._")
    else:
        w("_None._")
    w("")

    w("## Expired policies (would ingest with an expired-status flag)")
    w("")
    if expired:
        for p in sorted(expired, key=lambda x: x.expiry or today):
            w(f"- **{p.file.name}** — expired {_fmt_date(p.expiry)} ({p.row.version or 'no version'})")
    else:
        w("_None._")
    w("")

    w("## Exclusion candidates (human decision — flagged, not acted on)")
    w("")
    if excl:
        for p in excl:
            w(f"- **{p.file.name}** ({p.row.origin}) — {p.row.flags}")
    else:
        w("_None._")
    w("")

    w("---")
    w("")
    w("_Next phase (not in this run): batch-embed and upsert the planned documents, "
      "carrying audience / effective / expiry / status as chunk metadata, dropping the "
      "flagged form sections and skipped pages. This report is the gate for that step._")
    w("")
    return "\n".join(L)


def _section(w, title: str, items: list[str]) -> None:
    if not items:
        return
    w(f"### {title} ({len(items)})")
    w("")
    for it in items:
        w(f"- {it}")
    w("")


# ── Orchestration ───────────────────────────────────────────────────────────
def run_dry_run(kb_dir: Path, summary_path: Path, out_path: Path, do_pdf_check: bool) -> Reconciliation:
    today = date.today()

    print(f"[Step 0] Loading catalogue from {summary_path} ...")
    rows = load_summary_rows(summary_path)
    print(f"[Step 0] Parsed {len(rows)} catalogue rows.")

    print(f"[Step 0] Listing PDFs in {kb_dir} ...")
    files = list_pdfs(kb_dir)
    print(f"[Step 0] Found {len(files)} PDF file(s).")

    print("[Step 0] Reconciling rows <-> files ...")
    recon = reconcile(rows, files)
    print(f"[Step 0] Matched {len(recon.matched)}; "
          f"{len(recon.unmatched_rows)} row(s) unmatched; "
          f"{len(recon.unmatched_files)} file(s) unmatched.")

    print(f"[Dry-run] Applying rules"
          f"{' + opening each PDF' if do_pdf_check else ''} ...")
    plans = [build_plan(r, f, today, do_pdf_check) for r, f in recon.matched]

    report = render_report(plans, recon, today, kb_dir, summary_path, do_pdf_check)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"[Dry-run] Wrote report -> {out_path}")

    n_issues = sum(len(p.issues) for p in plans) + len(recon.unmatched_rows) + len(recon.unmatched_files)
    print(f"[Dry-run] {len(plans)} document(s) planned; {n_issues} issue(s) flagged for attention.")
    return recon


# ════════════════════════════════════════════════════════════════════════════
# PHASE 2 — real ingest
# ════════════════════════════════════════════════════════════════════════════
class IngestError(RuntimeError):
    """Raised for phase-2 failures that must stop the run loudly."""


@dataclass
class IngestChunk:
    page: int          # 1-based page number in the original PDF (for citations)
    chunk_index: int   # 0-based index within the document
    text: str


@dataclass
class DocIngest:
    """The prepared (offline) ingest for one document — before embedding."""

    plan: DocPlan
    doc_id: str
    chunks: list[IngestChunk] = field(default_factory=list)
    kept_pages: list[int] = field(default_factory=list)
    skipped_pages: list[int] = field(default_factory=list)   # blank/image pages
    dropped_form_pages: list[int] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)          # explicit, never swallowed


# ── Slugs & PDF reading ─────────────────────────────────────────────────────
def _slug(stem: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return s or "doc"


def assign_doc_ids(files: list[Path]) -> dict[Path, str]:
    ids: dict[Path, str] = {}
    seen: dict[str, int] = {}
    for f in files:
        base = _slug(f.stem)
        n = seen.get(base, 0)
        seen[base] = n + 1
        ids[f] = base if n == 0 else f"{base}-{n}"
    return ids


def read_pdf_pages(path: Path) -> list[tuple[int, Optional[str]]]:
    """Return [(page_no, text_or_None)]. Raises loudly if the PDF cannot open."""
    from pypdf import PdfReader

    try:
        reader = PdfReader(str(path))
    except Exception as e:  # noqa: BLE001 - re-raised as a typed, explicit failure
        raise IngestError(f"Cannot open PDF {path.name}: {type(e).__name__}: {e}") from e

    pages: list[tuple[int, Optional[str]]] = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text()
        except Exception as e:  # noqa: BLE001
            raise IngestError(
                f"Failed extracting text from {path.name} page {i + 1}: {type(e).__name__}: {e}"
            ) from e
        pages.append((i + 1, text))
    return pages


def detect_form_start(pages: list[tuple[int, Optional[str]]]) -> Optional[int]:
    """First page (skipping the cover) whose text starts an internal form tail."""
    for page_no, text in pages:
        if page_no == 1 or not text:
            continue
        low = text.lower()
        if any(marker in low for marker in FORM_START_MARKERS):
            return page_no
    return None


# ── Offline preparation (read → skip → drop → chunk) ────────────────────────
def _make_splitter():
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    return RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )


def prepare_document(plan: DocPlan, doc_id: str, splitter) -> DocIngest:
    di = DocIngest(plan=plan, doc_id=doc_id)
    pages = read_pdf_pages(plan.file)

    # Which trailing pages are a form we should drop?
    form_start: Optional[int] = None
    if plan.forms_dropped:
        form_start = detect_form_start(pages)
        if form_start is None:
            di.issues.append(
                "flagged as containing a form, but no form-start marker was found — "
                "no pages dropped (not guessing a boundary)"
            )

    chunk_index = 0
    for page_no, text in pages:
        if form_start is not None and page_no >= form_start:
            di.dropped_form_pages.append(page_no)
            continue
        if not text or not text.strip():
            di.skipped_pages.append(page_no)   # blank / image-only page
            continue
        di.kept_pages.append(page_no)
        for piece in splitter.split_text(text):
            piece = piece.strip()
            if not piece:
                continue
            di.chunks.append(IngestChunk(page=page_no, chunk_index=chunk_index, text=piece))
            chunk_index += 1

    if not di.chunks:
        di.issues.append("produced 0 chunks — nothing would be ingested for this document")

    # Cross-check actual blank pages against the summary's flagged count (report, don't fail).
    if len(di.skipped_pages) != plan.pages_skipped:
        di.issues.append(
            f"blank-page count mismatch: detected {len(di.skipped_pages)} "
            f"(pages {di.skipped_pages or '—'}), summary flagged {plan.pages_skipped}"
        )
    return di


def prepare_documents(plans: list[DocPlan], doc_ids: dict[Path, str]) -> list[DocIngest]:
    splitter = _make_splitter()
    out: list[DocIngest] = []
    for p in plans:
        di = prepare_document(p, doc_ids[p.file], splitter)
        out.append(di)
        print(f"  · {p.file.name}: {len(di.chunks)} chunks "
              f"(kept {len(di.kept_pages)}p, skipped {len(di.skipped_pages)}p, "
              f"dropped-form {len(di.dropped_form_pages)}p)"
              + (f"  ⚠ {len(di.issues)} issue(s)" if di.issues else ""))
    return out


# ── Chunk metadata (carried onto every Pinecone vector) ─────────────────────
def chunk_metadata(di: DocIngest, ch: IngestChunk) -> dict:
    p = di.plan
    md: dict = {
        "text": ch.text,
        "source_file": p.file.name,
        "doc_id": di.doc_id,
        "page": ch.page,
        "chunk_index": ch.chunk_index,
        "audience": p.audience,
        "origin": p.row.origin,
        "status": p.status,
    }
    # Pinecone rejects None metadata values — include only what we actually have.
    if p.effective:
        md["effective"] = p.effective.isoformat()
    if p.expiry:
        md["expiry"] = p.expiry.isoformat()
    if p.row.version:
        md["version"] = p.row.version
    return md


# ── Embedding (batched, fail-loud, dimension-checked) ───────────────────────
def embed_texts(texts: list[str]) -> list[list[float]]:
    from openai import OpenAI

    client = OpenAI()
    vectors: list[list[float]] = []
    total = len(texts)
    for start in range(0, total, EMBED_BATCH):
        batch = texts[start : start + EMBED_BATCH]
        try:
            resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        except Exception as e:  # noqa: BLE001
            raise IngestError(
                f"Embedding call failed for batch at offset {start}: {type(e).__name__}: {e}"
            ) from e
        if len(resp.data) != len(batch):
            raise IngestError(
                f"Embedding count mismatch at offset {start}: "
                f"sent {len(batch)}, got {len(resp.data)}"
            )
        for item in sorted(resp.data, key=lambda d: d.index):
            vec = item.embedding
            if len(vec) != EMBEDDING_DIM:
                raise IngestError(
                    f"Unexpected embedding dimension {len(vec)} (expected {EMBEDDING_DIM})"
                )
            vectors.append(vec)
        print(f"  · embedded {min(start + EMBED_BATCH, total)}/{total}")
    return vectors


# ── Pinecone (verified upsert; no success-on-failed-write) ──────────────────
def get_pinecone_index():
    import os

    from pinecone import Pinecone

    name = os.getenv("PINECONE_INDEX_NAME")
    if not name:
        raise IngestError("PINECONE_INDEX_NAME is not set.")
    if not os.getenv("PINECONE_API_KEY"):
        raise IngestError("PINECONE_API_KEY is not set.")
    return Pinecone(api_key=os.getenv("PINECONE_API_KEY")).Index(name)


def _upserted_count(resp) -> Optional[int]:
    if hasattr(resp, "upserted_count"):
        return resp.upserted_count
    if isinstance(resp, dict):
        return resp.get("upserted_count")
    return None


def clear_namespace(index, namespace: str) -> None:
    try:
        index.delete(delete_all=True, namespace=namespace)
        print(f"[ingest] Cleared namespace '{namespace}'.")
    except Exception as e:  # noqa: BLE001
        msg = str(e).lower()
        if "not found" in msg or "404" in msg or "namespace" in msg:
            print(f"[ingest] Namespace '{namespace}' had nothing to clear ({type(e).__name__}).")
        else:
            raise IngestError(f"Failed to clear namespace '{namespace}': {e}") from e


def upsert_vectors(index, vectors: list[dict], namespace: str) -> int:
    """Upsert in batches and VERIFY the write. Returns total upserted count."""
    total_upserted = 0
    for start in range(0, len(vectors), UPSERT_BATCH):
        batch = vectors[start : start + UPSERT_BATCH]
        try:
            resp = index.upsert(vectors=batch, namespace=namespace)
        except Exception as e:  # noqa: BLE001
            raise IngestError(
                f"Pinecone upsert failed for batch at offset {start}: {type(e).__name__}: {e}"
            ) from e
        n = _upserted_count(resp)
        if n is None:
            raise IngestError(
                f"Pinecone upsert at offset {start} returned no upserted_count — cannot confirm the write."
            )
        if n != len(batch):
            raise IngestError(
                f"Pinecone upsert at offset {start} confirmed {n} of {len(batch)} vectors."
            )
        total_upserted += n
        print(f"  · upserted {total_upserted}/{len(vectors)}")
    return total_upserted


# ── Phase-2 orchestration ────────────────────────────────────────────────────
def run_ingest(
    kb_dir: Path,
    summary_path: Path,
    out_path: Path,
    namespace: str,
    prepare_only: bool,
    fresh: bool,
) -> int:
    today = date.today()

    print(f"[Step 0] Loading catalogue from {summary_path} ...")
    rows = load_summary_rows(summary_path)
    files = list_pdfs(kb_dir)
    recon = reconcile(rows, files)
    print(f"[Step 0] Matched {len(recon.matched)}; "
          f"{len(recon.unmatched_rows)} row(s) / {len(recon.unmatched_files)} file(s) unmatched.")
    if recon.unmatched_rows or recon.unmatched_files:
        raise IngestError(
            "Reconciliation is not clean (unmatched rows or files). Resolve via the dry-run "
            "report before ingesting — refusing to ingest a partial corpus."
        )

    plans = [build_plan(r, f, today, do_pdf_check=False) for r, f in recon.matched]
    doc_ids = assign_doc_ids([f for _, f in recon.matched])

    print(f"[Prepare] Reading + chunking {len(plans)} document(s) (offline) ...")
    docs = prepare_documents(plans, doc_ids)

    total_chunks = sum(len(d.chunks) for d in docs)
    total_skipped = sum(len(d.skipped_pages) for d in docs)
    total_dropped = sum(len(d.dropped_form_pages) for d in docs)
    print(f"[Prepare] {total_chunks} chunks · {total_skipped} pages skipped · "
          f"{total_dropped} form pages dropped.")

    upserted = 0
    index_stats: Optional[str] = None

    if prepare_only:
        print("[Prepare-only] Skipping embedding/upsert (no API calls).")
    else:
        # Flatten to (metadata, id, text) preserving order for embedding alignment.
        flat: list[tuple[DocIngest, IngestChunk]] = [
            (d, ch) for d in docs for ch in d.chunks
        ]
        if not flat:
            raise IngestError("No chunks to ingest across the entire corpus.")

        print(f"[Embed] Embedding {len(flat)} chunk(s) with {EMBEDDING_MODEL} ...")
        embeddings = embed_texts([ch.text for _, ch in flat])
        if len(embeddings) != len(flat):
            raise IngestError(
                f"Embedding/chunk count mismatch: {len(embeddings)} vs {len(flat)}."
            )

        vectors = [
            {
                "id": f"{d.doc_id}#{ch.chunk_index}",
                "values": emb,
                "metadata": chunk_metadata(d, ch),
            }
            for (d, ch), emb in zip(flat, embeddings)
        ]

        index = get_pinecone_index()
        if fresh:
            clear_namespace(index, namespace)

        print(f"[Upsert] Writing {len(vectors)} vector(s) to namespace '{namespace}' ...")
        upserted = upsert_vectors(index, vectors, namespace)
        if upserted != len(vectors):
            raise IngestError(f"Upsert incomplete: {upserted}/{len(vectors)} confirmed.")

        # Save the full chunk-text corpus (List[str]) so /ask's BM25 (get_corpus) works.
        from src.corpus_store import save_corpus

        save_corpus(namespace, [ch.text for _, ch in flat])
        print(f"[Corpus] Saved {len(flat)} chunk texts under namespace '{namespace}'.")

        try:
            stats = index.describe_index_stats()
            ns = getattr(stats, "namespaces", None) or (stats.get("namespaces") if isinstance(stats, dict) else {})
            entry = ns.get(namespace) if ns else None
            count = getattr(entry, "vector_count", None) if entry is not None else None
            if count is None and isinstance(entry, dict):
                count = entry.get("vector_count")
            index_stats = f"{count} vector(s) currently in namespace '{namespace}'" if count is not None else None
        except Exception as e:  # noqa: BLE001 - stats are best-effort, never gate success
            index_stats = f"(could not read index stats: {type(e).__name__})"

    report = render_result_report(
        docs, namespace, today,
        prepare_only=prepare_only, fresh=fresh, upserted=upserted, index_stats=index_stats,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"[Report] Wrote {out_path}")

    n_issues = sum(len(d.issues) for d in docs)
    print(f"[Done] {len(docs)} docs · {total_chunks} chunks · "
          f"{'prepared (no upsert)' if prepare_only else f'{upserted} vectors upserted'} · "
          f"{n_issues} issue(s) flagged.")
    return 0


def render_result_report(
    docs: list[DocIngest],
    namespace: str,
    today: date,
    prepare_only: bool,
    fresh: bool,
    upserted: int,
    index_stats: Optional[str],
) -> str:
    total_chunks = sum(len(d.chunks) for d in docs)
    total_skipped = sum(len(d.skipped_pages) for d in docs)
    total_dropped = sum(len(d.dropped_form_pages) for d in docs)
    flagged = [d for d in docs if d.issues]

    L: list[str] = []
    w = L.append
    w("# Knowledge-Base Ingestion — Result")
    w("")
    mode = "PREPARE-ONLY (offline, no API calls)" if prepare_only else "EXECUTE (embedded + upserted)"
    w(f"> Generated: {datetime.now().isoformat(timespec='seconds')} · Mode: **{mode}**")
    w(f"> Namespace: **`{namespace}`**{' · cleared first (--fresh)' if fresh and not prepare_only else ''} · "
      f"Model: `{EMBEDDING_MODEL}` ({EMBEDDING_DIM}-d) · \"Today\": {today.isoformat()}")
    w("> `main.py` and the `/upload`, `/ask` paths were not modified. No secret values are printed.")
    w("")
    w("## Summary")
    w("")
    w(f"- **Documents ingested:** {len(docs)}")
    w(f"- **Chunks produced:** {total_chunks}")
    if not prepare_only:
        w(f"- **Vectors upserted (confirmed):** {upserted}")
        if index_stats:
            w(f"- **Index stats:** {index_stats}")
    w(f"- **Pages skipped (blank/image):** {total_skipped}")
    w(f"- **Form pages dropped:** {total_dropped}")
    w(f"- **Documents with issues flagged:** {len(flagged)}")
    w("")

    w("## Chunk metadata schema")
    w("")
    w("Every vector carries: `text`, `source_file`, `doc_id`, `page` (1-based, original "
      "PDF page — enables citations), `chunk_index`, `audience`, `origin`, `status`, and "
      "`effective` / `expiry` / `version` when known. Vector id = `{doc_id}#{chunk_index}` "
      "(globally unique within the shared namespace).")
    w("")

    w("## Per-document result")
    w("")
    w("| # | Document | Audience | Status | Pages kept | Skip | Form-drop | Chunks |")
    w("|---|----------|----------|--------|-----------:|-----:|----------:|-------:|")
    for d in docs:
        p = d.plan
        status_cell = {"expired": "🔴", "current": "🟢", "unknown": "⚪"}[p.status] + " " + p.status
        w(f"| {p.row.idx} | {p.file.name} | {p.audience} | {status_cell} | "
          f"{len(d.kept_pages)} | {len(d.skipped_pages) or '—'} | "
          f"{len(d.dropped_form_pages) or '—'} | {len(d.chunks)} |")
    w("")

    w("## Form pages dropped")
    w("")
    any_form = False
    for d in docs:
        if d.dropped_form_pages:
            any_form = True
            w(f"- **{d.plan.file.name}** — dropped pages {d.dropped_form_pages} "
              f"(form tail; policy body kept)")
    if not any_form:
        w("_None._")
    w("")

    w("## Pages skipped (blank/image, detected from content)")
    w("")
    any_skip = False
    for d in docs:
        if d.skipped_pages:
            any_skip = True
            w(f"- **{d.plan.file.name}** — pages {d.skipped_pages}")
    if not any_skip:
        w("_None._")
    w("")

    w("## Needs attention")
    w("")
    if not flagged:
        w("_None — every document produced chunks and matched its expected blank-page count._")
    else:
        for d in flagged:
            w(f"- **{d.plan.file.name}**")
            for issue in d.issues:
                w(f"  - {issue}")
    w("")
    w("---")
    w("")
    if prepare_only:
        w("_Prepare-only run: re-run with `--execute` to embed and upsert. "
          "The query side (`/ask`) is not yet pointed at this namespace._")
    else:
        w(f"_Ingested into namespace `{namespace}`. To retrieve, the query side must target "
          "this namespace (a separate change to `main.py`/`src/query.py`, not done here)._")
    w("")
    return "\n".join(L)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Knowledge-base ingestion (dry-run + real ingest).")
    ap.add_argument("--kb-dir", type=Path, default=DEFAULT_KB_DIR, help="Directory of source PDFs.")
    ap.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY, help="CORPUS_SUMMARY.md path.")
    ap.add_argument("--out", type=Path, default=None, help="Report output path (defaults per mode).")
    ap.add_argument("--namespace", default=DEFAULT_NAMESPACE, help="Pinecone namespace for the KB.")
    ap.add_argument("--no-pdf-check", action="store_true", help="Dry-run: do not open PDFs.")
    ap.add_argument("--prepare-only", action="store_true",
                    help="Phase 2 offline: read/chunk/plan, write result, NO embedding/upsert.")
    ap.add_argument("--execute", action="store_true",
                    help="Phase 2 live: embed + upsert to Pinecone.")
    ap.add_argument("--fresh", action="store_true",
                    help="With --execute: clear the namespace before upserting.")
    args = ap.parse_args(argv)

    try:
        if args.execute or args.prepare_only:
            out = args.out or DEFAULT_RESULT_OUT
            return run_ingest(
                args.kb_dir, args.summary, out, args.namespace,
                prepare_only=args.prepare_only and not args.execute,
                fresh=args.fresh,
            )
        out = args.out or DEFAULT_OUT
        run_dry_run(args.kb_dir, args.summary, out, do_pdf_check=not args.no_pdf_check)
    except (DryRunError, IngestError) as e:
        print(f"[FAILED] {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
