FROM python:3.9-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    API_URL=http://127.0.0.1:8000

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

COPY main.py .
COPY src/ ./src/
COPY frontend/ ./frontend/

RUN mkdir -p uploaded_pdfs

EXPOSE 8000 8501

ENTRYPOINT ["/docker-entrypoint.sh"]