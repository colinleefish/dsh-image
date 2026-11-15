#!/usr/bin/env bash
set -Eeuo pipefail

dsh_version="${1:?missing DSH version}"
pnpm_version="${2:?missing pnpm version}"
uv_version="${3:?missing uv version}"
image_version="${dsh_version}"

require_literal() {
  local file="$1"
  local literal="$2"
  if ! grep -F --quiet -- "${literal}" "${file}"; then
    printf 'version consistency check failed: %s does not contain %s\n' "${file}" "${literal}" >&2
    return 1
  fi
}

require_literal Dockerfile "ARG DSH_VERSION=${dsh_version}"
require_literal Dockerfile "ARG IMAGE_VERSION=${image_version}"
require_literal Dockerfile "ARG PNPM_VERSION=${pnpm_version}"
require_literal Dockerfile "ARG UV_VERSION=${uv_version}"
require_literal Dockerfile "ARG NODE_IMAGE=docker.io/library/node:24-trixie"
require_literal Dockerfile "ARG NPM_REGISTRY=https://registry.npmmirror.com"
require_literal Dockerfile "ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/"
require_literal Dockerfile "mirrors.aliyun.com"
require_literal Dockerfile "\"@deepseek-ai/dsh@\${DSH_VERSION}\""
require_literal .env.example "DSH_IMAGE_VERSION=${image_version}"
require_literal .env.example "registry.cn-beijing.aliyuncs.com/colinleefish"
require_literal compose.yaml "DSH_IMAGE_VERSION:-${image_version}"
require_literal compose.yaml 'DSH_IMAGE_REPOSITORY:-registry.cn-beijing.aliyuncs.com/colinleefish/dsh-image'
require_literal README.md "github.com/colinleefish/dsh-image/releases"
require_literal README.md ".env.example"
require_literal Makefile "DSH_VERSION ?= ${dsh_version}"
require_literal Makefile "IMAGE_VERSION ?= \$(DSH_VERSION)"
require_literal Makefile "PNPM_VERSION ?= ${pnpm_version}"
require_literal Makefile "UV_VERSION ?= ${uv_version}"
require_literal .github/workflows/publish.yml "DSH_VERSION: ${dsh_version}"
require_literal .github/workflows/publish.yml "PNPM_VERSION: ${pnpm_version}"
require_literal .github/workflows/publish.yml "UV_VERSION: ${uv_version}"
require_literal .github/workflows/publish.yml "docker.io/colinleefish/dsh-image"
require_literal .github/workflows/publish.yml "registry.cn-beijing.aliyuncs.com/colinleefish/dsh-image"

require_literal Dockerfile "ARG NPM_DSH_REGISTRY=https://registry.npmjs.org"

require_literal Dockerfile "XDG_CONFIG_HOME=/home/node/.config"
require_literal Dockerfile "store-dir="
require_literal Dockerfile "pnpm-store"
require_literal Dockerfile "NARB_DISABLE_NATIVE_CACHE=1"

require_literal Dockerfile "COPY scripts/dsh /opt/dsh-image/dsh"
require_literal Dockerfile "rm -f /usr/local/bin/dsh"

printf 'version consistency ok: dsh=%s image=%s pnpm=%s uv=%s\n' \
  "${dsh_version}" "${image_version}" "${pnpm_version}" "${uv_version}"