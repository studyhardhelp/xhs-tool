#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -n "${PYTHON_BIN:-}" ]]; then
  PY="${PYTHON_BIN}"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
elif command -v python >/dev/null 2>&1; then
  PY="python"
else
  echo "Python 3 is required, but neither python3 nor python was found." >&2
  exit 1
fi

"${PY}" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit(f"Python 3.10+ is required. Found: {sys.version}")
print(f"Using Python: {sys.executable}")
PY

cd "${SKILL_DIR}"
"${PY}" -m venv .venv
.venv/bin/pip install -r scripts/requirements-pc.txt
npm install --prefix scripts

echo "xhs-report environment is ready."
echo "Next: .venv/bin/python scripts/xhs_auth.py login --verbose --wait-auto"
