# Knowledge-Base Corpus Summary

> Analysis date: 2026-07-15 · Revised 2026-07-30 · Source: `knowledge_base/` (36 PDFs) · Method: automated text extraction (pypdf 6.8) of every file, then a read of each document's opening and closing sections plus a full-corpus keyword scan.
>
> **Revision 2026-07-30 — corpus reduced from 40 to 36 documents.** The four-document Awaab's Law / HHSRS cluster was removed: `Awaab's Law — Guidance for tenants in social housing (GOV.UK)`, `Housing Health and Safety Rating System`, `awaabs-law-ai-slides`, and `awaabs-law-policy-web-version-10`. These were the items on the Step 3 exclusion shortlist with the weakest provenance (third-party copyright, or origin UNKNOWN) plus the two largest files in the corpus. Rows are renumbered 1–36; page and provenance rollups are recomputed below. The directory was also renamed `kowledgebase/` → `knowledge_base/`.
> This is an honest content assessment. Characterisations are paraphrased from the extracted text — no document wording is reproduced. Where a fact could not be established from the text, it is marked **UNKNOWN** with a note on what would settle it.
> Provenance flags in Step 1 and the exclusion shortlist in Step 3 exist so you can decide which third-party items to keep or drop.

**Method caveats (so you can weigh the confidence):**
- Each PDF was fully text-extracted, but only the **head and tail** of each was read in full plus a corpus-wide keyword sweep. Provenance/branding/copyright signals are **high confidence** (they live in cover/footer text I read directly). Subject characterisations are **medium confidence** — interior pages were not read line-by-line.
- PDF `/Author` metadata is **document-control metadata, not subject authorship.** Roughly 26 files carry `/Author = "Grace Ogle"`; that is a template/document-controller fingerprint, not the policy's author. The governance blocks name role-based authors (e.g. "Policy Officer") instead. Do not read the metadata author as meaning one person wrote 26 policies.
- Filenames were **not** trusted for content. Two filenames are actively misleading and are corrected from content below.

---

## Step 1 — Per-document catalogue

**Publisher/origin key:** `ASTER` = Aster Group's own policy · `GOV` = UK government / Crown-copyright publication · `3P` = third-party non-government · `UNKNOWN` = origin not established from the text.

Aster Group is the organisation behind this corpus — a UK registered provider of social housing, operating as a group (Aster Communities, Synergy Housing, East Boro Housing Trust, Central & Cecil Housing Trust, Enham Trust, and others). The 34 ASTER items share a common template: an "overarching brand" preamble, numbered scope/statement/monitoring sections, a related-documents list, and a governance block (policy owner role, author role, approving body, effective/expiry dates, version, scheme-of-delegation reference).

| # | File | Pages | Origin | Doc type | Subject (paraphrased) | Effective → Expiry | Ver | Flags |
|---|------|------:|--------|----------|-----------------------|--------------------|-----|-------|
| 1 | A Decent Home — Definition and guidance for implementation | 38 | **GOV** | Govt guidance | The national Decent Homes standard and how it is delivered/monitored across social landlords | UNKNOWN (pub. **June 2006**) | — | Crown © 2006 (DCLG). Dated. Exclusion candidate |
| 2 | Aids & Adaptations Policy | 5 | ASTER | Policy | Adapting homes for accessible/independent living; who is eligible | 11/01/2024 → 11/01/2027 | v7.03 | Current |
| 3 | Anti-Social Behaviour Policy | 6 | ASTER | Policy | How ASB in communities is prevented and handled | 14/04/2024 → 14/04/2027 | V4.00 | **Approver field left as "Choose an Option"** |
| 4 | Asbestos Management Policy | 4 | ASTER | Policy | Managing asbestos risk in stock and premises | 01/09/2022 → **31/05/2026** | v2.2 | **EXPIRED**. 1 image/blank page |
| 5 | Compensation Policy | 4 | ASTER | Policy | Discretionary and statutory compensation to customers | 11/01/2024 → 11/04/2027 | 7.02 | Current |
| 6 | Complaints Policy | 6 | ASTER | Policy | Complaint handling approach and routes | 01/05/2024 → 30/04/2027 | 8.04 | Current. Contains a contact phone/address |
| 7 | Customer Voice Policy | 4 | ASTER | Policy | Customer engagement / feedback approach | 11/01/2024 → 11/01/2027 | 2.01 | Current |
| 8 | Damp, Mould & Condensation Policy | 4 | ASTER | Policy | Landlord approach to damp/mould/condensation and duties | 05/10/2023 → 05/10/2026 | V1.03 | Current. Topic overlaps items 1, 16 |
| 9 | Data Protection, Privacy & Confidentiality Policy | 11 | ASTER | Policy | UK GDPR / DPA 2018 compliance as controller/processor | UNKNOWN → 25/02/2027 | v8.2 | Effective date not found in extract |
| 10 | Diversity & Inclusion Policy | 2 | ASTER | Policy | Equality/inclusion commitments across the group | 01/11/2024 → 31/10/2027 | 7.01 | Current |
| 11 | Domestic Abuse Policy | 6 | ASTER | Policy | Support and case handling for domestic abuse | 18/07/2024 → 18/07/2027 | v2.01 | Current |
| 12 | Electrical Installations Safety Policy | 3 | ASTER | Policy | Electrical safety inspection/testing regime | 01/09/2022 → **31/05/2026** | v2.2 | **EXPIRED** |
| 13 | Empty Homes Policy | 3 | ASTER | Policy | Managing void properties between tenancies | 21/10/2025 → 20/10/2028 | V3.00 | Current |
| 14 | Environmental Sustainability Policy | 2 | ASTER | Policy | Environmental management / pollution prevention | 16/07/2025 → 16/07/2028 | 7.00 | Current |
| 15 | Fire Safety Policy | 4 | ASTER | Policy | Fire risk assessment and prevention regime | 01/09/2022 → **31/05/2026** | V3.2 | **EXPIRED**. Notes a deferred Building Safety Act 2022 addendum |
| 16 | Homes (Fitness for Human Habitation) Act 2018 | 10 | **GOV** | Legislation | Act amending the Landlord & Tenant Act 1985 on habitation fitness | Enacted **20 Dec 2018** | c.34 | Crown © 2018 (TSO). Primary law. 2 image/blank pages |
| 17 | Gas, Oil & Solid Fuel Policy | 4 | ASTER | Policy | Fuel-appliance safety regime | 01/10/2023 → 30/09/2026 | V6.0 | Current |
| 18 | Group Health & Safety Policy | 17 | ASTER | Policy | Group-wide H&S duties under HSWA 1974 | 10/06/2025 → **09/06/2026** | v4.2 | **EXPIRED**. Board-approved |
| 19 | Infestation and Pests Policy | 4 | ASTER | Policy | Pest/infestation responsibilities and eradication | 13/03/2026 → 12/03/2029 | V2.00 | Current (newest effective date) |
| 20 | Leasehold & Freehold Policy | 6 | ASTER | Policy | Duties to leaseholders under lease terms | 02/05/2023 → **02/05/2026** | V2.01 | **EXPIRED** |
| 21 | Lettings Policy | 5 | ASTER | Policy | How homes are allocated/let | 19/08/2025 → 19/08/2028 | V4.02 | Current. 1 image/blank page |
| 22 | Lifts & Lifting Equipment Policy | 4 | ASTER | Policy | Lift servicing/examination regime (LOLER) | 01/09/2022 → **31/05/2026** | v2.3 | **EXPIRED** |
| 23 | Neighbourhood Management Policy | 4 | ASTER | Policy | Managing communal areas/estates | 22/07/2025 → 22/07/2028 | 5.0 | Current |
| 24 | Pets Policy | 5 | ASTER | Policy | Responsible pet ownership rules | 24/10/2024 → 24/10/2027 | V2.03 | Current |
| 25 | Recharges Policy | 4 | ASTER | Policy | Recovering repair costs from customers | 01/04/2024 → 31/03/2027 | v2.00 | Current |
| 26 | Repairs and Maintenance Policy | 4 | ASTER | Policy | Responsive repairs service scope | 05/10/2023 → 05/10/2026 | 4.05 | Current. **Approver field left as "Choose an Option"** |
| 27 | Right to Buy / Right to Acquire Policy | 5 | ASTER | Policy | RTB/RTA/RTSO purchase rights and eligibility | 06/04/2024 → 23/01/2027 | V6.1 | Current |
| 28 | Safeguarding Adults at Risk Policy | 6 | ASTER | Policy | Adult safeguarding duties (Care Act 2014) | 16/07/2025 → 16/07/2028 | V7.01 | Current. Contains named safeguarding-lead contact details |
| 29 | Safeguarding Children at Risk Policy | 6 | ASTER | Policy | Child safeguarding duties | 24/07/2025 → 24/07/2028 | V2.03 | Current |
| 30 | Section 20 Policy | 8 | ASTER | Policy + form | Leaseholder consultation on major works/charges | 19/03/2025 → 19/03/2028 | v5.02 | Current. Tail is an internal workflow/approval form |
| 31 | Service Charge Policy | 4 | ASTER | Policy | How service charges are set and recovered | 06/07/2023 → **05/07/2026** | 3.0 | **EXPIRED** |
| 32 | Smoke & Carbon Monoxide Alarm Policy | 4 | ASTER | Policy | Alarm installation/testing regime | 01/09/2022 → **31/05/2026** | V1.2 | **EXPIRED**. 1 image/blank page |
| 33 | Temporary Re-Housing (Decant) Policy | 5 | ASTER | Policy | Temporary rehousing during works/emergencies | 29/01/2025 → 29/01/2028 | V1.02 | Current |
| 34 | Tenancy Policy | 5 | ASTER | Policy | Tenancy types and management | 23/04/2025 → 22/04/2028 | V4.01 | Current |
| 35 | Unreasonable Behaviour Policy | 5 | ASTER | Policy | Managing unreasonable customer conduct toward staff | 17/12/2024 → 17/12/2027 | 1.03 | Current |
| 36 | Vulnerability Policy | 5 | ASTER | Policy | Adjustments for customers who disclose vulnerability | 19/09/2025 → 19/08/2028 | V1.00 | Current. 1 image/blank page |

### Removed 2026-07-30
Four documents were dropped from the corpus. They were the whole of the third-party/unknown-provenance set plus the two largest files:

| Was # | File | Pages | Origin | Reason |
|------:|------|------:|--------|--------|
| 5 | Awaab's Law — Guidance for tenants in social housing (GOV.UK) | 25 | GOV | Tenant-facing explainer, not a landlord procedure — its voice and answers differ from every other document here |
| 20 | Housing Health and Safety Rating System | 185 | GOV | Crown © 2006 (ODPM). ~20 years old and 34% of all corpus pages; its bulk skewed the index |
| 39 | awaabs-law-ai-slides | 103 | 3P | Third-party copyright (Ward Hadaway LLP / Housing Ombudsman), no redistribution licence. Slide-sparse (~310 chars/page), weak for retrieval |
| 40 | awaabs-law-policy-web-version-10 | 7 | UNKNOWN | No Aster branding, no governance block, no author metadata — ownership never established |

---

## Step 2 — Thematic map & overlap

The 34 Aster policies cluster into six operational domains. Two non-Aster items remain (both **GOV**, Step 1 rows 1 and 16); they sit around the **housing hazards** topic, which is where what retrieval ambiguity remains is concentrated.

**A. Building safety & statutory compliance (9):** Asbestos · Electrical Installations · Fire Safety · Gas/Oil/Solid Fuel · Lifts & Lifting Equipment · Smoke & CO Alarms · Group Health & Safety · Damp/Mould/Condensation · (plus water safety, referenced but **not present**).
**B. Repairs, property & assets (6):** Repairs & Maintenance · Aids & Adaptations · Empty Homes · Recharges · Infestation & Pests · Environmental Sustainability.
**C. Tenancy & housing management (6):** Tenancy · Lettings · Temporary Re-Housing (Decant) · Neighbourhood Management · Pets · Right to Buy/Acquire.
**D. Leasehold, charges & redress (4):** Leasehold & Freehold · Section 20 · Service Charge · Compensation.
**E. Customer, community & safeguarding (9):** Complaints · Customer Voice · Unreasonable Behaviour · Diversity & Inclusion · Domestic Abuse · Anti-Social Behaviour · Safeguarding Adults · Safeguarding Children · Vulnerability.
**F. Information governance (1):** Data Protection, Privacy & Confidentiality.

**The hazards overlap cluster (3 documents, was 7 before the 2026-07-30 reduction):**
| Document | Provenance | Role in the topic |
|----------|-----------|-------------------|
| Damp, Mould & Condensation Policy | ASTER | The landlord's operational policy |
| Homes (Fitness for Human Habitation) Act 2018 | GOV | Underpinning legislation |
| A Decent Home (2006) | GOV | The related Decent Homes standard |

Removing the four Awaab's Law / HHSRS documents substantially defused this hot-spot. It did not eliminate it: a question like "what are the timescales for fixing damp and mould?" can still draw on a current landlord policy, 2018 primary legislation, and a 2006 government standard at once, and these may **disagree in detail or date**. Retrieval tuning and answer judging should still treat this cluster as the most likely source of a confidently wrong or internally contradictory answer.

Note also what the reduction *removed* from the corpus: Awaab's Law itself is no longer represented by any document. Questions about Awaab's Law timescales are now out of scope, and the system should decline them rather than answering from the Damp & Mould Policy by inference.

---

## Step 3 — Corpus rollup

### Composition (exact)
- **36 PDFs · 222 pages · 6.11 MB on disk.** Extracted-character count is **not restated** here — the 2026-07-15 figure (~958,000) covered all 40 documents and the per-file breakdown needed to subtract exactly was never recorded. The ingest run recomputes it; see `docs/INGEST_RESULT.md`.
- **Text extraction is healthy overall:** ~99% of pages yielded text. Only ~6 pages across 5 files came back empty (image-only covers/dividers): Asbestos, Lettings, Smoke & CO, Vulnerability (1 each) and Fitness for Human Habitation Act (2).
- **Size skew is much reduced.** Removing HHSRS (185 pages) and the slide deck (103 pages) took out the two dominant files. The largest remaining is **A Decent Home, 38 pages — 17% of corpus pages**, down from HHSRS's 34%. The next largest are Group Health & Safety (17), Data Protection (11), and the Fitness for Human Habitation Act (10). The 34 Aster policies remain short (median ~5 pages), so the corpus is now fairly evenly distributed.

### Provenance breakdown
| Origin | Count | Documents |
|--------|------:|-----------|
| **ASTER** (own policy) | 34 | Items 2–15, 17–36 |
| **GOV** (Crown copyright) | 2 | A Decent Home (2006) · Homes (Fitness for Human Habitation) Act 2018 |
| **3P** (third-party non-gov) | 0 | — |
| **UNKNOWN** | 0 | — |

### Exclusion shortlist — resolved 2026-07-30
The original shortlist listed 6 non-Aster items. Four were removed (see "Removed 2026-07-30" in Step 1). **Two GOV items were retained**, and the reasoning for keeping them stands:

1. **A Decent Home (2006, DCLG)** — Crown copyright. **~20 years old**; the standard has evolved since. Retained as historical reference for the Decent Homes definition, but **verify it reflects current policy before relying on it.** It is now the single largest file in the corpus.
2. **Homes (Fitness for Human Habitation) Act 2018** — primary legislation (Crown copyright, freely reproducible). Authoritative and stable; low risk to keep.

Note that the corpus is therefore **34 Aster policies plus 2 Crown-copyright government documents**, not purely Aster-authored material. Any provenance claim made to end users should say so.

### Data-quality issues found (Aster set)
- **8 of 34 Aster policies are past their stated expiry date as of 2026-07-30:** Asbestos, Electrical, Fire Safety, Lifts, Smoke & CO (all 31/05/2026), Group Health & Safety (09/06/2026), Leasehold & Freehold (02/05/2026), and Service Charge (05/07/2026). Notably, five of the eight are **building-safety** policies — the highest-stakes category to be serving from an out-of-date document. A RAG answer will happily cite an expired policy with no signal that it has lapsed. *Expiry is computed against the run date at ingest time, so this count grows on its own; it is not a fixed property of the corpus.*
- **2 policies shipped with an unfilled template field:** Anti-Social Behaviour and Repairs & Maintenance both show `Approved by: Choose an Option` — the dropdown placeholder was never completed.
- **Template artifacts throughout:** many files retain `Click or tap to enter a date` placeholders and repeat the long group-entity boilerplate on both first and last pages. This boilerplate is near-identical across ~20 files and will produce **many near-duplicate chunks** that add retrieval noise and can crowd out substantive text.
- **Contact details / named individuals** appear in a few files (Complaints: phone + postal address; Safeguarding Adults: named lead with email/phone). Worth knowing before any answer is surfaced publicly.

### Implications for the RAG pipeline
- **Topic collision on hazards (Step 2)** is reduced from 7 documents to 3, but not gone. A current landlord policy, 2018 legislation, and a 2006 government standard can still be retrieved together for the same question and disagree on detail or date.
- **A Decent Home (2006)** can surface ~20-year-old guidance against current Aster policy. It is now the largest file in the corpus, so freshness/authority signalling matters for it specifically.
- **Awaab's Law is no longer in the corpus.** The system should decline Awaab's Law questions rather than inferring an answer from the Damp & Mould Policy. This is a coverage gap to state plainly to users, not one to paper over.
- **Boilerplate duplication** inflates chunk counts and BM25 term statistics with legal-entity lists that carry no answer value. This is now the single largest remaining source of retrieval noise and is handled at ingest time.
- **Expired policies** are the highest-stakes data-quality issue left. Five of the eight are building-safety documents.

### What I would need to finish the picture (open questions)
1. **Are the 8 expired policies genuinely lapsed, or is the expiry date a review date that has slipped?** This changes whether the right behaviour is to warn or to refuse. Current design warns.
2. **Should the Awaab's Law coverage gap be filled?** The four removed documents were the corpus's only Awaab's Law material. If Aster has its own Awaab's Law policy, it belongs here.
3. **Is A Decent Home (2006) intentionally retained as historical reference, or should it be refreshed** to the current-standard equivalent?
4. **Interior-page verification** — characterisations here rest on each document's opening/closing plus a keyword sweep; a full page-by-page read would firm up the medium-confidence subject lines if that precision is needed.

*End of corpus summary. Step 3 (this rollup) is reproduced to the terminal.*
