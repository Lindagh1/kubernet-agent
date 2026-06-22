#!/bin/bash
set -euo pipefail

exec streamlit run app.py \
  --server.address=0.0.0.0 \
  --server.port="${PORT:-8080}" \
  --server.headless=true \
  --browser.gatherUsageStats=false
