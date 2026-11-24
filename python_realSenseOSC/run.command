#!/bin/bash
# Quick launcher for macOS (double-click or ./run.command)
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv || exit 1
  .venv/bin/pip install -r requirements.txt || exit 1
fi
exec .venv/bin/python realsense_osc.py "$@"
