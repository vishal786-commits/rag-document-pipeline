# Knowledge-Base Ingestion — Result

> Generated: 2026-07-15T14:15:35 · Mode: **EXECUTE (embedded + upserted)**
> Namespace: **`knowledgebase`** · cleared first (--fresh) · Model: `text-embedding-3-small` (1536-d) · "Today": 2026-07-15
> `main.py` and the `/upload`, `/ask` paths were not modified. No secret values are printed.

## Summary

- **Documents ingested:** 40
- **Chunks produced:** 1452
- **Vectors upserted (confirmed):** 1452
- **Index stats:** 1452 vector(s) currently in namespace 'knowledgebase'
- **Pages skipped (blank/image):** 11
- **Form pages dropped:** 4
- **Documents with issues flagged:** 1

## Chunk metadata schema

Every vector carries: `text`, `source_file`, `doc_id`, `page` (1-based, original PDF page — enables citations), `chunk_index`, `audience`, `origin`, `status`, and `effective` / `expiry` / `version` when known. Vector id = `{doc_id}#{chunk_index}` (globally unique within the shared namespace).

## Per-document result

| # | Document | Audience | Status | Pages kept | Skip | Form-drop | Chunks |
|---|----------|----------|--------|-----------:|-----:|----------:|-------:|
| 1 | A Decent Home-Definition and guidance for implementation.pdf | reference | ⚪ unknown | 38 | — | — | 128 |
| 2 | Aids & Adaptations Policy.pdf | staff | 🟢 current | 5 | — | — | 18 |
| 3 | Anti-Social Behaviour Policy.pdf | staff | 🟢 current | 6 | — | — | 22 |
| 4 | Asbestos Management Policy.pdf | staff | 🔴 expired | 3 | 1 | — | 9 |
| 5 | Awaab’s Law_ Guidance for tenants in social housing - GOV.UK.pdf | tenant | ⚪ unknown | 25 | — | — | 59 |
| 6 | Compensation Policy.pdf | staff | 🟢 current | 4 | — | — | 14 |
| 7 | Complaints Policy.pdf | staff | 🟢 current | 6 | — | — | 22 |
| 8 | Customer Voice Policy.pdf | staff | 🟢 current | 4 | — | — | 13 |
| 9 | Damp, Mould & Condensation Policy.pdf | staff | 🟢 current | 4 | — | — | 15 |
| 10 | Data Protection, Privacy & Confidentiality Policy.pdf | staff | 🟢 current | 11 | — | — | 40 |
| 11 | Diversity & Inclusion Policy.pdf | staff | 🟢 current | 2 | — | — | 8 |
| 12 | Domestic Abuse Policy.pdf | staff | 🟢 current | 6 | — | — | 20 |
| 13 | Electrical Installations Safety Policy.pdf | staff | 🔴 expired | 3 | — | — | 9 |
| 14 | Empty Homes Policy.pdf | staff | 🟢 current | 3 | — | — | 10 |
| 15 | Environmental Sustainability Policy.pdf | staff | 🟢 current | 2 | — | — | 5 |
| 16 | Fire Safety Policy.pdf | staff | 🔴 expired | 4 | — | — | 12 |
| 17 | Fitness for Human Habitation Act 2018.pdf | reference | ⚪ unknown | 8 | 2 | — | 20 |
| 18 | Gas, Oil & Solid Fuel Policy.pdf | staff | 🟢 current | 4 | — | — | 11 |
| 19 | Group Health & Safety Policy.pdf | staff | 🔴 expired | 17 | — | — | 59 |
| 20 | Housing Health and Safety Rating System.pdf | reference | ⚪ unknown | 185 | — | — | 558 |
| 21 | Infestation and Pests Policy.pdf | staff | 🟢 current | 4 | — | — | 16 |
| 22 | Leasehold & Freehold Policy.pdf | staff | 🔴 expired | 6 | — | — | 21 |
| 23 | Lettings Policy.pdf | staff | 🟢 current | 4 | 1 | — | 14 |
| 24 | Lifts & Lifting Equipment Policy.pdf | staff | 🔴 expired | 4 | — | — | 12 |
| 25 | Neighbourhood Management Policy.pdf | staff | 🟢 current | 4 | — | — | 13 |
| 26 | Pets Policy.pdf | staff | 🟢 current | 5 | — | — | 21 |
| 27 | Recharges Policy.pdf | staff | 🟢 current | 4 | — | — | 13 |
| 28 | Repairs and Maintenance Policy.pdf | staff | 🟢 current | 4 | — | — | 12 |
| 29 | Right to Buy _ Right to Acquire Policy.pdf | staff | 🟢 current | 5 | — | — | 15 |
| 30 | Safeguarding Adults at Risk Policy.pdf | staff | 🟢 current | 6 | — | — | 21 |
| 31 | Safeguarding Children at Risk Policy.pdf | staff | 🟢 current | 6 | — | — | 22 |
| 32 | Section 20 Policy.pdf | staff | 🟢 current | 4 | — | 4 | 12 |
| 33 | Service Charge Policy.pdf | staff | 🔴 expired | 4 | — | — | 16 |
| 34 | Smoke & Carbon Monoxide Alarm Policy.pdf | staff | 🔴 expired | 3 | 1 | — | 8 |
| 35 | Temporary Re-Housing (Decant) Policy.pdf | staff | 🟢 current | 5 | — | — | 17 |
| 36 | Tenancy Policy.pdf | staff | 🟢 current | 5 | — | — | 17 |
| 37 | Unreasonable Behaviour Policy.pdf | staff | 🟢 current | 5 | — | — | 17 |
| 38 | Vulnerability Policy.pdf | staff | 🟢 current | 4 | 1 | — | 14 |
| 39 | awaabs-law-ai-slides.pdf | reference | ⚪ unknown | 98 | 5 | — | 102 |
| 40 | awaabs-law-policy-web-version-10.pdf | staff | ⚪ unknown | 7 | — | — | 17 |

## Form pages dropped

- **Section 20 Policy.pdf** — dropped pages [5, 6, 7, 8] (form tail; policy body kept)

## Pages skipped (blank/image, detected from content)

- **Asbestos Management Policy.pdf** — pages [4]
- **Fitness for Human Habitation Act 2018.pdf** — pages [2, 4]
- **Lettings Policy.pdf** — pages [5]
- **Smoke & Carbon Monoxide Alarm Policy.pdf** — pages [4]
- **Vulnerability Policy.pdf** — pages [5]
- **awaabs-law-ai-slides.pdf** — pages [20, 75, 83, 84, 85]

## Needs attention

- **awaabs-law-ai-slides.pdf**
  - blank-page count mismatch: detected 5 (pages [20, 75, 83, 84, 85]), summary flagged 0

---

_Ingested into namespace `knowledgebase`. To retrieve, the query side must target this namespace (a separate change to `main.py`/`src/query.py`, not done here)._
