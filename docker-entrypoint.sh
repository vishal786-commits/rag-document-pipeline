#!/bin/sh
set -e
uvicorn main:app --host 0.0.0.0 --port 8000 &
exec streamlit run frontend/app.py \
  --server.address 0.0.0.0 \
  --server.port 8501 \
  --server.headless true \
  --browser.gatherUsageStats false