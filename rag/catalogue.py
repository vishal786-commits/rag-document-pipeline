"""Parse docs/CORPUS_SUMMARY.md and reconcile it against the PDFs on disk.

The summary table is the metadata source of truth: audience, provenance,
version, and effective/expiry dates all come from it, not from the PDFs.

Design rule inherited from the previous ingester: no silent sentinels. Every
failure to parse or match is raised by name. A partial corpus is never ingested,
because a knowledge base that quietly lost a document is worse than one that
refuses to build.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


class CatalogueError(RuntimeError):
    """Raised for preflight failures that must stop the run loudly."""


# Doc-type -> audience rules. Anything not listed is UNRESOLVED, never defaulted.
STAFF_TYPES = {"policy", "policy + form", "landlord policy"}
REFERENCE_TYPES = {"legislation", "govt guidance", "govt operating guidance"}

# Tokens dropped when fuzzy-matching a summary row title to a filename.
MATCH_STOPWORDS = {"the", "and", "for", "of", "a", "an", "to", "in", "policy"}
MATCH_THRESHOLD = 0.45

DATE_FORMATS = ("%d/%m/%Y", "%d %b %Y", "%d %B %Y")


@dataclass
class SummaryRow:
    """One parsed row of the Step 1 catalogue table."""

    idx: str
    title: str
    pages: int | None
    origin: str
    doc_type: str
    dates_raw: str
    version: str
    flags: str


@dataclass
class DocMeta:
    """Resolved metadata for one document. These fields reach Pinecone."""

    doc_id: str
    file: Path
    title: str
    audience: str  # staff | tenant | reference
    origin: str  # ASTER | GOV | 3P | UNKNOWN
    status: str  # current | expired | unknown
    effective: date | None
    expiry: date | None
    version: str
    has_form: bool
    pages_expected: int | None


# ── Loading the summary table ───────────────────────────────────────────────
def load_summary_rows(summary_path: Path) -> list[SummaryRow]:
    if not summary_path.exists():
        raise CatalogueError(f"Summary file not found: {summary_path}")

    lines = summary_path.read_text(encoding="utf-8").splitlines()

    header_i = None
    for i, line in enumerate(lines):
        if line.lower().replace(" ", "").startswith("|#|file|pages|"):
            header_i = i
            break
    if header_i is None:
        raise CatalogueError(
            f"Could not locate the Step 1 catalogue table (header '| # | File | Pages | ...') "
            f"in {summary_path}. The summary format may have changed."
        )

    rows: list[SummaryRow] = []
    # Data rows start two lines after the header, skipping the |---|---| separator.
    for line in lines[header_i + 2 :]:
        if not line.strip().startswith("|"):
            break  # table ended
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 9:
            continue
        idx, title, pages_raw, origin, doc_type, _subject, dates_raw, ver, flags = cells[:9]
        rows.append(
            SummaryRow(
                idx=strip_md(idx),
                title=strip_md(title),
                pages=parse_int(pages_raw),
                origin=strip_md(origin).upper(),
                doc_type=strip_md(doc_type),
                dates_raw=strip_md(dates_raw),
                version=strip_md(ver),
                flags=strip_md(flags),
            )
        )

    if not rows:
        raise CatalogueError(f"Located the catalogue header but parsed zero rows in {summary_path}.")
    return rows


def strip_md(s: str) -> str:
    return s.replace("**", "").strip()


def parse_int(s: str) -> int | None:
    m = re.search(r"\d+", s)
    return int(m.group()) if m else None


def list_pdfs(kb_dir: Path) -> list[Path]:
    if not kb_dir.exists():
        raise CatalogueError(f"Knowledge-base directory not found: {kb_dir}")
    pdfs = sorted(p for p in kb_dir.glob("*.pdf") if p.is_file())
    if not pdfs:
        raise CatalogueError(f"No PDF files found in {kb_dir}")
    return pdfs


# ── Reconciling rows against files ──────────────────────────────────────────
def tokens(name: str) -> set[str]:
    name = re.sub(r"[^a-z0-9]+", " ", name.lower())
    return {t for t in name.split() if t and t not in MATCH_STOPWORDS}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def reconcile(rows: list[SummaryRow], files: list[Path]) -> list[tuple[SummaryRow, Path]]:
    """Greedy one-to-one title match, highest-scoring pairs first.

    Raises if any row or file is left over: an unmatched row means a document
    went missing, an unmatched file means one arrived uncatalogued. Either way
    the corpus and its metadata disagree and ingesting would bake that in.
    """
    scored: list[tuple[float, int, int]] = []
    row_tokens = [tokens(r.title) for r in rows]
    file_tokens = [tokens(f.stem) for f in files]
    for ri in range(len(rows)):
        for fi in range(len(files)):
            score = jaccard(row_tokens[ri], file_tokens[fi])
            if score >= MATCH_THRESHOLD:
                scored.append((score, ri, fi))
    scored.sort(key=lambda t: (-t[0], t[1], t[2]))

    used_rows: set[int] = set()
    used_files: set[int] = set()
    matched: list[tuple[SummaryRow, Path]] = []
    for _score, ri, fi in scored:
        if ri in used_rows or fi in used_files:
            continue
        used_rows.add(ri)
        used_files.add(fi)
        matched.append((rows[ri], files[fi]))

    unmatched_rows = [rows[i].title for i in range(len(rows)) if i not in used_rows]
    unmatched_files = [files[i].name for i in range(len(files)) if i not in used_files]
    if unmatched_rows or unmatched_files:
        raise CatalogueError(
            "Reconciliation is not clean; refusing to ingest a partial corpus.\n"
            f"  Catalogue rows with no PDF ({len(unmatched_rows)}): {unmatched_rows}\n"
            f"  PDFs with no catalogue row ({len(unmatched_files)}): {unmatched_files}\n"
            "Fix docs/CORPUS_SUMMARY.md or knowledge_base/ so the two agree."
        )

    matched.sort(key=lambda pair: row_sort_key(pair[0]))
    return matched


def row_sort_key(r: SummaryRow) -> tuple[int, str]:
    m = re.search(r"\d+", r.idx)
    return (int(m.group()) if m else 9999, r.title)


# ── Dates ───────────────────────────────────────────────────────────────────
def parse_date_token(tok: str) -> tuple[date | None, str | None]:
    """Return (date, issue). Exactly one of the two is always None."""
    tok = tok.replace("**", "").strip()
    if not tok:
        return None, "empty"
    if tok.upper().startswith("UNKNOWN"):
        return None, f"marked UNKNOWN in summary ({tok!r})"

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(tok, fmt).date(), None
        except ValueError:
            pass

    # Embedded dd/mm/yyyy, e.g. "Version 1.0 eff 02/03/2026".
    m = re.search(r"\d{1,2}/\d{1,2}/\d{4}", tok)
    if m:
        try:
            return datetime.strptime(m.group(), "%d/%m/%Y").date(), None
        except ValueError:
            pass

    # Embedded "d Mon yyyy", e.g. "Enacted 20 Dec 2018".
    m = re.search(r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}", tok)
    if m:
        for fmt in ("%d %b %Y", "%d %B %Y"):
            try:
                return datetime.strptime(m.group(), fmt).date(), None
            except ValueError:
                pass

    return None, f"could not parse a date from {tok!r}"


def parse_effective_expiry(dates_raw: str) -> tuple[date | None, date | None]:
    """Split the 'Effective -> Expiry' cell. Unparseable values stay None."""
    cell = dates_raw.replace("**", "").strip()
    if "→" in cell:  # the right-arrow used in the summary table
        left, right = cell.split("→", 1)
        effective, _ = parse_date_token(left)
        expiry, _ = parse_date_token(right)
        return effective, expiry
    effective, _ = parse_date_token(cell)
    return effective, None


def resolve_status(expiry: date | None, today: date) -> str:
    """expired / current / unknown. No expiry is reported, never assumed current."""
    if expiry is None:
        return "unknown"
    return "expired" if expiry < today else "current"


# ── Rules ───────────────────────────────────────────────────────────────────
def resolve_audience(row: SummaryRow) -> str:
    """staff | tenant | reference. Raises rather than defaulting an unknown type."""
    flags = row.flags.lower()
    if "tenant-facing" in flags or "tenant facing" in flags:
        return "tenant"
    doc_type = row.doc_type.lower().strip()
    if doc_type in STAFF_TYPES:
        return "staff"
    if doc_type in REFERENCE_TYPES:
        return "reference"
    raise CatalogueError(
        f"Row {row.idx} ({row.title!r}): doc type {row.doc_type!r} maps to no audience rule. "
        f"Add it to STAFF_TYPES or REFERENCE_TYPES in rag/catalogue.py, or fix the summary."
    )


def has_form(row: SummaryRow) -> bool:
    """True when the document ends in an internal workflow form to be dropped."""
    return bool(
        re.search(r"\bform\b", row.doc_type, re.IGNORECASE)
        or re.search(r"\bform\b", row.flags, re.IGNORECASE)
    )


def slug(stem: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return s or "doc"


def assign_doc_ids(files: list[Path]) -> dict[Path, str]:
    """Stable, unique, filename-derived ids. Collisions get a numeric suffix."""
    ids: dict[Path, str] = {}
    seen: dict[str, int] = {}
    for f in files:
        base = slug(f.stem)
        n = seen.get(base, 0)
        seen[base] = n + 1
        ids[f] = base if n == 0 else f"{base}-{n}"
    return ids


# ── The one entry point ─────────────────────────────────────────────────────
def load_catalogue(kb_dir: Path, summary_path: Path, today: date | None = None) -> list[DocMeta]:
    """Parse the summary, match it to the PDFs, and resolve every field.

    Raises CatalogueError if the summary and the directory disagree in any way.
    """
    today = today or date.today()
    rows = load_summary_rows(summary_path)
    files = list_pdfs(kb_dir)
    matched = reconcile(rows, files)
    doc_ids = assign_doc_ids([f for _row, f in matched])

    catalogue: list[DocMeta] = []
    for row, file in matched:
        effective, expiry = parse_effective_expiry(row.dates_raw)
        catalogue.append(
            DocMeta(
                doc_id=doc_ids[file],
                file=file,
                title=row.title,
                audience=resolve_audience(row),
                origin=row.origin,
                status=resolve_status(expiry, today),
                effective=effective,
                expiry=expiry,
                version=row.version,
                has_form=has_form(row),
                pages_expected=row.pages,
            )
        )
    return catalogue
