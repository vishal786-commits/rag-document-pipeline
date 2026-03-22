# DocMind — RAG Document Pipeline

A modular **Retrieval-Augmented Generation (RAG)** system with a FastAPI backend and Streamlit frontend.  
Upload any PDF and ask questions in plain English — DocMind retrieves the exact context and answers precisely.

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
5. Rewrite user query using LLM to fix spelling and grammar
6. Embed the rewritten query
7. Retrieve top-k chunks from Pinecone (dynamic — scales with document size)
8. Rerank retrieved chunks using BM25 keyword scoring
9. Generate a grounded answer using GPT with reranked context

---

## Project Structure

```
rag-document-pipeline/
│
├── src/
│   ├── chunker.py        # sentence-aware recursive chunking
│   ├── embedder.py       # OpenAI embedding generation
│   ├── pdfreader.py      # PDF text extraction
│   ├── vectorstore.py    # Pinecone upsert and retrieval
│   ├── llm.py            # LLM prompt construction and response
│   ├── ingest.py         # ingestion pipeline (read → chunk → embed → store)
│   └── query.py          # query pipeline (embed → retrieve → generate)
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
| `embedder.py` | Generates embeddings via OpenAI `text-embedding-ada-002` |
| `vectorstore.py` | Upserts and queries Pinecone with session-scoped namespaces |
| `llm.py` | Query rewriting, prompt construction, LLM response generation |
| `ingest.py` | Orchestrates ingestion pipeline, returns chunk count |
| `query.py` | Query rewriting → embedding → dynamic retrieval → BM25 reranking → generation |
| `main.py` | FastAPI routes: `GET /`, `POST /upload`, `POST /ask` |
| `frontend/app.py` | Streamlit chat interface — upload, session management, chat history |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/upload` | Upload a PDF, returns `session_id` |
| POST | `/ask` | Ask a question, returns answer with chat history context |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| LLM | OpenAI GPT |
| Embeddings | OpenAI `text-embedding-ada-002` |
| Vector DB | Pinecone |
| Chunking | LangChain `RecursiveCharacterTextSplitter` |
| Backend | FastAPI |
| Frontend | Streamlit |
| Reranking | BM25 (`rank-bm25`) |

---

## Running Locally

**1. Clone and install:**
```bash
git clone https://github.com/vishal786-commits/rag-document-pipeline.git
cd rag-document-pipeline
pip install -r requirements.txt
```

**2. Set up environment variables in `.env`:**
```
OPENAI_API_KEY=your_key
PINECONE_API_KEY=your_key
PINECONE_INDEX=your_index
```

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
