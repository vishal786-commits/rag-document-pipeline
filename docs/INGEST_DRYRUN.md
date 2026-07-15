# Knowledge-Base Ingestion — Dry-Run Report

> Generated: 2026-07-15T14:00:33 · "Today" for expiry checks: **2026-07-15**
> **Dry run — report only.** No embeddings, no Pinecone writes, no corpus writes. `main.py` and the `/upload`, `/ask` paths were not touched. No secrets are read or printed.

- **Source of truth:** `docs\CORPUS_SUMMARY.md` (Step 1 catalogue)
- **PDF directory:** `kowledgebase`
- **PDF parse check:** enabled (each PDF opened)

## Rules applied

> Reconstructed from the corpus summary (original spec was truncated). Review and correct in `ingest_kb.py`.

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


## Summary

- **Documents planned for ingestion:** 40 (matched to 40 of 40 PDFs on disk)
- **Audience mix:** 4 reference, 35 staff, 1 tenant
- **Status:** 8 expired · 26 current · 6 unknown
- **Forms dropped:** 1 document(s)
- **Pages skipped (image/blank):** 6 page(s) across 5 document(s)
- **Exclusion candidates flagged:** 5

- **⚠ Needs attention:** 7 item(s) — see [Needs attention](#needs-attention).

## Per-document plan

| # | Document | Audience | Effective | Expiry | Status | Forms | Skip pg | Origin | Ver |
|---|----------|----------|-----------|--------|--------|-------|--------:|--------|-----|
| 1 | A Decent Home-Definition and guidance for implementation.pdf | reference | — ⚠ | — ⚠ | ⚪ unknown | — | — | GOV | — |
| 2 | Aids & Adaptations Policy.pdf | staff | 2024-01-11 | 2027-01-11 | 🟢 current | — | — | ASTER | v7.03 |
| 3 | Anti-Social Behaviour Policy.pdf | staff | 2024-04-14 | 2027-04-14 | 🟢 current | — | — | ASTER | V4.00 |
| 4 | Asbestos Management Policy.pdf | staff | 2022-09-01 | 2026-05-31 | 🔴 expired | — | 1 | ASTER | v2.2 |
| 5 | Awaab’s Law_ Guidance for tenants in social housing - GOV.UK.pdf | tenant | 2025-12-04 | — ⚠ | ⚪ unknown | — | — | GOV | — |
| 6 | Compensation Policy.pdf | staff | 2024-01-11 | 2027-04-11 | 🟢 current | — | — | ASTER | 7.02 |
| 7 | Complaints Policy.pdf | staff | 2024-05-01 | 2027-04-30 | 🟢 current | — | — | ASTER | 8.04 |
| 8 | Customer Voice Policy.pdf | staff | 2024-01-11 | 2027-01-11 | 🟢 current | — | — | ASTER | 2.01 |
| 9 | Damp, Mould & Condensation Policy.pdf | staff | 2023-10-05 | 2026-10-05 | 🟢 current | — | — | ASTER | V1.03 |
| 10 | Data Protection, Privacy & Confidentiality Policy.pdf | staff | — ⚠ | 2027-02-25 | 🟢 current | — | — | ASTER | v8.2 |
| 11 | Diversity & Inclusion Policy.pdf | staff | 2024-11-01 | 2027-10-31 | 🟢 current | — | — | ASTER | 7.01 |
| 12 | Domestic Abuse Policy.pdf | staff | 2024-07-18 | 2027-07-18 | 🟢 current | — | — | ASTER | v2.01 |
| 13 | Electrical Installations Safety Policy.pdf | staff | 2022-09-01 | 2026-05-31 | 🔴 expired | — | — | ASTER | v2.2 |
| 14 | Empty Homes Policy.pdf | staff | 2025-10-21 | 2028-10-20 | 🟢 current | — | — | ASTER | V3.00 |
| 15 | Environmental Sustainability Policy.pdf | staff | 2025-07-16 | 2028-07-16 | 🟢 current | — | — | ASTER | 7.00 |
| 16 | Fire Safety Policy.pdf | staff | 2022-09-01 | 2026-05-31 | 🔴 expired | — | — | ASTER | V3.2 |
| 17 | Fitness for Human Habitation Act 2018.pdf | reference | 2018-12-20 | — ⚠ | ⚪ unknown | — | 2 | GOV | c.34 |
| 18 | Gas, Oil & Solid Fuel Policy.pdf | staff | 2023-10-01 | 2026-09-30 | 🟢 current | — | — | ASTER | V6.0 |
| 19 | Group Health & Safety Policy.pdf | staff | 2025-06-10 | 2026-06-09 | 🔴 expired | — | — | ASTER | v4.2 |
| 20 | Housing Health and Safety Rating System.pdf | reference | — ⚠ | — ⚠ | ⚪ unknown | — | — | GOV | v2 |
| 21 | Infestation and Pests Policy.pdf | staff | 2026-03-13 | 2029-03-12 | 🟢 current | — | — | ASTER | V2.00 |
| 22 | Leasehold & Freehold Policy.pdf | staff | 2023-05-02 | 2026-05-02 | 🔴 expired | — | — | ASTER | V2.01 |
| 23 | Lettings Policy.pdf | staff | 2025-08-19 | 2028-08-19 | 🟢 current | — | 1 | ASTER | V4.02 |
| 24 | Lifts & Lifting Equipment Policy.pdf | staff | 2022-09-01 | 2026-05-31 | 🔴 expired | — | — | ASTER | v2.3 |
| 25 | Neighbourhood Management Policy.pdf | staff | 2025-07-22 | 2028-07-22 | 🟢 current | — | — | ASTER | 5.0 |
| 26 | Pets Policy.pdf | staff | 2024-10-24 | 2027-10-24 | 🟢 current | — | — | ASTER | V2.03 |
| 27 | Recharges Policy.pdf | staff | 2024-04-01 | 2027-03-31 | 🟢 current | — | — | ASTER | v2.00 |
| 28 | Repairs and Maintenance Policy.pdf | staff | 2023-10-05 | 2026-10-05 | 🟢 current | — | — | ASTER | 4.05 |
| 29 | Right to Buy _ Right to Acquire Policy.pdf | staff | 2024-04-06 | 2027-01-23 | 🟢 current | — | — | ASTER | V6.1 |
| 30 | Safeguarding Adults at Risk Policy.pdf | staff | 2025-07-16 | 2028-07-16 | 🟢 current | — | — | ASTER | V7.01 |
| 31 | Safeguarding Children at Risk Policy.pdf | staff | 2025-07-24 | 2028-07-24 | 🟢 current | — | — | ASTER | V2.03 |
| 32 | Section 20 Policy.pdf | staff | 2025-03-19 | 2028-03-19 | 🟢 current | drop | — | ASTER | v5.02 |
| 33 | Service Charge Policy.pdf | staff | 2023-07-06 | 2026-07-05 | 🔴 expired | — | — | ASTER | 3.0 |
| 34 | Smoke & Carbon Monoxide Alarm Policy.pdf | staff | 2022-09-01 | 2026-05-31 | 🔴 expired | — | 1 | ASTER | V1.2 |
| 35 | Temporary Re-Housing (Decant) Policy.pdf | staff | 2025-01-29 | 2028-01-29 | 🟢 current | — | — | ASTER | V1.02 |
| 36 | Tenancy Policy.pdf | staff | 2025-04-23 | 2028-04-22 | 🟢 current | — | — | ASTER | V4.01 |
| 37 | Unreasonable Behaviour Policy.pdf | staff | 2024-12-17 | 2027-12-17 | 🟢 current | — | — | ASTER | 1.03 |
| 38 | Vulnerability Policy.pdf | staff | 2025-09-19 | 2028-08-19 | 🟢 current | — | 1 | ASTER | V1.00 |
| 39 | awaabs-law-ai-slides.pdf | reference | — ⚠ | — ⚠ | ⚪ unknown | — | — | 3P | — |
| 40 | awaabs-law-policy-web-version-10.pdf | staff | 2026-03-02 | — ⚠ | ⚪ unknown | — | — | UNKNOWN | 1.0 |

<a id="needs-attention"></a>
## Needs attention

### Date parse issues (7)

- A Decent Home-Definition and guidance for implementation.pdf — raw `UNKNOWN (pub. June 2006)` — effective: marked UNKNOWN in summary ('UNKNOWN (pub. June 2006)'); expiry: no expiry given in summary
- Awaab’s Law_ Guidance for tenants in social housing - GOV.UK.pdf — raw `Updated 4 Dec 2025` — expiry: no expiry given in summary
- Data Protection, Privacy & Confidentiality Policy.pdf — raw `UNKNOWN → 25/02/2027` — effective: marked UNKNOWN in summary ('UNKNOWN')
- Fitness for Human Habitation Act 2018.pdf — raw `Enacted 20 Dec 2018` — expiry: no expiry given in summary
- Housing Health and Safety Rating System.pdf — raw `UNKNOWN (pub. Feb 2006)` — effective: marked UNKNOWN in summary ('UNKNOWN (pub. Feb 2006)'); expiry: no expiry given in summary
- awaabs-law-ai-slides.pdf — raw `UNKNOWN (dated 30 Sep 2025)` — effective: marked UNKNOWN in summary ('UNKNOWN (dated 30 Sep 2025)'); expiry: no expiry given in summary
- awaabs-law-policy-web-version-10.pdf — raw `Version 1.0 eff 02/03/2026` — expiry: no expiry given in summary

## Forms dropped

- **Section 20 Policy.pdf** — Current. Tail is an internal workflow/approval form

## Pages skipped (image/blank)

- **Asbestos Management Policy.pdf** — 1 page(s)
- **Fitness for Human Habitation Act 2018.pdf** — 2 page(s)
- **Lettings Policy.pdf** — 1 page(s)
- **Smoke & Carbon Monoxide Alarm Policy.pdf** — 1 page(s)
- **Vulnerability Policy.pdf** — 1 page(s)

_Total: 6 page(s). Counts come from the summary's `Flags` (`N image/blank page`); slide-sparse pages not tagged that way are not counted here._

## Expired policies (would ingest with an expired-status flag)

- **Leasehold & Freehold Policy.pdf** — expired 2026-05-02 (V2.01)
- **Asbestos Management Policy.pdf** — expired 2026-05-31 (v2.2)
- **Electrical Installations Safety Policy.pdf** — expired 2026-05-31 (v2.2)
- **Fire Safety Policy.pdf** — expired 2026-05-31 (V3.2)
- **Lifts & Lifting Equipment Policy.pdf** — expired 2026-05-31 (v2.3)
- **Smoke & Carbon Monoxide Alarm Policy.pdf** — expired 2026-05-31 (V1.2)
- **Group Health & Safety Policy.pdf** — expired 2026-06-09 (v4.2)
- **Service Charge Policy.pdf** — expired 2026-07-05 (3.0)

## Exclusion candidates (human decision — flagged, not acted on)

- **A Decent Home-Definition and guidance for implementation.pdf** (GOV) — Crown © 2006 (DCLG). Dated. Exclusion candidate
- **Awaab’s Law_ Guidance for tenants in social housing - GOV.UK.pdf** (GOV) — Crown © 2025, Open Government Licence v3.0. Tenant-facing (not a landlord procedure). Exclusion candidate
- **Fitness for Human Habitation Act 2018.pdf** (GOV) — Crown © 2018 (TSO). Primary law. 2 image/blank pages. Exclusion candidate
- **Housing Health and Safety Rating System.pdf** (GOV) — Crown © 2006 (ODPM). Largest file — 34% of all corpus pages. Exclusion candidate
- **awaabs-law-ai-slides.pdf** (3P) — Filename misleading — content is a law-firm briefing (Ward Hadaway LLP) + Housing Ombudsman, not "AI". Third-party copyright. Sparse text/slide. Exclusion candidate

---

_Next phase (not in this run): batch-embed and upsert the planned documents, carrying audience / effective / expiry / status as chunk metadata, dropping the flagged form sections and skipped pages. This report is the gate for that step._
