#!/usr/bin/env bash
# One-time setup for the MERIT fork of sciwrite-lint.
# Run from the repository root:  bash merit/setup.sh
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not installed. Install it with:"
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh && source \$HOME/.local/bin/env"
  exit 1
fi

echo "==> Creating virtual environment (.venv, Python 3.13)"
[ -d .venv ] || uv venv --python 3.13 .venv

echo "==> Installing pinned dependencies (several GB, takes a few minutes)"
uv pip install --python .venv/bin/python -r requirements-pinned.txt
uv pip install --python .venv/bin/python -e . --no-deps

if [ ! -f .env ]; then
  cp .env.example .env
  echo "==> Created .env from .env.example. Put your OpenRouter key in it."
else
  echo "==> .env already exists, left unchanged"
fi

echo "==> Checking install"
.venv/bin/sciwrite-lint --version
.venv/bin/python -c "import bibtexparser; v = bibtexparser.__version__; assert v.startswith('1.'), v; print('bibtexparser', v)"

cat <<'MSG'

Setup done. Next:
  1. Edit .env and paste your OpenRouter API key.
  2. source .venv/bin/activate
  3. Connection test (1 paper, 1 check):
     python merit/score.py consistency --papers c02_percentages.tex --checks percentages-sum
  Full guide: merit/README.md
MSG
