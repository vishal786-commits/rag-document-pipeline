# Ingest Result

> Run: 2026-07-30T16:24:09.248185+00:00 · executed
> Parser: pymupdf4llm · Chunking: heading-aware, max 1200 chars
> Namespace: `knowledgebase` · Embeddings: `text-embedding-3-small`

## Totals

- Documents: **36**
- Chunks: **687**
- Table chunks: **60**
- Boilerplate chunks dropped: **56**
- Blank pages skipped: **6**
- Form pages dropped: **4**

## Per document

| doc_id | audience | status | pages | chunks | tables |
|--------|----------|--------|------:|-------:|-------:|
| a-decent-home-definition-and-guidance-for-implementation | reference | unknown | 38 | 124 | 3 |
| aids-adaptations-policy | staff | current | 5 | 16 | 1 |
| anti-social-behaviour-policy | staff | current | 6 | 21 | 1 |
| asbestos-management-policy | staff | expired | 3 | 15 | 3 |
| compensation-policy | staff | current | 4 | 15 | 1 |
| complaints-policy | staff | current | 6 | 19 | 1 |
| customer-voice-policy | staff | current | 4 | 13 | 1 |
| damp-mould-condensation-policy | staff | current | 4 | 19 | 4 |
| data-protection-privacy-confidentiality-policy | staff | current | 11 | 44 | 7 |
| diversity-inclusion-policy | staff | current | 2 | 8 | 1 |
| domestic-abuse-policy | staff | current | 6 | 19 | 1 |
| electrical-installations-safety-policy | staff | expired | 3 | 12 | 2 |
| empty-homes-policy | staff | current | 3 | 11 | 1 |
| environmental-sustainability-policy | staff | current | 2 | 6 | 1 |
| fire-safety-policy | staff | expired | 4 | 18 | 3 |
| fitness-for-human-habitation-act-2018 | reference | unknown | 8 | 19 | 0 |
| gas-oil-solid-fuel-policy | staff | current | 4 | 13 | 2 |
| group-health-safety-policy | staff | expired | 17 | 54 | 1 |
| infestation-and-pests-policy | staff | current | 4 | 17 | 1 |
| leasehold-freehold-policy | staff | expired | 6 | 21 | 1 |
| lettings-policy | staff | current | 4 | 16 | 1 |
| lifts-lifting-equipment-policy | staff | expired | 4 | 14 | 3 |
| neighbourhood-management-policy | staff | current | 4 | 14 | 1 |
| pets-policy | staff | current | 5 | 18 | 1 |
| recharges-policy | staff | current | 4 | 12 | 1 |
| repairs-and-maintenance-policy | staff | current | 4 | 13 | 2 |
| right-to-buy-right-to-acquire-policy | staff | current | 5 | 16 | 2 |
| safeguarding-adults-at-risk-policy | staff | current | 6 | 21 | 1 |
| safeguarding-children-at-risk-policy | staff | current | 6 | 22 | 2 |
| section-20-policy | staff | current | 4 | 16 | 2 |
| service-charge-policy | staff | expired | 4 | 15 | 1 |
| smoke-carbon-monoxide-alarm-policy | staff | expired | 3 | 13 | 2 |
| temporary-re-housing-decant-policy | staff | current | 5 | 20 | 2 |
| tenancy-policy | staff | current | 5 | 18 | 1 |
| unreasonable-behaviour-policy | staff | current | 5 | 18 | 1 |
| vulnerability-policy | staff | current | 4 | 13 | 1 |

## Pages skipped

- blank/image-only: `Asbestos Management Policy.pdf` pages [4]
- blank/image-only: `Fitness for Human Habitation Act 2018.pdf` pages [2, 4]
- blank/image-only: `Lettings Policy.pdf` pages [5]
- blank/image-only: `Smoke & Carbon Monoxide Alarm Policy.pdf` pages [4]
- blank/image-only: `Vulnerability Policy.pdf` pages [5]
- form tail: `Section 20 Policy.pdf` pages [5, 6, 7, 8]

## Boilerplate dropped

Chunks matching ['overarching (company )?brand'] and no longer than 800 characters. Every drop is listed so the rule can be audited; if anything substantive appears here, tighten the pattern.

| doc_id | page | preview |
|--------|-----:|---------|
| aids-adaptations-policy | 1 | **Aids & Adaptations Policy** Click or tap to enter a date. Aster Group is the overarching brand name of Aster Group Ltd |
| aids-adaptations-policy | 1 | **Aster Group** is our overarching company brand and comprises the following companies and charitable entities. Aster Gr |
| anti-social-behaviour-policy | 1 | p Aster Group is the overarching brand name of Aster Group Ltd and all of its subsidiaries. |
| anti-social-behaviour-policy | 6 | **Aster Group** is our overarching company brand and comprises the following companies and charitable entities. Aster Gr |
| asbestos-management-policy | 1 | Aster Group is the overarching brand name of Aster Group Ltd and all of its subsidiaries. |
| asbestos-management-policy | 3 | **Aster Group** is our overarching company brand and comprises the following companies and charitable entities. Aster Gr |
| compensation-policy | 1 | **Compensation Policy** Click or tap to enter a date. Aster Group is the overarching brand name of Aster Group Ltd and a |
| compensation-policy | 4 | **Aster Group** is our overarching company brand and comprises the following companies and charitable entities. Aster Gr |
| complaints-policy | 1 | **Complaints Policy** Aster Group is the overarching brand name of Aster Group Ltd and all of its subsidiaries. |
| complaints-policy | 6 | Aster Group is our overarching company brand and comprises the following companies and charitable entities. Aster Group  |
| customer-voice-policy | 1 | **Customer Voice Policy** Aster Group is the overarching brand name of Aster Group Ltd and all of its subsidiaries. |
| customer-voice-policy | 4 | **Aster Group** is our overarching company brand and comprises the following companies and charitable entities. Aster Gr |
| data-protection-privacy-confidentiality-policy | 1 | **Data Protection, Privacy & Confidentiality** V8.2 **Policy** Aster Group is the overarching brand name of Aster Group  |
| data-protection-privacy-confidentiality-policy | 10 | **Aster Group** is our overarching company brand and comprises the following companies and charitable entities. Aster Gr |
| diversity-inclusion-policy | 1 | **Diversity and Inclusion Policy** Aster Group is the overarching brand name of Aster Group Ltd and all of its subsidiar |
| diversity-inclusion-policy | 1 | - Knowing our customers and colleagues better and making it easy for them to tell us who they are to enable us tailor wh |
| domestic-abuse-policy | 1 | **Domestic Abuse Policy** Click or tap to enter a date. Aster Group is the overarching brand name of Aster Group Ltd and |
| domestic-abuse-policy | 1 | - 1.5 Further to this there is a statutory definition of DA: _"Behaviour of_ a _person (''.A'') towards another person ( |
| domestic-abuse-policy | 6 | **Aster Group** is our overarching company brand and comprises the following companies and charitable entities. Aster Gr |
| electrical-installations-safety-policy | 1 | Aster Group is the overarching brand name of Aster Group Ltd and all of its subsidiaries. |
| electrical-installations-safety-policy | 3 | **Aster Group** is our overarching company brand and comprises the following companies and charitable entities. Aster Gr |
| empty-homes-policy | 1 | **Empty Homes Policy** Click or tap to enter a date. Aster Group is the overarching brand name of Aster Group Ltd and al |
| environmental-sustainability-policy | 1 | **Environmental Sustainability Policy** Aster Group is the overarching brand name of Aster Group Ltd and all of its subs |
| fire-safety-policy | 1 | Aster Group is the overarching brand name of Aster Group Ltd and all of its subsidiaries. |
| fire-safety-policy | 3 | **Aster Group** is our overarching company brand and comprises the following companies and charitable entities. Aster Gr |
| gas-oil-solid-fuel-policy | 1 | **Gas, Oil and Solid Fuel Safety Policy** Aster Group is the overarching brand name of Aster Group Ltd and all of its su |
| group-health-safety-policy | 1 | Aster Group is the overarching brand name of Aster Group Ltd and all of its subsidiaries. |
| infestation-and-pests-policy | 1 | **Infestations and Pests Policy** Click or tap to enter a date. Aster Group is the overarching brand name of Aster Group |
| infestation-and-pests-policy | 4 | **Aster Group** is our overarching company brand and comprises the following companies and charitable entities. Aster Gr |
| lettings-policy | 1 | **Lettings Policy** Click or tap to enter a date. Aster Group is the overarching brand name of Aster Group Ltd and all o |
| lifts-lifting-equipment-policy | 1 | **Lifts & lifting equipment policy** Aster Group is the overarching brand name of Aster Group Ltd and all of its subsidi |
| lifts-lifting-equipment-policy | 3 | > **Aster Group** is our overarching company brand and comprises the following companies and charitable entities. Aster  |
| neighbourhood-management-policy | 1 | Aster Group is the overarching brand name of Aster Group Ltd and all of its subsidiaries. |
| neighbourhood-management-policy | 4 | **Aster Group** is our overarching company brand and comprises the following companies and charitable entities. Aster Gr |
| pets-policy | 1 | **Pets Policy** Click or tap to enter a date. Aster Group is the overarching brand name of Aster Group Ltd and all of it |
| pets-policy | 5 | **Aster Group** is our overarching company brand and comprises the following companies and charitable entities. Aster Gr |
| recharges-policy | 1 | Aster Group is the overarching brand name of Aster Group Ltd and all of its subsidiaries. |
| recharges-policy | 4 | **Aster Group** is our overarching company brand and comprises the following companies and charitable entities. Aster Gr |
| repairs-and-maintenance-policy | 1 | **Repairs & Maintenance Policy** Aster Group is the overarching brand name of Aster Group Ltd and all of its subsidiarie |
| repairs-and-maintenance-policy | 4 | **Aster Group** is our overarching company brand and comprises the following companies and charitable entities. Aster Gr |
| right-to-buy-right-to-acquire-policy | 1 | **Right To Buy/ Right to Acquire Policy** Aster Group is the overarching brand name of Aster Group Ltd and all of its su |
| right-to-buy-right-to-acquire-policy | 5 | **Aster Group** is our overarching company brand and comprises the following companies and charitable entities. Aster Gr |
| safeguarding-adults-at-risk-policy | 1 | **Safeguarding Adults at Risk Policy** Click or tap to enter a date. Aster Group is the overarching brand name of Aster  |
| safeguarding-adults-at-risk-policy | 6 | . > **Aster Group** is our overarching company brand and comprises the following companies and charitable entities. Aste |
| safeguarding-children-at-risk-policy | 1 | **Safeguarding Children Policy** Click or tap to enter a date. Aster Group is the overarching brand name of Aster Group  |
| section-20-policy | 1 | **Section 20 Policy** Click or tap to enter a date. Aster Group is the overarching brand name of Aster Group Ltd and all |
| section-20-policy | 4 | **Aster Group** is our overarching company brand and comprises the following companies and charitable entities. Aster Gr |
| smoke-carbon-monoxide-alarm-policy | 1 | Aster Group is the overarching brand name of Aster Group Ltd and all of its subsidiaries. |
| smoke-carbon-monoxide-alarm-policy | 3 | **Aster Group** is our overarching company brand and comprises the following companies and charitable entities. Aster Gr |
| temporary-re-housing-decant-policy | 1 | **Temporary Re-Housing (Decant) Policy** Click or tap to enter a date. Aster Group is the overarching brand name of Aste |
| temporary-re-housing-decant-policy | 1 | **Aster Group** is our overarching company brand and comprises the following companies and charitable entities. Aster Gr |
| tenancy-policy | 1 | Aster Group is the overarching brand name of Aster Group Ltd and all of its subsidiaries. |
| tenancy-policy | 5 | - **Aster Group** is our overarching company brand and comprises the following companies and charitable - entities. Aste |
| unreasonable-behaviour-policy | 1 | **Unreasonable Behaviour Policy** Click or tap to enter a date. Aster Group is the overarching brand name of Aster Group |
| unreasonable-behaviour-policy | 5 | **Aster Group** is our overarching company brand and comprises the following companies and charitable entities. Aster Gr |
| vulnerability-policy | 4 | **Aster Group** is our overarching company brand and comprises the following companies and charitable entities. Aster Gr |

## Duplicate review candidates

Bodies repeated verbatim across at least 5 distinct documents that were **kept**. These are templated clauses; some carry real answer value (a monitoring or review commitment) and some do not. Nothing here is dropped automatically -- if one of these is pure boilerplate, add a pattern to `BOILERPLATE_PATTERNS` in `rag/config.py`.

| docs | chars | preview |
|-----:|------:|---------|
| 5 | 290 | - 3.3 The effectiveness of this policy will be continuously monitored, and the embedding of the policy scrutin |
