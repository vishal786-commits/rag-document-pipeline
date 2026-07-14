# DocMind — RAG Document Pipeline

A modular **Retrieval-Augmented Generation (RAG)** system with a FastAPI backend and Streamlit frontend.  
Upload a PDF and ask questions in plain English — DocMind retrieves relevant context and answers using that context.

---

## System Architecture

<p align="center">
  <img src="assets/System Architecture.svg" alt="RAG System Architecture" width="800"/>
</p>

**Pipeline flow:**

1. Extract text from a PDF
2. Split text into sentence-aware chunks (recursive character splitting)
3. Generate vector embeddings via OpenAI
4. Store vectors in Pinecone under a unique session namespace
5. Rewrite the user query with the LLM (spelling / grammar / clarity)
6. Embed the rewritten query
7. Retrieve top-k chunks from Pinecone — dense/semantic (dynamic — scales with document size)
8. Rank the full chunk corpus with BM25 — sparse/keyword
9. Fuse the dense and BM25 rankings with Reciprocal Rank Fusion (RRF)
10. Generate a grounded answer with GPT using the fused context

---

## Project Structure

```
rag-document-pipeline/
│
├── src/
│   ├── chunker.py        # sentence-aware recursive chunking
│   ├── embedder.py       # OpenAI embedding generation
│   ├── pdfreader.py      # PDF text extraction
│   ├── vectorstore.py    # Pinecone upsert and retrieval (dense)
│   ├── corpus_store.py   # per-namespace chunk store for full-corpus BM25 (sparse)
│   ├── hybrid.py         # BM25 ranking + Reciprocal Rank Fusion
│   ├── llm.py            # LLM prompt construction and response
│   ├── ingest.py         # ingestion pipeline (read → chunk → embed → store)
│   └── query.py          # query pipeline (rewrite → embed → dense+BM25 → RRF → generate)
│
├── frontend/
│   └── app.py            # Streamlit UI
│
├── assets/
│   └── System Architecture.svg
│
├── main.py               # FastAPI entry point
├── requirements.txt
└── README.md
```

---

| Module | Description |
|--------|-------------|
| `pdfreader.py` | Extracts raw text from PDF, returns list of page strings |
| `chunker.py` | Splits text using `RecursiveCharacterTextSplitter` — respects sentence boundaries |
| `embedder.py` | Generates embeddings via OpenAI `text-embedding-3-small` |
| `vectorstore.py` | Upserts and queries Pinecone with session-scoped namespaces (dense retrieval) |
| `corpus_store.py` | Persists the full chunk list per namespace so BM25 can score every chunk |
| `hybrid.py` | Full-corpus BM25 ranking and Reciprocal Rank Fusion of dense + sparse |
| `llm.py` | Query rewriting, prompt construction, LLM response (`gpt-3.5-turbo`) |
| `ingest.py` | Orchestrates ingestion pipeline, returns chunk count |
| `query.py` | Query rewriting → embedding → dense + full-corpus BM25 → RRF fusion → generation |
| `main.py` | FastAPI routes: `GET /`, `POST /upload`, `POST /ask` |
| `frontend/app.py` | Streamlit chat interface — upload, session management, chat history |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/upload` | Upload a PDF (`multipart/form-data` field `file`); returns `session_id` |
| POST | `/ask` | Query params: `session_id`, `question` — returns `answer` (uses server-side chat history for that session) |

The Streamlit app expects the API at `http://localhost:8000` by default (`frontend/app.py`).

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| LLM | OpenAI `gpt-3.5-turbo` |
| Embeddings | OpenAI `text-embedding-3-small` |
| Vector DB | Pinecone |
| Chunking | LangChain `RecursiveCharacterTextSplitter` |
| Backend | FastAPI |
| Frontend | Streamlit |
| Hybrid retrieval | Dense (Pinecone) + BM25 (`rank-bm25`) fused with Reciprocal Rank Fusion |

---

## Retrieval Evaluation

Retrieval quality is measured on a labeled set of **20 questions** grounded in the
sample policy document. A query counts as a hit if a chunk containing the gold evidence
phrase appears in the top *k*. Dense ranking is reproduced with local cosine similarity
over the same `text-embedding-3-small` vectors Pinecone stores, so results are
deterministic and repeatable. Recall@k / MRR@k:

| k | Dense-only | Dense + BM25 rerank | Hybrid dense + BM25 (RRF) |
|---|------------|---------------------|---------------------------|
| 3 | 90.0% / 0.817 | 95.0% / 0.925 | **95.0% / 0.925** |
| 5 | 95.0% / 0.827 | 95.0% / 0.925 | **95.0% / 0.925** |

Adding BM25 lifts **Recall@3 from 90% → 95%** and **MRR@3 from 0.82 → 0.93** over
dense-only. The advantage of full **RRF fusion** over merely reranking dense's candidates
shows up once dense retrieval is capped below corpus size (the real large-document
condition): with a capped candidate pool, plain rerank's MRR@3 drops to ~0.84 while hybrid
RRF holds 0.93, because it fuses in high-BM25 chunks from the *whole* corpus rather than
reordering what dense already returned. Full methodology, ground truth, and the capped-pool
breakdown are in [`eval/`](eval/); reproduce with:

```bash
python -m eval.retrieval_eval              # full eval (needs OPENAI_API_KEY)
python -m eval.retrieval_eval --pool 8 --k 3   # capped-pool: where RRF beats plain rerank
python -m eval.retrieval_eval --validate       # offline ground-truth check, no API key
```

---

## Running Locally

**1. Clone and install:**

```bash
git clone https://github.com/vishal786-commits/rag-document-pipeline.git
cd rag-document-pipeline
pip install -r requirements.txt
```

**2. Set up environment variables in `.env`:**

```env
OPENAI_API_KEY=your_key
PINECONE_API_KEY=your_key
PINECONE_INDEX_NAME=your_index_name
```

Variable names must match what the code loads (`PINECONE_INDEX_NAME` in `src/vectorstore.py`).

**3. Start the backend:**

```bash
uvicorn main:app --reload
```

**4. Start the frontend:**

```bash
streamlit run frontend/app.py
```

Then open `http://localhost:8501`.

---

## License

To be decided
