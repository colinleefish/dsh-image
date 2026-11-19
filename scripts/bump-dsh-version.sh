#!/usr/bin/env bash
# Bump every repo pin from the current Makefile DSH_VERSION to NEW_VERSION.
set -Eeuo pipefail

new_version="${1:?usage: bump-dsh-version.sh <new-dsh-version>}"

if [[ ! "${new_version}" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
  printf 'refusing implausible version: %s\n' "${new_version}" >&2
  exit 1
fi

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "${root}"

old_version="$(grep -E '^DSH_VERSION \?=' Makefile | sed 's/^DSH_VERSION ?= //')"
if [[ -z "${old_version}" ]]; then
  printf 'could not read current DSH_VERSION from Makefile\n' >&2
  exit 1
fi

if [[ "${old_version}" == "${new_version}" ]]; then
  printf 'already at %s\n' "${new_version}"
  exit 0
fi

replace_in_file() {
  local file="$1"
  if [[ ! -f "${file}" ]]; then
    printf 'missing file: %s\n' "${file}" >&2
    return 1
  fi
  if ! grep -Fq -- "${old_version}" "${file}"; then
    printf 'warn: %s contains no %s (skipped partial replace)\n' "${file}" "${old_version}" >&2
  fi
  sed -i '' "s/${old_version//\./\\.}/${new_version}/g" "${file}" 2>/dev/null \
    || sed -i "s/${old_version//\./\\.}/${new_version}/g" "${file}"
}

replace_in_file Dockerfile
replace_in_file Makefile
replace_in_file .env.example
replace_in_file compose.yaml
if grep -Fq -- "${old_version}" README.md 2>/dev/null; then
  replace_in_file README.md
fi
if grep -Fq -- "${old_version}" MAINTAINERS.md 2>/dev/null; then
  replace_in_file MAINTAINERS.md
fi
# Do not edit .github/workflows/* — GITHUB_TOKEN cannot push workflow file changes.

make version-check
printf 'bumped dsh %s -> %s\n' "${old_version}" "${new_version}"