# Knowledge-Base Corpus Summary

> Analysis date: 2026-07-15 · Source: `kowledgebase/` (40 PDFs) · Method: automated text extraction (pypdf 6.8) of every file, then a read of each document's opening and closing sections plus a full-corpus keyword scan.
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
| 5 | Awaab's Law — Guidance for tenants in social housing (GOV.UK) | 25 | **GOV** | Govt guidance | Tenant-facing explainer of Awaab's Law rights and landlord duties | Updated **4 Dec 2025** | — | Crown © 2025, **Open Government Licence v3.0**. Tenant-facing (not a landlord procedure). Exclusion candidate |
| 6 | Compensation Policy | 4 | ASTER | Policy | Discretionary and statutory compensation to customers | 11/01/2024 → 11/04/2027 | 7.02 | Current |
| 7 | Complaints Policy | 6 | ASTER | Policy | Complaint handling approach and routes | 01/05/2024 → 30/04/2027 | 8.04 | Current. Contains a contact phone/address |
| 8 | Customer Voice Policy | 4 | ASTER | Policy | Customer engagement / feedback approach | 11/01/2024 → 11/01/2027 | 2.01 | Current |
| 9 | Damp, Mould & Condensation Policy | 4 | ASTER | Policy | Landlord approach to damp/mould/condensation and duties | 05/10/2023 → 05/10/2026 | V1.03 | Current. Topic overlaps items 1,5,19,39,40 |
| 10 | Data Protection, Privacy & Confidentiality Policy | 11 | ASTER | Policy | UK GDPR / DPA 2018 compliance as controller/processor | UNKNOWN → 25/02/2027 | v8.2 | Effective date not found in extract |
| 11 | Diversity & Inclusion Policy | 2 | ASTER | Policy | Equality/inclusion commitments across the group | 01/11/2024 → 31/10/2027 | 7.01 | Current |
| 12 | Domestic Abuse Policy | 6 | ASTER | Policy | Support and case handling for domestic abuse | 18/07/2024 → 18/07/2027 | v2.01 | Current |
| 13 | Electrical Installations Safety Policy | 3 | ASTER | Policy | Electrical safety inspection/testing regime | 01/09/2022 → **31/05/2026** | v2.2 | **EXPIRED** |
| 14 | Empty Homes Policy | 3 | ASTER | Policy | Managing void properties between tenancies | 21/10/2025 → 20/10/2028 | V3.00 | Current |
| 15 | Environmental Sustainability Policy | 2 | ASTER | Policy | Environmental management / pollution prevention | 16/07/2025 → 16/07/2028 | 7.00 | Current |
| 16 | Fire Safety Policy | 4 | ASTER | Policy | Fire risk assessment and prevention regime | 01/09/2022 → **31/05/2026** | V3.2 | **EXPIRED**. Notes a deferred Building Safety Act 2022 addendum |
| 17 | Homes (Fitness for Human Habitation) Act 2018 | 10 | **GOV** | Legislation | Act amending the Landlord & Tenant Act 1985 on habitation fitness | Enacted **20 Dec 2018** | c.34 | Crown © 2018 (TSO). Primary law. 2 image/blank pages. Exclusion candidate |
| 18 | Gas, Oil & Solid Fuel Policy | 4 | ASTER | Policy | Fuel-appliance safety regime | 01/10/2023 → 30/09/2026 | V6.0 | Current |
| 19 | Group Health & Safety Policy | 17 | ASTER | Policy | Group-wide H&S duties under HSWA 1974 | 10/06/2025 → **09/06/2026** | v4.2 | **EXPIRED** ~5 weeks ago. Board-approved |
| 20 | Housing Health and Safety Rating System | 185 | **GOV** | Govt operating guidance | The HHSRS hazard-assessment methodology (Housing Act 2004, s.9) | UNKNOWN (pub. **Feb 2006**) | v2 | Crown © 2006 (ODPM). **Largest file — 34% of all corpus pages.** Exclusion candidate |
| 21 | Infestation and Pests Policy | 4 | ASTER | Policy | Pest/infestation responsibilities and eradication | 13/03/2026 → 12/03/2029 | V2.00 | Current (newest effective date) |
| 22 | Leasehold & Freehold Policy | 6 | ASTER | Policy | Duties to leaseholders under lease terms | 02/05/2023 → **02/05/2026** | V2.01 | **EXPIRED** |
| 23 | Lettings Policy | 5 | ASTER | Policy | How homes are allocated/let | 19/08/2025 → 19/08/2028 | V4.02 | Current. 1 image/blank page |
| 24 | Lifts & Lifting Equipment Policy | 4 | ASTER | Policy | Lift servicing/examination regime (LOLER) | 01/09/2022 → **31/05/2026** | v2.3 | **EXPIRED** |
| 25 | Neighbourhood Management Policy | 4 | ASTER | Policy | Managing communal areas/estates | 22/07/2025 → 22/07/2028 | 5.0 | Current |
| 26 | Pets Policy | 5 | ASTER | Policy | Responsible pet ownership rules | 24/10/2024 → 24/10/2027 | V2.03 | Current |
| 27 | Recharges Policy | 4 | ASTER | Policy | Recovering repair costs from customers | 01/04/2024 → 31/03/2027 | v2.00 | Current |
| 28 | Repairs and Maintenance Policy | 4 | ASTER | Policy | Responsive repairs service scope | 05/10/2023 → 05/10/2026 | 4.05 | Current. **Approver field left as "Choose an Option"** |
| 29 | Right to Buy / Right to Acquire Policy | 5 | ASTER | Policy | RTB/RTA/RTSO purchase rights and eligibility | 06/04/2024 → 23/01/2027 | V6.1 | Current |
| 30 | Safeguarding Adults at Risk Policy | 6 | ASTER | Policy | Adult safeguarding duties (Care Act 2014) | 16/07/2025 → 16/07/2028 | V7.01 | Current. Contains named safeguarding-lead contact details |
| 31 | Safeguarding Children at Risk Policy | 6 | ASTER | Policy | Child safeguarding duties | 24/07/2025 → 24/07/2028 | V2.03 | Current |
| 32 | Section 20 Policy | 8 | ASTER | Policy + form | Leaseholder consultation on major works/charges | 19/03/2025 → 19/03/2028 | v5.02 | Current. Tail is an internal workflow/approval form |
| 33 | Service Charge Policy | 4 | ASTER | Policy | How service charges are set and recovered | 06/07/2023 → **05/07/2026** | 3.0 | **EXPIRED** ~10 days ago |
| 34 | Smoke & Carbon Monoxide Alarm Policy | 4 | ASTER | Policy | Alarm installation/testing regime | 01/09/2022 → **31/05/2026** | V1.2 | **EXPIRED**. 1 image/blank page |
| 35 | Temporary Re-Housing (Decant) Policy | 5 | ASTER | Policy | Temporary rehousing during works/emergencies | 29/01/2025 → 29/01/2028 | V1.02 | Current |
| 36 | Tenancy Policy | 5 | ASTER | Policy | Tenancy types and management | 23/04/2025 → 22/04/2028 | V4.01 | Current |
| 37 | Unreasonable Behaviour Policy | 5 | ASTER | Policy | Managing unreasonable customer conduct toward staff | 17/12/2024 → 17/12/2027 | 1.03 | Current |
| 38 | Vulnerability Policy | 5 | ASTER | Policy | Adjustments for customers who disclose vulnerability | 19/09/2025 → 19/08/2028 | V1.00 | Current. 1 image/blank page |
| 39 | awaabs-law-ai-slides | 103 | **3P** | Presentation slides | Legal-briefing/training deck on Awaab's Law + Housing Ombudsman material | UNKNOWN (dated **30 Sep 2025**) | — | **Filename misleading** — content is a law-firm briefing (Ward Hadaway LLP) + Housing Ombudsman, not "AI". Third-party copyright. Sparse text/slide. Exclusion candidate |
| 40 | awaabs-law-policy-web-version-10 | 7 | **UNKNOWN** | Landlord policy | A social landlord's own Awaab's Law policy | Version 1.0 eff **02/03/2026** | 1.0 | **No Aster branding, no author metadata.** Owner UNKNOWN — see notes |

### Notes on the two problem documents
- **#39 `awaabs-law-ai-slides.pdf`** — The filename suggests "AI", but the extracted content is a **legal briefing/training presentation** dated 30 September 2025, attributed on its own slides to a partner at **Ward Hadaway LLP**, with **Housing Ombudsman Service** material appended at the end. The `/Author` metadata ("Becky Ibbertson") is almost certainly the person who saved/compiled the PDF, not the source. **This is third-party copyrighted content, not an Aster document and not an open-licensed government publication.** 103 pages but only ~32K characters extracted (~310 chars/page) — it is genuinely slide-sparse, which matters for retrieval (see Step 3).
- **#40 `awaabs-law-policy-web-version-10.pdf`** — Reads as a **social landlord's own Awaab's Law policy** (first-person "we/our", an internal Risk Assurance Team, an Equality Impact Assessment, version 1.0 effective 2 March 2026). **But it carries none of the Aster group-entity boilerplate or governance block that every one of the 34 Aster policies carries, and has no author metadata.** I cannot confirm from the text whether this is Aster's own draft, a template, or another landlord's document. **Origin: UNKNOWN.** To settle it: confirm with you whether Aster authored/adopted this, or whether it came from an external template/landlord.

---

## Step 2 — Thematic map & overlap

The 34 Aster policies cluster into six operational domains. The 6 non-Aster items (Step 1 flags GOV/3P/UNKNOWN) sit mostly around one hot topic — **housing hazards / Awaab's Law** — which is where retrieval ambiguity concentrates.

**A. Building safety & statutory compliance (9):** Asbestos · Electrical Installations · Fire Safety · Gas/Oil/Solid Fuel · Lifts & Lifting Equipment · Smoke & CO Alarms · Group Health & Safety · Damp/Mould/Condensation · (plus water safety, referenced but **not present**).
**B. Repairs, property & assets (5):** Repairs & Maintenance · Aids & Adaptations · Empty Homes · Recharges · Infestation & Pests · Environmental Sustainability.
**C. Tenancy & housing management (6):** Tenancy · Lettings · Temporary Re-Housing (Decant) · Neighbourhood Management · Pets · Right to Buy/Acquire.
**D. Leasehold, charges & redress (4):** Leasehold & Freehold · Section 20 · Service Charge · Compensation.
**E. Customer, community & safeguarding (9):** Complaints · Customer Voice · Unreasonable Behaviour · Diversity & Inclusion · Domestic Abuse · Anti-Social Behaviour · Safeguarding Adults · Safeguarding Children · Vulnerability.
**F. Information governance (1):** Data Protection, Privacy & Confidentiality.

**The Awaab's Law / hazards overlap cluster (7 documents, mixed provenance — retrieval hot-spot):**
| Document | Provenance | Role in the topic |
|----------|-----------|-------------------|
| Damp, Mould & Condensation Policy | ASTER | The landlord's operational policy |
| awaabs-law-policy-web-version-10 | UNKNOWN | A landlord Awaab's Law policy (owner unconfirmed) |
| Awaab's Law — tenant guidance (GOV.UK) | GOV | Tenant-facing rights explainer |
| awaabs-law-ai-slides | 3P | Legal/Ombudsman briefing deck |
| Housing Health and Safety Rating System | GOV | Defines the hazards the law references |
| Homes (Fitness for Human Habitation) Act 2018 | GOV | Underpinning legislation |
| A Decent Home (2006) | GOV | The related Decent Homes standard |

A question like "what are the timescales for fixing damp and mould?" can legitimately be answered from four of these at once — a landlord policy, a tenant guide, a legal deck, and government regs — which may **disagree in detail or date**. This is the single most important corpus fact for anyone tuning retrieval or judging answer quality.

---

## Step 3 — Corpus rollup

### Composition (exact)
- **40 PDFs · 542 pages · ~958,000 extracted characters · 10.7 MB on disk.**
- **Text extraction is healthy overall:** ~99% of pages yielded text. Only ~10 pages across 6 files came back empty (image-only covers/dividers): Asbestos, Lettings, Smoke & CO, Vulnerability (1 each), Fitness for Human Habitation Act (2), and the slide deck (5). These are the pages most at risk of the `None`-page chunking crash noted in the codebase recon.
- **Severe size skew.** One government document — **HHSRS, 185 pages (~382K chars)** — is **34% of all pages and ~40% of all extracted text.** The two next-largest (the slide deck at 103 pages, the Decent Home guide at 38) are also non-Aster. **The three largest files in the corpus are all third-party.** The 34 Aster policies are short (median ~5 pages).

### Provenance breakdown
| Origin | Count | Documents |
|--------|------:|-----------|
| **ASTER** (own policy) | 34 | Items 2–4, 6–16, 18–19, 21–38 |
| **GOV** (Crown copyright) | 4 | A Decent Home (2006) · HHSRS (2006) · Fitness for Human Habitation Act (2018) · Awaab's Law tenant guidance (2025) |
| **3P** (third-party non-gov) | 1 | awaabs-law-ai-slides (law firm + Ombudsman) |
| **UNKNOWN** | 1 | awaabs-law-policy-web-version-10 |

### Exclusion shortlist (your call)
These **6 non-Aster items** are the ones to decide on. I am flagging, not recommending removal — several are genuinely useful context — but they carry different ownership, licensing, and freshness profiles than the Aster policies:

1. **HHSRS (2006, ODPM)** — Crown copyright, internal-circulation reproduction permitted. **Nearly 20 years old** and dominates the corpus by size. Keep for hazard definitions, but its bulk will skew any merged index.
2. **A Decent Home (2006, DCLG)** — Crown copyright. **~19 years old**; the standard has evolved since. Verify it reflects current policy before relying on it.
3. **Homes (Fitness for Human Habitation) Act 2018** — primary legislation (Crown copyright, freely reproducible). Authoritative and stable; low risk to keep.
4. **Awaab's Law tenant guidance (2025, MHCLG)** — Open Government Licence v3.0, reusable with attribution. Current. Note it is **tenant-facing**, so its voice/answers differ from a landlord procedure.
5. **awaabs-law-ai-slides** — **third-party copyright (Ward Hadaway LLP / Housing Ombudsman).** No evident redistribution licence. **Highest exclusion priority on IP grounds**, and slide-sparse text makes it weak for retrieval anyway.
6. **awaabs-law-policy-web-version-10** — **origin UNKNOWN.** Decide only after confirming who owns it (see Step 1 notes).

### Data-quality issues found (Aster set)
- **8 of 34 Aster policies are past their stated expiry date as of today (2026-07-15):** Asbestos, Electrical, Fire Safety, Lifts, Smoke & CO (all 31/05/2026), **Group Health & Safety (09/06/2026)**, Leasehold & Freehold (02/05/2026), and **Service Charge (05/07/2026, ~10 days ago).** Notably, five of the eight are **building-safety** policies — the highest-stakes category to be serving from an out-of-date document. A RAG answer will happily cite an expired policy with no signal that it has lapsed.
- **2 policies shipped with an unfilled template field:** Anti-Social Behaviour and Repairs & Maintenance both show `Approved by: Choose an Option` — the dropdown placeholder was never completed.
- **Template artifacts throughout:** many files retain `Click or tap to enter a date` placeholders and repeat the long group-entity boilerplate on both first and last pages. This boilerplate is near-identical across ~20 files and will produce **many near-duplicate chunks** that add retrieval noise and can crowd out substantive text.
- **Contact details / named individuals** appear in a few files (Complaints: phone + postal address; Safeguarding Adults: named lead with email/phone). Worth knowing before any answer is surfaced publicly.

### Implications for the RAG pipeline
- **Topic collision on hazards/Awaab's Law (Step 2).** With 7 overlapping documents of mixed provenance and dates, retrieval must either scope to one authoritative source or the generator must reconcile conflicts. This is the most likely place to produce a confidently wrong or internally contradictory answer.
- **The 20-year-old government pair (HHSRS, Decent Home)** can surface dated guidance against current Aster policy. If both are indexed together, freshness/authority weighting matters.
- **Boilerplate duplication** inflates chunk counts and BM25 term statistics with legal-entity lists that carry no answer value.
- **The slide deck** (~310 chars/page of fragmented bullets) chunks poorly and is the weakest retrieval citizen in the set, independent of the IP question.
- **Size skew:** if these were ever merged into a single index rather than one-PDF-per-session, HHSRS alone would supply a disproportionate share of chunks.

### What I would need to finish the picture (open questions)
1. **Ownership of `awaabs-law-policy-web-version-10`** — Aster's, a template, or another landlord's? (Currently UNKNOWN.)
2. **Redistribution rights for `awaabs-law-ai-slides`** — is there a licence to hold/serve the Ward Hadaway / Ombudsman material?
3. **Is the corpus used one-PDF-per-session, or merged into one shared index?** It changes how much the size skew and cross-document conflicts matter.
4. **Are the two 2006 government documents intentionally retained as historical reference, or should they be refreshed** to current-standard equivalents?
5. **Should expired policies be excluded or flagged at answer time?** Eight are currently past expiry, five of them safety-critical.
6. **Interior-page verification** — characterisations here rest on each document's opening/closing plus a keyword sweep; a full page-by-page read would firm up the medium-confidence subject lines if that precision is needed.

*End of corpus summary. Step 3 (this rollup) is reproduced to the terminal.*
