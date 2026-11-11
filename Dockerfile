# syntax=docker/dockerfile:1.7
# Lean DeepSeek Harness image: Web UI + agent CLI tools, no Chromium/noVNC.

ARG NODE_IMAGE=docker.io/library/node:24-trixie
FROM ${NODE_IMAGE}

ARG DSH_VERSION=0.2.2-rc.1
ARG PNPM_VERSION=10.15.1
ARG UV_VERSION=0.9.7
ARG TARGETARCH

RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
 && apt-get update \
 && apt-get install --yes --no-install-recommends \
    ca-certificates \
    curl \
    file \
    git \
    jq \
    less \
    openssh-client \
    postgresql-client \
    procps \
    python3 \
    ripgrep \
    rsync \
    tini \
    unzip \
    vim-tiny \
    wget \
    zip \
 && rm -rf /var/lib/apt/lists/*

# uv (static binary) for Python tooling inside the agent workspace.
RUN set -eux; \
  case "${TARGETARCH}" in \
    amd64) uv_arch=x86_64 ;; \
    arm64) uv_arch=aarch64 ;; \
    *) echo "unsupported arch: ${TARGETARCH}" >&2; exit 1 ;; \
  esac; \
  curl --fail --location --retry 3 \
    -o /tmp/uv.tar.gz \
    "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${uv_arch}-unknown-linux-gnu.tar.gz"; \
  tar -xzf /tmp/uv.tar.gz -C /tmp; \
  install -m 0755 "/tmp/uv-${uv_arch}-unknown-linux-gnu/uv" /usr/local/bin/uv; \
  install -m 0755 "/tmp/uv-${uv_arch}-unknown-linux-gnu/uvx" /usr/local/bin/uvx; \
  rm -rf /tmp/uv.tar.gz "/tmp/uv-${uv_arch}-unknown-linux-gnu"; \
  uv --version

RUN npm install --global --omit=dev --no-audit --no-fund \
      --allow-scripts=@deepseek-ai/dsh-subprocess-local,koffi,node-pty,@google/genai,protobufjs \
      "@deepseek-ai/dsh@${DSH_VERSION}" \
      "pnpm@${PNPM_VERSION}" \
 && test "$(dsh --version)" = "${DSH_VERSION}" \
 && test "$(pnpm --version)" = "${PNPM_VERSION}" \
 && npm cache clean --force

COPY scripts/dsh-web-relay.cjs /opt/dsh-image/dsh-web-relay.cjs
COPY scripts/entrypoint.sh /usr/local/bin/dsh-image-entrypoint
RUN chmod 0755 /usr/local/bin/dsh-image-entrypoint

ENV DSH_HOME=/home/node/.dsh \
    DSH_TELEMETRY_DISABLED=1 \
    HOME=/workspace \
    NPM_CONFIG_CACHE=/home/node/.dsh/npm-cache

RUN mkdir -p "${DSH_HOME}" /workspace \
 && chown -R node:node "${DSH_HOME}" /workspace

USER node
WORKDIR /workspace

EXPOSE 3080

ARG IMAGE_VERSION=0.2.2-rc.1-r1
ARG IMAGE_REVISION=unknown
LABEL org.opencontainers.image.title="colinleefish/dsh-image" \
      org.opencontainers.image.description="Lean DeepSeek Harness image without Chromium" \
      org.opencontainers.image.source="https://github.com/colinleefish/dsh-image" \
      org.opencontainers.image.url="https://github.com/colinleefish/dsh-image" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="${IMAGE_VERSION}" \
      org.opencontainers.image.revision="${IMAGE_REVISION}" \
      io.github.colinleefish.dsh.upstream.npm="@deepseek-ai/dsh@${DSH_VERSION}"

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/dsh-image-entrypoint"]
CMD ["--profile", "web", "--no-open", "--port", "3080"]
