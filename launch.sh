#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$(readlink -f -- "$0")")"
if [[ "${1:-}" == --rollback ]]; then
  /usr/bin/python -c 'from updater import rollback_installation; from pathlib import Path; rollback_installation(Path.cwd())'
  shift
fi
exec /usr/bin/python app.py "$@"
