#!/bin/zsh
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Create the venv first: python3.11 -m venv .venv && .venv/bin/pip install -e ."
  exit 1
fi
.venv/bin/python -m clo_intel run
echo "Review UI: http://127.0.0.1:8000"
exec .venv/bin/python -m clo_intel serve
