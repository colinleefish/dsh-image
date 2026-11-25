#!/usr/bin/env bash
# Write a published row into images.json / IMAGES.md and push to main.
set -euo pipefail

: "${SYNC_VERSION:?}"
: "${HUB_DIGEST:?}"
: "${ACR_DIGEST:?}"
: "${GITHUB_SHA:?}"
: "${DOCKERHUB_IMAGE:?}"
: "${ACR_IMAGE:?}"

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "${root}"

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

python3 scripts/dsh_catalog.py record \
  --version "${SYNC_VERSION}" \
  --git "${GITHUB_SHA}" \
  --dockerhub "${HUB_DIGEST}" \
  --acr "${ACR_DIGEST}"

pin="$(grep -E '^DSH_VERSION \?=' Makefile | sed 's/^DSH_VERSION ?= //')"
python3 scripts/dsh_catalog.py assert-pin "${pin}"

git add images.json IMAGES.md Makefile Dockerfile compose.yaml .env.example README.md
if git diff --cached --quiet; then
  printf 'publish record produced no commit\n' >&2
  exit 1
fi

retry() {
  local attempt
  for attempt in 1 2 3 4 5; do
    if "$@"; then
      return 0
    fi
    printf 'command failed (attempt %s)\n' "${attempt}" >&2
    sleep $((attempt * 5))
  done
  return 1
}

git commit -m "Publish dsh-image ${SYNC_VERSION}." \
  -m "Image tags: ${DOCKERHUB_IMAGE}:${SYNC_VERSION} and ${ACR_IMAGE}:${SYNC_VERSION}."
retry git push origin HEAD:main
