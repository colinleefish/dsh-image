#!/usr/bin/env bash
# If both registries already have VERSION, write digests to GITHUB_OUTPUT.
set -euo pipefail

: "${SYNC_VERSION:?}"
: "${DOCKERHUB_IMAGE:?}"
: "${ACR_IMAGE:?}"
: "${GITHUB_OUTPUT:?}"

digest_of() {
  docker buildx imagetools inspect "$1" | awk '/^Digest:/{print $2; exit}'
}

hub_digest="$(digest_of "${DOCKERHUB_IMAGE}:${SYNC_VERSION}" || true)"
acr_digest="$(digest_of "${ACR_IMAGE}:${SYNC_VERSION}" || true)"
if [[ -n "${hub_digest}" && -n "${acr_digest}" ]]; then
  {
    echo "found=true"
    echo "hub_digest=${hub_digest}"
    echo "acr_digest=${acr_digest}"
  } >>"${GITHUB_OUTPUT}"
  printf 'both registries already have %s\n' "${SYNC_VERSION}"
else
  echo "found=false" >>"${GITHUB_OUTPUT}"
  printf 'missing image %s (hub=%s acr=%s)\n' \
    "${SYNC_VERSION}" "${hub_digest:-empty}" "${acr_digest:-empty}"
fi
