#!/bin/zsh
# Start the Northbridge CLO desk on this Mac.
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Create the venv first: python3.11 -m venv .venv && .venv/bin/pip install -e ."
  exit 1
fi
echo "Credit desk: http://127.0.0.1:8000"
exec .venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
