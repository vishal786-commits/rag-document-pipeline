# DocMind — Codebase Reconnaissance

> Recon date: 2026-07-14 · Branch: `dev` · Reviewer: automated deep-read of every tracked source file.
> This is an honest engineering assessment, not marketing copy. Sections 14–16 are deliberately unflattering.

---

## 1. What this is (plain language)

DocMind is a single-document **RAG (retrieval-augmented generation) chatbot**. A user uploads one PDF; the app extracts its text, splits it into ~900-character chunks, embeds each chunk with OpenAI `text-embedding-3-small`, and stores the vectors in a **Pinecone** index under a per-upload namespace (a random UUID that doubles as the "session id"). When the user asks a question, the system rewrites the question for spelling/grammar, embeds it, retrieves candidate chunks two ways — **dense** (Pinecone cosine) and **sparse** (BM25 keyword over the *whole* chunk corpus) — fuses the two rankings with **Reciprocal Rank Fusion (RRF)**, stuffs the top chunks into a `gpt-3.5-turbo` prompt, and returns a grounded answer. There are two processes: a **FastAPI** backend (`main.py`, port 8000) that does all the real work, and a **Streamlit** frontend (`frontend/app.py`, port 8501) that is a pure HTTP client of the backend. Both are baked into one Docker image and launched together by `docker-entrypoint.sh`; CI builds that image, smoke-tests `/health`, pushes to ECR, and deploys to AWS ECS. There is a real, reusable **retrieval eval harness** (`eval/`) with 20 labeled questions against a sample insurance policy — that is the strongest-engineered part of the repo.

**Maturity:** solid personal/portfolio project. Clean module boundaries, a genuine eval, working CI/CD. But it is single-process, single-user-at-a-time in spirit, has no persistence guarantees, no auth, no automated correctness tests, and several silent-failure paths. It would not survive contact with real concurrent traffic without rework.

---

## 2. How to run it

**Local (two terminals):**
```bash
pip install -r requirements.txt
# .env needs: OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_INDEX_NAME  (API_URL optional, frontend only)
uvicorn main:app --reload            # backend  :8000
streamlit run frontend/app.py        # frontend :8501  -> open http://localhost:8501
```

**Docker (both in one container):**
```bash
docker build -t docmind .
docker run -p 8000:8000 -p 8501:8501 --env-file .env docmind
```

**Eval (no PDF upload needed):**
```bash
python -m eval.retrieval_eval --validate   # offline, no API key: confirms gold phrases survive chunking
python -m eval.retrieval_eval              # full run, needs OPENAI_API_KEY; caches embeddings to eval/.cache
```

Prereqs the code assumes but does not check for you: a Pinecone index that already exists with **1536 dimensions** and **cosine** metric (matching `text-embedding-3-small`). Nothing in the code creates the index.

---

## 3. Architecture map

```
                 ┌──────────────────────────┐
  Browser  ──▶   │  Streamlit  (app.py:8501)│   pure HTTP client, holds UI session_state
                 └────────────┬─────────────┘
                              │ requests.post(/upload, /ask)
                              ▼
                 ┌──────────────────────────┐
                 │   FastAPI  (main.py:8000) │   in-process dict `chat_memory[session_id]`
                 └───┬───────────────────┬───┘
            ingest() │                   │ answer()
                     ▼                   ▼
   read_pdf ─ chunk_pages ─ embed   rewrite_query ─ embed_user_query
        │        │            │           │              │
        │        │            ▼           │              ▼
        │        │      store_in_pinecone │        search_in_pinecone  (dense)
        │        └──▶ save_corpus ────────┼──────▶ get_corpus ─ bm25_rank (sparse)
        │             (.corpus/*.json)    │              │
        │                                 └──▶ reciprocal_rank_fusion(dense, sparse)
        │                                              │
        └──────────────────────────────────────▶ query_llm_with_context ─▶ answer text
```

Two independent state stores back retrieval: **Pinecone** (dense vectors, source of truth) and **`.corpus/<namespace>.json` + an in-process dict** (full chunk text for BM25). They are written together in `ingest()` but are not transactional and can drift.

---

## 4. Module-by-module tour

| File | Responsibility | Notes |
|------|----------------|-------|
| `main.py` | FastAPI app: `/`, `/health`, `/upload`, `/ask`; in-memory `chat_memory` | Session state is a plain dict — see §16. |
| `src/pdfreader.py` | `read_pdf` → list of page-text strings | Swallows exceptions, returns `[]`; can emit `None` pages (§10). |
| `src/chunker.py` | `chunk_pages` via LangChain `RecursiveCharacterTextSplitter` (900/150) | Joins all pages first, so **page boundaries and page numbers are lost** — no citations possible. |
| `src/embedder.py` | `embed_chunks`, `embed_user_query` (OpenAI) | Embeds chunks **one at a time in a loop** (§14); returns `[]` sentinel on failure (§16). |
| `src/vectorstore.py` | Pinecone upsert / query, lazy singleton index | `store_in_pinecone` **swallows all errors** → ingest "succeeds" on a failed write. Return type annotation lies (§15). |
| `src/corpus_store.py` | Full chunk list per namespace, in-mem cache + JSON file | Never evicted / never cleaned up (§16). Honest, well-documented module. |
| `src/hybrid.py` | `bm25_rank` (full corpus), `reciprocal_rank_fusion` | Cleanest, best-documented file. Deterministic tie-breaking. |
| `src/llm.py` | `rewrite_query`, `query_llm_with_context` (gpt-3.5-turbo) | Long system prompt; graceful fallbacks on API error. |
| `src/query.py` | Orchestrates rewrite → embed → dense+sparse → RRF → generate; `_retrieval_sizes` dynamic k | Also holds legacy `rerank_with_bm25` that **duplicates** `hybrid.bm25_rank` (§16). |
| `src/ingest.py` | read → chunk → embed → store + save_corpus; returns chunk count | No rollback if half the steps fail. |
| `frontend/app.py` | Streamlit chat UI (~940 lines, mostly inline CSS) | Status panel shows hardcoded/always-green connection state (§15). |
| `eval/retrieval_eval.py` | Offline reproducible retrieval eval, 3 strategies, MRR/Recall | Genuinely good; imports real `src/` code so numbers are honest. |

---

## 5. Data & storage model

- **Namespace = session id = upload id = Pinecone namespace = corpus filename.** One identity (a UUID minted per upload in `main.py`) is overloaded to mean all five things. There is no concept of a user, and no relationship between two uploads by the same person.
- **Pinecone vectors:** id `chunk_{i}`, metadata `{text, chunk_index}`. IDs are unique only within a namespace. Re-uploading the same file makes a brand-new namespace; the old one is never deleted.
- **Corpus store:** `.corpus/<namespace>.json` = the full ordered chunk list, mirrored in an in-process `_cache` dict. This exists purely because Pinecone is awkward for "give me every chunk in this namespace" (needed for full-corpus BM25).
- **Chat history:** `chat_memory[session_id]["history"]` = list of `(question, answer)` tuples, in RAM only.
- **Uploaded files:** written to `uploaded_pdfs/<original filename>` on disk, keyed by filename (not by UUID) — collision-prone (§16).

Nothing has a TTL. Nothing is garbage-collected. Vectors, corpus files, and RAM entries accumulate for the life of the index/container.

---

## 6. Request lifecycles

**Upload (`POST /upload`)**
1. Mint `session_id = uuid4()`.
2. `await file.read()` → write bytes to `uploaded_pdfs/<filename>` (offloaded to a thread).
3. `ingest(file_path, namespace=session_id)`: read PDF → chunk → embed every chunk → upsert to Pinecone (batches of 100) → `save_corpus`.
4. Seed `chat_memory[session_id] = {history: [], chunk_count}`.
5. Return `{session_id}`.

**Ask (`POST /ask?session_id=…&question=…`)**
1. Look up session; **if missing, silently fall back to `{history: [], chunk_count: 20}`** (§15).
2. `_retrieval_sizes(chunk_count)` → `(candidate_k, final_k)`.
3. `rewrite_query` (LLM call #1) → `embed_user_query` (embedding call) → `search_in_pinecone` (dense).
4. `get_corpus` → `bm25_rank` (sparse, full corpus) → `reciprocal_rank_fusion` → top `final_k`. If corpus missing, fall back to `rerank_with_bm25` over dense candidates only.
5. `query_llm_with_context` with the **original** question (not the rewritten one) + chat history (LLM call #2).
6. Append `(question, answer)` to history; return `{answer}`.

Every question therefore costs **2 OpenAI chat calls + 1 embedding call**, strictly sequential.

---

## 7. External services & dependencies

- **OpenAI:** embeddings (`text-embedding-3-small`) + chat (`gpt-3.5-turbo`). Synchronous SDK wrapped in `asyncio.to_thread`.
- **Pinecone:** vector index (name from `PINECONE_INDEX_NAME`). Lazy singleton client.
- **AWS:** ECR (image registry) + ECS (runtime), driven by GitHub Actions. Region `ap-south-1`.
- **Python libs:** `fastapi`, `uvicorn`, `streamlit`, `pypdf`, `langchain-text-splitters[all]`, `rank-bm25`, `python-dotenv`, `requests`, `python-multipart`. **All unpinned** in `requirements.txt` (§16).

---

## 8. Configuration & secrets

- `.env` (gitignored): `OPENAI_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, and locally also `API_URL`.
- `.env.example` documents only the first three — **`API_URL` is undocumented** (frontend uses it to find the backend).
- `CORS_DIR`… actually `CORPUS_DIR` env var overrides `.corpus` location (undocumented).
- CI secrets: `AWS_*`, `ECS_TASK_DEFINITION`, `ECS_SERVICE`, `ECS_CLUSTER`, `CONTAINER_NAME`.
- A real `.env` with live-looking keys is present in the working tree. It is correctly gitignored, but it exists on disk — treat those keys as needing rotation if this machine is ever shared.

---

## 9. Concurrency & async model

Everything is declared `async`, and blocking SDK calls are correctly pushed to threads via `asyncio.to_thread` — so the event loop is not blocked. **But there is almost no actual parallelism where it matters:** `embed_chunks` embeds chunks one-by-one in a `for` loop, awaiting each before starting the next. A 200-chunk document makes 200 sequential embedding round-trips. The "async end-to-end" work made the call chain non-blocking for *other requests*, but did not make any single ingest or query faster. `corpus_store` functions are sync (fine, they're fast/local) but are called from async code without `to_thread` — trivial disk I/O, low risk.

---

## 10. Error handling & failure modes

The dominant pattern is **catch-everything-and-return-a-sentinel**, which converts failures into silent wrong-but-successful results:

- `read_pdf` → returns `[]` on any error → 0 chunks → upload reports success with an empty document.
- `pypdf`'s `extract_text()` can return `None` for image-only pages; `"\n".join(pages)` in `chunker` will raise `TypeError` if any page is `None` — an *un*handled path inside the "handled" one.
- `embed_chunks` → appends `[]` (a zero-length vector) for a failed chunk, keeping list length equal to `chunks`, so the `len(chunks)==len(embeddings)` guard in `store_in_pinecone` **passes** and a malformed empty vector is upserted.
- `store_in_pinecone` → catches everything, prints, returns `None`. `ingest` then returns `len(chunks)` regardless, so **a totally failed Pinecone write still returns a happy `chunk_count`.**
- `embed_user_query` → `[]` on failure → a Pinecone query with an empty vector.
- LLM helpers fail soft to friendly strings — the one place soft failure is appropriate.

Net: the system is very good at *not crashing* and very bad at *telling you it failed*.

---

## 11. Testing & evaluation

- **No unit or integration tests.** No `pytest`, no test directory. The word "test" in the CI job name refers only to a container health-check curl.
- **The eval harness is the real testing asset.** `eval/retrieval_eval.py` reproduces Pinecone's cosine ranking locally, caches embeddings, scores Dense / Dense+rerank / Hybrid-RRF on 20 gold-labeled questions, and has an offline `--validate` mode requiring no API key. It imports the actual `src/` code, so its numbers are trustworthy. This is portfolio-grade work and the healthiest part of the repo.
- Gap: the eval covers **retrieval**, not generation, not the API layer, not chunking edge cases, not failure paths.

---

## 12. Build, container & CI/CD

- **Dockerfile:** `python:3.11-slim`, installs unpinned requirements, copies `main.py`, `src/`, `frontend/`. Note it does **not** copy `eval/` or `data/` (fine — they aren't needed at runtime). Runs as **root** (no non-root user).
- **Entrypoint:** starts `uvicorn` in the background (`&`) and `exec`s Streamlit in the foreground. Consequence: **if uvicorn dies, the container stays alive** because Streamlit is PID 1's exec target. The backend can be dead while the container looks healthy to any check pointed at 8501.
- **CI (`.github/workflows/ci.yml`):** on push to `main` — build → run container with dummy keys → poll `/health` up to 60s → push `:sha` and `:latest` to ECR → render task def → deploy to ECS with `wait-for-service-stability`. Health check only validates port 8000. No test stage, no lint, no eval run gate.
- The git log shows a long, painful CI-stabilization history (`fixed-final`, `fixed-final-really`) — the pipeline works now but was hard-won.

---

## 13. Security posture

- **No authentication or authorization anywhere.** `/upload` and `/ask` are open. Anyone who can reach the backend can upload and query.
- `session_id` (a UUID) is the only access control on a document's chunks, and it is returned to the client in plaintext. There's no verification that the caller "owns" the session.
- **Question is passed as a URL query parameter** on `/ask` — it lands in access logs, proxies, and browser history, and is subject to URL length limits.
- No rate limiting → each request spends real OpenAI money; an open endpoint is a billing-DoS vector.
- No CORS middleware (works today only because the browser talks to Streamlit, and Streamlit talks to FastAPI server-side).
- Container runs as root.
- Uploaded filenames are used unsanitized for the on-disk path (`os.path.join(UPLOAD_DIR, file.filename)`) — a crafted `filename` with `../` is a path-traversal concern.

---

## 14. Performance & cost characteristics

**Latency, per question (all sequential):**
1. `rewrite_query` — a full `gpt-3.5-turbo` round-trip **on every question**, purely to fix spelling. This is pure added latency for the common case where the question is already clean.
2. `embed_user_query` — one embedding round-trip.
3. `search_in_pinecone` — one Pinecone round-trip.
4. `bm25_rank` — **re-tokenizes and re-fits `BM25Okapi` over the entire corpus on every single query** (nothing is cached; the index is rebuilt from scratch each ask). Cheap for 28 chunks, linear and wasteful for large documents.
5. `query_llm_with_context` — the main `gpt-3.5-turbo` call, and it replays the **entire chat history** every turn, so token cost grows with conversation length.

**Ingest latency:** dominated by `embed_chunks` doing **N sequential embedding calls** (one per chunk). This is the single biggest performance defect: a large PDF ingests in O(N) round-trips when OpenAI's embeddings endpoint accepts batched input in one call. Batching would cut ingest time by ~1–2 orders of magnitude.

**Cost drivers:** 2 chat calls + 1 embedding per question; full-history replay; a never-pruned Pinecone index that accrues storage cost for every document ever uploaded, forever.

**Scaling ceiling:** the in-process `chat_memory` dict and the in-process corpus `_cache` mean the app is effectively **single-replica**. Two ECS tasks behind a load balancer would serve inconsistent sessions (a question routed to the replica that didn't ingest the doc falls back to `chunk_count: 20` and an empty corpus). BM25-rebuild-per-query and per-chunk embedding both scale badly with document size.

---

## 15. Leaky abstractions & coupling

**The standout — a retrieval-tuning constant has leaked into the HTTP layer.** In `main.py`, the `/ask` fallback for an unknown session is:

```python
session = chat_memory.get(session_id, {"history": [], "chunk_count": 20})
```

That literal `20` is not an arbitrary default — it is exactly the large-document `candidate_k` produced by `_retrieval_sizes` in `src/query.py`. The web/session layer now silently encodes a retrieval-depth decision that belongs entirely to the retrieval module. Change the retrieval sizing policy in `query.py` and this `20` in `main.py` becomes quietly wrong, with no test and no comment linking the two. The HTTP endpoint should not know or care how deep retrieval goes.

**Other leaks, in decreasing severity:**

- **`search_in_pinecone`'s type signature lies about the boundary.** It is annotated `-> List[dict]` and documented as returning "search results with metadata and similarity scores," but it actually returns `List[str]` (it reaches into `match.metadata["text"]` and throws the scores away). The caller in `query.py` correctly treats them as strings. The abstraction claims to expose Pinecone match objects but has already collapsed them to bare text — so scores can never be used for fusion weighting downstream, and the annotation actively misleads.

- **`query.py:rerank_with_bm25` knows about process lifecycle.** Its docstring justifies itself as the path "when the full corpus isn't available … e.g. a namespace ingested before this process started." A pure reranking function is reasoning about *in-memory cache warmth / container restarts* — a `corpus_store` implementation detail that has bled into retrieval logic. Retrieval shouldn't know why the corpus might be missing.

- **The frontend hardcodes the backend's address in its status UI.** `frontend/app.py` renders a status card reading `API Connected / localhost:8000` as static markup, even though the real backend URL is `os.environ["API_URL"]`. The "Connected" dot is always green regardless of whether the backend is reachable — the UI asserts a fact it never checks, and hardcodes a deployment detail that is configurable everywhere else.

- **One identifier means five things.** `namespace` is simultaneously the Pinecone namespace, the corpus filename, the chat-memory key, the upload id, and the "session." Modules named for storage (`vectorstore`, `corpus_store`) take a parameter called `namespace`, but `main.py` passes a `session_id` and `query.py`'s `answer()` receives it positionally as `namespace`. The naming seam hides that these concepts are fused, which is exactly why the multi-replica story is broken.

---

## 16. Debt and landmines (ranked, worst first)

1. **Ingest reports success on a failed Pinecone write.** `store_in_pinecone` swallows every exception; `ingest` returns `len(chunks)` unconditionally. A user can "successfully" upload a document that stored zero vectors, then get "The document does not cover this topic" for everything. Silent data loss with a green checkmark.

2. **Failed embeddings become empty vectors that get upserted.** `embed_chunks` appends `[]` on error, the length guard passes, and a 0-dimension vector goes to Pinecone (or an empty query vector goes to search). Corrupts retrieval silently.

3. **Single-replica by construction.** `chat_memory` (RAM dict) and corpus `_cache` (RAM dict) are per-process. Any horizontal scaling breaks sessions and corpus availability. The CD pipeline deploys to ECS as if this were stateless; it is not.

4. **Nothing is ever cleaned up.** Pinecone namespaces, `.corpus/*.json` files, `uploaded_pdfs/*`, and `chat_memory` entries all grow without bound. "Remove document" in the UI only clears Streamlit state — the vectors, corpus file, and disk PDF all persist. This is an unbounded cost and storage leak.

5. **Per-chunk sequential embedding.** `embed_chunks` makes one API call per chunk in a loop. The embeddings endpoint batches; this should be a single (or few) call(s). Biggest, easiest perf win in the repo. (§14)

6. **`extract_text()` can return `None`.** `chunk_pages` does `"\n".join(pages)`; a single image page yields `None` and raises `TypeError` — inside code that was written to look robust. Untested.

7. **Upload path keyed by original filename, not UUID.** `uploaded_pdfs/<file.filename>` — two uploads named `policy.pdf` overwrite each other on disk, and unsanitized filenames enable `../` path traversal. (§13)

8. **No auth, no rate limit, question in URL.** Open money-spending endpoints; billing-DoS and log-leakage exposure. (§13)

9. **Unpinned dependencies.** `requirements.txt` has zero version constraints. A breaking upstream release (LangChain, Pinecone SDK, and OpenAI SDK all move fast) can break a fresh build or the next CI run with no code change. Reproducibility is not guaranteed.

10. **Container hides a dead backend.** uvicorn runs backgrounded behind a foregrounded Streamlit `exec`; uvicorn can die while the container stays "up." No process supervisor, no restart. (§12)

11. **Duplicated BM25 logic.** `query.py:rerank_with_bm25` and `hybrid.py:bm25_rank` reimplement the same tokenize-and-score. The fallback also re-fits BM25 on a tiny candidate set, giving different (worse) IDF statistics than the full-corpus path it's standing in for — a subtle correctness drift between the two paths.

12. **Runs as root in the container**, no non-root `USER`.

13. **Empty `src/__init__.py`** plus `sys.path` juggling in the eval — imports work but the packaging story is ad hoc.

14. **`temperature=0.5`** on an assistant whose whole prompt demands "never invent facts / strictly use context" — a mild but real invitation to drift.

15. **`.env` with real-looking secrets sits in the working tree.** Correctly gitignored, but present; rotate if the machine isn't trusted.

16. **Undocumented config knobs:** `API_URL` and `CORPUS_DIR` are read from the environment but absent from `.env.example`.

---

## 17. Open questions (what I'd need to ask you)

1. **Is this meant to be multi-user / multi-replica, or is single-instance the accepted design?** Almost every §16 item above changes priority depending on the answer. Right now the CD pipeline implies "scalable service" but the code implies "one process, one user at a time."
2. **What is the intended document size?** The per-chunk embedding and per-query BM25 rebuild are fine for a 28-chunk policy PDF and painful for a 500-page manual. Knowing the target changes what "fix" means.
3. **Is there supposed to be a lifecycle for Pinecone namespaces and corpus files** (delete on "Remove document", TTL, per-user quota), or is unbounded growth acceptable for now?
4. **Is the deployed ECS service actually live and public?** If so, the missing auth/rate-limit is urgent; if it's a private demo, it's deferrable.
5. **Why `gpt-3.5-turbo`?** Cost, or just not revisited? A newer model would improve grounding quality at similar or lower cost and might let you drop the separate rewrite call.
6. **Is the query-rewrite step earning its latency/cost?** It fires a full LLM call on every question. Do you have evidence it improves retrieval enough to justify being on the hot path (vs. cheaper local normalization, or skipping it)?
7. **Is losing page numbers during chunking acceptable?** The current design makes source citations ("see page 7") impossible. If citations matter, chunking needs to carry page metadata.
8. **What should happen when ingest partially fails?** Today it reports success. Do you want it to surface the failure to the user, retry, or roll back?

---

*End of recon. Sections 1, 14, and 15 are reproduced in the terminal for immediate reading.*
