# syntax=docker/dockerfile:1.7
# Lean DeepSeek Harness image: Web UI + agent CLI tools, no Chromium/noVNC.
# Apt/pip use Aliyun mirrors. @deepseek-ai/dsh installs from the official npm
# registry so native optionalDependencies/prebuilds are intact (npmmirror can
# ship broken linux-x64-gnu addon packages).

ARG NODE_IMAGE=docker.io/library/node:24-trixie
FROM ${NODE_IMAGE}

ARG DSH_VERSION=0.2.2-rc.1
ARG PNPM_VERSION=10.15.1
ARG UV_VERSION=0.9.7
ARG NPM_REGISTRY=https://registry.npmmirror.com
ARG NPM_DSH_REGISTRY=https://registry.npmjs.org
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG TARGETARCH

# Debian 13 (trixie) DEB822 sources → Aliyun
RUN sed -i \
      -e 's|https\?://deb.debian.org|https://mirrors.aliyun.com|g' \
      -e 's|https\?://security.debian.org|https://mirrors.aliyun.com/debian-security|g' \
      /etc/apt/sources.list.d/debian.sources \
 && apt-get update \
 && apt-get install --yes --no-install-recommends \
    build-essential \
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
    python3-pip \
    ripgrep \
    rsync \
    tini \
    unzip \
    vim-tiny \
    wget \
    zip \
 && rm -rf /var/lib/apt/lists/*

# uv from Aliyun PyPI (avoids GitHub release downloads inside China).
RUN PIP_INDEX_URL="${PIP_INDEX_URL}" \
    PIP_TRUSTED_HOST=mirrors.aliyun.com \
    pip3 install --break-system-packages --no-cache-dir "uv==${UV_VERSION}" \
 && uv --version

# pnpm can come from the China npm mirror; dsh itself must use registry.npmjs.org.
RUN npm install --global --omit=dev --no-audit --no-fund \
      --registry="${NPM_REGISTRY}" \
      "pnpm@${PNPM_VERSION}" \
 && npm install --global --omit=dev --no-audit --no-fund \
      --registry="${NPM_DSH_REGISTRY}" \
      --allow-scripts=@deepseek-ai/dsh-subprocess-local,koffi,node-pty,@google/genai,protobufjs \
      "@deepseek-ai/dsh@${DSH_VERSION}" \
 && test "$(node /usr/local/lib/node_modules/@deepseek-ai/dsh/lib/bin.js --version)" = "${DSH_VERSION}" \
 && test "$(pnpm --version)" = "${PNPM_VERSION}" \
 && test -e /usr/local/lib/node_modules/@deepseek-ai/dsh/node_modules/node-addon-require-builtin-linux-x64-gnu \
 && npm cache clean --force

COPY scripts/dsh-web-relay.cjs /opt/dsh-image/dsh-web-relay.cjs
COPY scripts/dsh /usr/local/bin/dsh
COPY scripts/entrypoint.sh /usr/local/bin/dsh-image-entrypoint
RUN chmod 0755 /usr/local/bin/dsh /usr/local/bin/dsh-image-entrypoint \
 && dsh --version | grep -Fx "${DSH_VERSION}"

ENV DSH_HOME=/home/node/.dsh \
    DSH_TELEMETRY_DISABLED=1 \
    HOME=/workspace \
    NPM_CONFIG_CACHE=/home/node/.dsh/npm-cache \
    NPM_CONFIG_REGISTRY=${NPM_REGISTRY} \
    PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_TRUSTED_HOST=mirrors.aliyun.com \
    UV_INDEX_URL=${PIP_INDEX_URL} \
    NARB_DISABLE_NATIVE_CACHE=1

RUN mkdir -p "${DSH_HOME}" /workspace \
 && chown -R node:node "${DSH_HOME}" /workspace

USER node
WORKDIR /workspace

EXPOSE 3080

ARG IMAGE_VERSION=0.2.2-rc.1-r5
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
