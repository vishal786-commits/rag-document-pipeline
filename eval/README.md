# Retrieval Evaluation

Measures retrieval quality of the DocMind pipeline on a labeled question set and
quantifies what the **hybrid dense + BM25 retrieval (RRF)** contributes.

## What it measures

Three strategies are scored at a fixed cutoff `k` on 20 questions grounded in the
sample insurance policy (`data/National Insurance Terms and Conditions for Private Car.pdf`):

| Strategy | Retrieval |
|----------|-----------|
| **Dense-only** | cosine top-k over `text-embedding-3-small` vectors |
| **Dense + rerank** | dense retrieves a candidate pool, BM25 reranks *those candidates* to top-k |
| **Hybrid (RRF)** | independent dense ranking **and** full-corpus BM25 ranking, fused with Reciprocal Rank Fusion — the production path |

The difference between the last two matters: `rerank` can only reorder chunks dense
already found, so it can never recover a keyword match dense dropped. `Hybrid (RRF)`
ranks the **entire corpus** with BM25 and fuses, so a chunk missed by dense can still
surface.

**Metrics:** `Hit@k` / `Recall@k` (a query counts as a hit if any top-k chunk contains
the gold evidence phrase) and `MRR@k`.

Dense retrieval is computed with local cosine similarity over the same embedding
vectors Pinecone stores — this reproduces Pinecone's cosine ranking exactly while
staying deterministic, offline-repeatable, and free of writes to the shared index.
The chunking, embedding, and reranking code is imported directly from `src/`, so the
numbers reflect the real system.

## Ground truth

`eval_set.json` — 20 questions, each with a short `gold` phrase that appears verbatim
in the document. A retrieved chunk is judged relevant if it contains the gold phrase
(whitespace-collapsed, case-insensitive).

## Running

```bash
# Offline sanity check — no API key needed. Confirms every gold phrase survives chunking.
python -m eval.retrieval_eval --validate

# Full eval — needs OPENAI_API_KEY in your environment or .env.
# Embeddings are cached to eval/.cache after the first run, so re-runs are free.
python -m eval.retrieval_eval

# Evaluate at specific cutoffs
python -m eval.retrieval_eval --k 3 --k 5
```

## Results

20 questions, 28 chunks, `text-embedding-3-small`. Recall@k / MRR@k:

| k | Dense-only | Dense + rerank | Hybrid (RRF) |
|---|------------|----------------|--------------|
| 3 | 90.0% / 0.817 | 95.0% / 0.925 | **95.0% / 0.925** |
| 5 | 95.0% / 0.827 | 95.0% / 0.925 | **95.0% / 0.925** |

Both keyword strategies lift **Recall@3 from 90% → 95%** and **MRR@3 from 0.82 → 0.93**
over dense-only retrieval.

**Where hybrid RRF pulls ahead of plain rerank:** on this 28-chunk document the default
candidate pool is the whole corpus, so dense drops nothing and the two keyword strategies
tie. Their behavior diverges once dense retrieval is capped below the corpus size — the
real condition for large documents (`retrieve_k = 20` out of hundreds of chunks). Capping
the pool to simulate that (`--pool 8`):

| k | Dense + rerank MRR@k | Hybrid (RRF) MRR@k |
|---|----------------------|--------------------|
| 3 | 0.842 | **0.925** |

Plain rerank degrades because it can only reorder dense's limited candidates; hybrid RRF
holds its ranking quality by fusing in high-BM25 chunks from the full corpus. Reproduce
with `python -m eval.retrieval_eval --pool 8 --k 3`.
