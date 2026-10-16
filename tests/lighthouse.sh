#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

# Detect Node package runner (pnpm, npx, or bunx)
if command -v pnpm &> /dev/null; then
  RUNNER="pnpm dlx"
elif command -v npx &> /dev/null; then
  RUNNER="npx"
elif command -v bunx &> /dev/null; then
  RUNNER="bunx"
else
  echo "Error: Neither pnpm, npx, nor bunx is installed. Please install Node.js/pnpm."
  exit 1
fi

# Check if site is already running on port 5000
SERVER_PID=""
if ! curl -s -f http://127.0.0.1:5000/ > /dev/null 2>&1; then
  echo "Starting local server on http://127.0.0.1:5000 for audit..."
  if [ -f ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
  else
    PYTHON_BIN="python3"
  fi
  $PYTHON_BIN server.py > /dev/null 2>&1 &
  SERVER_PID=$!
  trap 'if [ -n "$SERVER_PID" ]; then echo "Stopping background server..."; kill "$SERVER_PID" 2>/dev/null || true; fi' EXIT INT TERM

  for i in $(seq 1 20); do
    if curl -s -f http://127.0.0.1:5000/ > /dev/null 2>&1; then
      break
    fi
    sleep 0.5
  done
fi

echo "Running Lighthouse CI audit..."
$RUNNER @lhci/cli autorun "$@"

if [[ "$*" == *"--open"* ]]; then
  $RUNNER @lhci/cli open
fi
