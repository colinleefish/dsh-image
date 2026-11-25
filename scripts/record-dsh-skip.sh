#!/usr/bin/env bash
# After a failed image build: restore pin files, record skipped, commit.
set -euo pipefail

: "${SYNC_VERSION:?}"

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "${root}"

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

reason="${1:-build failed}"
git checkout -- Makefile Dockerfile compose.yaml .env.example README.md || true
python3 scripts/dsh_catalog.py skip --version "${SYNC_VERSION}" --reason "${reason}"
git add images.json IMAGES.md
if git diff --cached --quiet; then
  printf 'skip record produced no commit\n' >&2
  exit 0
fi
git commit -m "Skip dsh-image ${SYNC_VERSION}." \
  -m "${reason}"
git push origin HEAD:main
