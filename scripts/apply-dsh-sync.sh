#!/usr/bin/env bash
# Apply one plan from scripts/plan_dsh_sync.py.
# commit_mode=main moves main forward. commit_mode=detached tags a side commit.
set -euo pipefail

: "${SYNC_ACTION:?}"
: "${SYNC_VERSION:?}"
: "${SYNC_COMMIT_MODE:?}"
: "${SYNC_CREATE_TAG:?}"
: "${SYNC_DISPATCH_PUBLISH:?}"
: "${UPSTREAM_REPO:?}"

if [[ "${SYNC_COMMIT_MODE}" != "main" && "${SYNC_COMMIT_MODE}" != "detached" && "${SYNC_COMMIT_MODE}" != "none" ]]; then
  printf 'unknown commit_mode: %s\n' "${SYNC_COMMIT_MODE}" >&2
  exit 1
fi
if [[ "${SYNC_CREATE_TAG}" != "true" && "${SYNC_CREATE_TAG}" != "false" ]]; then
  printf 'SYNC_CREATE_TAG must be true or false\n' >&2
  exit 1
fi
if [[ "${SYNC_DISPATCH_PUBLISH}" != "true" && "${SYNC_DISPATCH_PUBLISH}" != "false" ]]; then
  printf 'SYNC_DISPATCH_PUBLISH must be true or false\n' >&2
  exit 1
fi

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "${root}"

branch="$(git symbolic-ref --short HEAD 2>/dev/null || true)"
if [[ "${branch}" != "main" ]]; then
  printf 'sync must start on main\n' >&2
  exit 1
fi
if ! git diff --quiet || ! git diff --cached --quiet; then
  printf 'working tree is dirty\n' >&2
  exit 1
fi

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

return_branch=""
cleanup() {
  if [[ -n "${return_branch}" ]]; then
    git checkout -f "${return_branch}" >/dev/null 2>&1 || true
    return_branch=""
  fi
}
trap cleanup EXIT

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

printf 'apply %s version=%s commit_mode=%s create_tag=%s dispatch=%s\n' \
  "${SYNC_ACTION}" "${SYNC_VERSION}" "${SYNC_COMMIT_MODE}" \
  "${SYNC_CREATE_TAG}" "${SYNC_DISPATCH_PUBLISH}"

if [[ "${SYNC_COMMIT_MODE}" == "detached" ]]; then
  return_branch="$(git symbolic-ref --short HEAD)"
  git checkout --detach
fi

if [[ "${SYNC_COMMIT_MODE}" != "none" ]]; then
  chmod +x scripts/bump-dsh-version.sh
  ./scripts/bump-dsh-version.sh "${SYNC_VERSION}"
  if git diff --quiet && git diff --cached --quiet; then
    printf 'bump produced no diff for %s\n' "${SYNC_VERSION}" >&2
    exit 1
  fi
  git add -A
  case "${SYNC_ACTION}" in
    advance)
      git commit -m "Bump @deepseek-ai/dsh to ${SYNC_VERSION} (upstream dsh-v${SYNC_VERSION})." \
        -m "Automated sync from ${UPSTREAM_REPO}."
      ;;
    repair-main)
      git commit -m "Move main pin forward to ${SYNC_VERSION}." \
        -m "main had fallen behind dsh-v${SYNC_VERSION}. The existing tag stays put."
      ;;
    backfill)
      git commit -m "Backfill @deepseek-ai/dsh ${SYNC_VERSION} without moving main." \
        -m "Automated sync from ${UPSTREAM_REPO}."
      ;;
    *)
      printf 'refusing to commit for action %s\n' "${SYNC_ACTION}" >&2
      exit 1
      ;;
  esac
  if [[ "${SYNC_COMMIT_MODE}" == "main" ]]; then
    retry git push origin HEAD:main
  fi
fi

git_tag="dsh-v${SYNC_VERSION}"
if [[ "${SYNC_CREATE_TAG}" == "true" ]]; then
  if git rev-parse -q --verify "refs/tags/${git_tag}" >/dev/null; then
    printf 'tag %s already exists\n' "${git_tag}"
  else
    git tag -a "${git_tag}" -m "dsh-image ${SYNC_VERSION} (upstream dsh-v${SYNC_VERSION})"
  fi
  retry git push origin "refs/tags/${git_tag}"
fi

if [[ -n "${return_branch}" ]]; then
  git checkout "${return_branch}"
  return_branch=""
fi

if [[ "${SYNC_DISPATCH_PUBLISH}" == "true" ]]; then
  # GITHUB_TOKEN tag pushes do not trigger other workflows.
  retry gh workflow run publish.yml --ref "${git_tag}"
fi
