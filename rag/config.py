"""Every environment variable and tuning constant in the project.

No other module calls os.getenv, so the whole configuration surface is readable
in one screen.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent

# ── Paths ───────────────────────────────────────────────────────────────────
KB_DIR = REPO_ROOT / "knowledge_base"
SUMMARY_PATH = REPO_ROOT / "docs" / "CORPUS_SUMMARY.md"
CHUNKS_PATH = REPO_ROOT / "data" / "kb_chunks.jsonl"
CHUNKS_META_PATH = REPO_ROOT / "data" / "kb_chunks.meta.json"
INGEST_REPORT_PATH = REPO_ROOT / "docs" / "INGEST_RESULT.md"

# ── Credentials ─────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "knowledgebase")

# ── Models ──────────────────────────────────────────────────────────────────
CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1-mini")
EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
EMBED_DIM = 1536
EMBED_BATCH = 128

# ── Chunking ────────────────────────────────────────────────────────────────
# Headings do the real splitting; this is only a size guard for long sections.
# 1200 (up from the old fixed 900) because heading-aware sections are
# semantically coherent and the contextual header costs ~80 chars of budget.
MAX_CHUNK_CHARS = 1200
CHUNK_OVERLAP = 150

# pymupdf4llm emits heading levels that are NOT comparable across documents:
# the Data Protection Policy uses '#' for its top-level sections while the
# Section 20 Policy uses '###' for the same thing. Corpus-wide the spread runs
# h1..h5, so all five are registered and the heading *path* is built from
# whichever levels a given document actually uses.
HEADER_LEVELS = [("#", "h1"), ("##", "h2"), ("###", "h3"), ("####", "h4"), ("#####", "h5")]

# Boilerplate removal is an explicit pattern match, not a repetition rule.
# Repetition alone cannot tell boilerplate from templated-but-substantive text:
# the Aster group-entity preamble and the "this policy is monitored after 12
# months" clause are both repeated verbatim across five or more documents, but
# only the first carries no answer value. So we name the thing we mean.
BOILERPLATE_PATTERNS = [
    r"overarching (company )?brand",  # "Aster Group is the overarching brand name of ..."
]
# Guard: a chunk longer than this that merely mentions the preamble is real
# content and is kept, whatever the pattern says.
BOILERPLATE_MAX_CHARS = 800

# Bodies repeated across at least this many distinct documents are *reported*
# as review candidates in the ingest report. Nothing is dropped on this basis.
DUPLICATE_REPORT_MIN_DOCS = 5

# ── Retrieval ───────────────────────────────────────────────────────────────
CANDIDATE_K = 20  # per retriever, before fusion
FINAL_K = 6  # documents handed to the LLM
RRF_DAMPING = 60  # k in the original Reciprocal Rank Fusion paper


def require(name: str, value: str | None) -> str:
    """Fail loudly and by name when a required credential is missing."""
    if not value:
        raise RuntimeError(
            f"{name} is not set. Copy .env.example to .env and fill it in."
        )
    return value
