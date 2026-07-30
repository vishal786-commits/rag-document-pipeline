FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUTF8=1

COPY requirements.txt .
RUN pip install -r requirements.txt

# Run as a non-root user.
RUN useradd --create-home --uid 10001 appuser

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

COPY main.py .
COPY rag/ ./rag/
COPY frontend/ ./frontend/

# Required, not optional: BM25 is built from this snapshot at startup and the
# service comes up degraded without it. The PDFs themselves are never read at
# runtime, so knowledge_base/ is deliberately not copied.
COPY data/kb_chunks.jsonl data/kb_chunks.meta.json ./data/

USER appuser

EXPOSE 8000 8501

ENTRYPOINT ["/docker-entrypoint.sh"]
