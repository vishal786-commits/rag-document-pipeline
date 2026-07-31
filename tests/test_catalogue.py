"""Catalogue parsing is pure and runs with no PDFs and no network."""

from datetime import date
from pathlib import Path

import pytest

from rag.catalogue import (
    CatalogueError,
    SummaryRow,
    assign_doc_ids,
    has_form,
    jaccard,
    load_summary_rows,
    parse_date_token,
    parse_effective_expiry,
    reconcile,
    resolve_audience,
    resolve_status,
    slug,
    tokens,
)

SUMMARY = Path(__file__).resolve().parent.parent / "docs" / "CORPUS_SUMMARY.md"


def row(**kw) -> SummaryRow:
    base = dict(
        idx="1",
        title="Fire Safety Policy",
        pages=4,
        origin="ASTER",
        doc_type="Policy",
        dates_raw="01/09/2022 → 31/05/2026",
        version="V3.2",
        flags="EXPIRED",
    )
    base.update(kw)
    return SummaryRow(**base)


# ── Dates ───────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "token,expected",
    [
        ("01/09/2022", date(2022, 9, 1)),  # dd/mm/yyyy, not mm/dd
        ("20 Dec 2018", date(2018, 12, 20)),
        ("4 December 2025", date(2025, 12, 4)),
        ("Version 1.0 eff 02/03/2026", date(2026, 3, 2)),  # embedded
        ("Enacted 20 Dec 2018", date(2018, 12, 20)),  # embedded
    ],
)
def test_parse_date_token_accepts_the_formats_the_summary_uses(token, expected):
    parsed, issue = parse_date_token(token)
    assert parsed == expected
    assert issue is None


@pytest.mark.parametrize("token", ["", "UNKNOWN", "UNKNOWN (pub. June 2006)", "sometime soon"])
def test_parse_date_token_reports_an_issue_rather_than_guessing(token):
    parsed, issue = parse_date_token(token)
    assert parsed is None
    assert issue, "an unparseable date must produce a stated reason, not a silent None"


def test_parse_effective_expiry_splits_on_the_unicode_arrow():
    """The summary uses U+2192. Reading the file as cp1252 would mangle this and
    silently turn every document's status into 'unknown'."""
    effective, expiry = parse_effective_expiry("01/09/2022 → 31/05/2026")
    assert effective == date(2022, 9, 1)
    assert expiry == date(2026, 5, 31)


def test_parse_effective_expiry_without_an_arrow_has_no_expiry():
    effective, expiry = parse_effective_expiry("Enacted 20 Dec 2018")
    assert effective == date(2018, 12, 20)
    assert expiry is None


def test_resolve_status():
    today = date(2026, 7, 30)
    assert resolve_status(date(2026, 5, 31), today) == "expired"
    assert resolve_status(date(2027, 1, 1), today) == "current"
    assert resolve_status(None, today) == "unknown", "no expiry is never assumed current"


# ── Audience ────────────────────────────────────────────────────────────────
def test_tenant_flag_beats_doc_type():
    assert resolve_audience(row(doc_type="Govt guidance", flags="Tenant-facing")) == "tenant"


def test_policy_types_map_to_staff():
    assert resolve_audience(row(doc_type="Policy")) == "staff"
    assert resolve_audience(row(doc_type="Policy + form")) == "staff"


def test_legislation_maps_to_reference():
    assert resolve_audience(row(doc_type="Legislation", flags="")) == "reference"


def test_unknown_doc_type_raises_rather_than_defaulting():
    with pytest.raises(CatalogueError, match="maps to no audience rule"):
        resolve_audience(row(doc_type="Interpretive Dance", flags=""))


# ── Forms ───────────────────────────────────────────────────────────────────
def test_has_form_reads_both_doc_type_and_flags():
    assert has_form(row(doc_type="Policy + form"))
    assert has_form(row(doc_type="Policy", flags="Tail is an internal workflow form"))
    assert not has_form(row(doc_type="Policy", flags="Current"))


# ── Matching ────────────────────────────────────────────────────────────────
def test_tokens_drops_stopwords():
    assert tokens("The Fire Safety Policy") == {"fire", "safety"}


def test_jaccard_is_zero_for_an_empty_side():
    assert jaccard(set(), {"a"}) == 0.0


def test_reconcile_raises_when_a_catalogue_row_has_no_pdf():
    rows = [row(title="Fire Safety Policy"), row(idx="2", title="Pets Policy")]
    files = [Path("Fire Safety Policy.pdf")]

    with pytest.raises(CatalogueError, match="refusing to ingest a partial corpus"):
        reconcile(rows, files)


def test_reconcile_raises_when_a_pdf_has_no_catalogue_row():
    rows = [row(title="Fire Safety Policy")]
    files = [Path("Fire Safety Policy.pdf"), Path("Surprise Policy.pdf")]

    with pytest.raises(CatalogueError, match="PDFs with no catalogue row"):
        reconcile(rows, files)


def test_reconcile_matches_despite_filename_punctuation_differences():
    rows = [row(title="Right to Buy / Right to Acquire Policy")]
    files = [Path("Right to Buy _ Right to Acquire Policy.pdf")]

    matched = reconcile(rows, files)
    assert len(matched) == 1


# ── Ids ─────────────────────────────────────────────────────────────────────
def test_slug_is_ascii_and_hyphenated():
    assert slug("Damp, Mould & Condensation Policy") == "damp-mould-condensation-policy"


def test_assign_doc_ids_disambiguates_collisions():
    ids = assign_doc_ids([Path("a/Pets Policy.pdf"), Path("b/Pets  Policy.pdf")])
    assert sorted(ids.values()) == ["pets-policy", "pets-policy-1"]


# ── The real summary file ───────────────────────────────────────────────────
def test_the_real_summary_parses_and_has_one_row_per_pdf():
    rows = load_summary_rows(SUMMARY)
    assert len(rows) == 36
    assert all(r.title for r in rows)
    assert {r.origin for r in rows} == {"ASTER", "GOV"}


def test_the_real_summary_reconciles_cleanly_against_the_knowledge_base():
    """The guard that matters most: catalogue and directory must agree."""
    from rag.catalogue import list_pdfs
    from rag.config import KB_DIR

    matched = reconcile(load_summary_rows(SUMMARY), list_pdfs(KB_DIR))
    assert len(matched) == 36
