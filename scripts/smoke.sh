#!/usr/bin/env bash
set -Eeuo pipefail

image="${1:?missing image ref}"
dsh_version="${2:?missing DSH version}"
name="dsh-image-smoke-$$"

cleanup() {
  docker rm -f "${name}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker run -d --name "${name}" \
  -p 127.0.0.1:13080:3080 \
  "${image}" >/dev/null

ok=0
for _ in $(seq 1 40); do
  code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:13080/" || true)"
  # Unconfigured install may 401 or redirect; connection + HTTP response is enough.
  if [[ "${code}" =~ ^(200|301|302|401|403)$ ]]; then
    ok=1
    break
  fi
  sleep 2
done

docker exec "${name}" sh -lc "
  set -e
  test \"\$(dsh --version)\" = '${dsh_version}'
  command -v psql >/dev/null
  command -v uv >/dev/null
  command -v rg >/dev/null
  command -v git >/dev/null
  command -v jq >/dev/null
  command -v vim.tiny >/dev/null || command -v vim >/dev/null
  # No Chromium in this image.
  if command -v chromium >/dev/null 2>&1 || command -v google-chrome >/dev/null 2>&1; then
    echo 'unexpected browser binary present' >&2
    exit 1
  fi
"

if [[ "${ok}" -ne 1 ]]; then
  echo "smoke: web UI did not respond on :13080" >&2
  docker logs "${name}" >&2 || true
  exit 1
fi

echo "smoke ok: ${image} (dsh ${dsh_version}, http ${code})"
