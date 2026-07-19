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

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "Node.js 18+ and npm are required for the XHS request-signing runtime." >&2
  exit 1
fi

NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
if [[ "${NODE_MAJOR}" -lt 18 ]]; then
  echo "Node.js 18+ is required. Found: $(node --version)" >&2
  exit 1
fi

"${PY}" - <<'PY'
import sys
if sys.version_info < (3, 9):
    raise SystemExit(f"Python 3.9+ is required. Found: {sys.version}")
print(f"Using Python: {sys.executable}")
PY

cd "${SKILL_DIR}"
"${PY}" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r scripts/requirements-pc.txt
npm ci --prefix scripts --ignore-scripts --no-audit --no-fund

echo "xhs-tool environment is ready."
echo "Next: .venv/bin/python scripts/xhs_auth.py login --verbose --wait-auto"
