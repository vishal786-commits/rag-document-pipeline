#!/bin/sh
# Runs the API and the UI in one container. If either dies the container exits,
# so the orchestrator restarts it -- previously uvicorn could die silently and
# leave a "healthy" container serving a broken UI.
set -e

uvicorn main:app --host 0.0.0.0 --port 8000 &
api_pid=$!

streamlit run frontend/app.py \
  --server.address 0.0.0.0 \
  --server.port 8501 \
  --server.headless true \
  --browser.gatherUsageStats false &
ui_pid=$!

# Exit as soon as either process does, carrying its status.
wait -n "$api_pid" "$ui_pid"
status=$?
kill "$api_pid" "$ui_pid" 2>/dev/null || true
exit "$status"
