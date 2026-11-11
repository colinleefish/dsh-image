# dsh-image

Personal **lean** DeepSeek Harness container image: Web UI + agent shell tools, **no Chromium / noVNC / Browser Use**.

China-first indexes: Debian → `mirrors.aliyun.com`, npm → `registry.npmmirror.com`, pip/uv → `mirrors.aliyun.com/pypi`.

Pinned like [runzhliu/deepseek-harness-docker](https://github.com/runzhliu/deepseek-harness-docker):

| Variable | Meaning | Current |
| --- | --- | --- |
| `DSH_VERSION` | npm `@deepseek-ai/dsh` | `0.2.2-rc.1` |
| `DSH_IMAGE_VERSION` / `IMAGE_VERSION` | immutable image revision | `0.2.2-rc.1-r4` |

Bump `IMAGE_VERSION` (`-r5`, …) for container-only changes. Bump `DSH_VERSION` only when packaging a new upstream npm release, and update every pin together (`make version-check`).

Published tags (same digest family from CI):

- `registry.cn-beijing.aliyuncs.com/colinleefish/dsh-image:<ver>`
- `docker.io/colinleefish/dsh-image:<ver>`

## Tools baked in

`git`, `openssh-client`, `curl`, `jq`, `ripgrep`, `postgresql-client` (`psql`), `python3`, `uv`/`uvx`, `vim-tiny`, `pnpm`, Node 24 (Trixie).

## GitHub Actions secrets

| Secret | Purpose |
| --- | --- |
| `DOCKERHUB_USERNAME` | Docker Hub user (e.g. `colinleefish`) |
| `DOCKERHUB_TOKEN` | Docker Hub access token |
| `ACR_USERNAME` | **旧版个人版**登录名 = 阿里云账号全名（常见为 `colinleefish@aliyun.com`，不是命名空间 `colinleefish`，也不是 AccessKey） |
| `ACR_PASSWORD` | 容器镜像服务 → 访问凭证 里设置的**镜像仓库独立密码**（不是阿里云登录密码，也不是 AK Secret） |

Registry：`registry.cn-beijing.aliyuncs.com`（个人版北京）。不要填企业版 `*.cr.aliyuncs.com` / InstanceId。

Workflow: `.github/workflows/publish.yml` — manual dispatch or tag `image-v0.2.2-rc.1-r4`.

After a successful publish it creates GitHub Release `image-v<IMAGE_VERSION>` with pull commands and attaches `sha256sums.txt` (manifest digests for Hub + ACR). Re-running against an already-pushed tag skips rebuild and only refreshes the Release.

```bash
gh secret set DOCKERHUB_USERNAME -R colinleefish/dsh-image
gh secret set DOCKERHUB_TOKEN -R colinleefish/dsh-image
gh secret set ACR_USERNAME -R colinleefish/dsh-image -b 'colinleefish@aliyun.com'
gh secret set ACR_PASSWORD -R colinleefish/dsh-image
```

## Build

```bash
cp .env.example .env
# pins: DSH_VERSION=0.2.2-rc.1  DSH_IMAGE_VERSION=0.2.2-rc.1-r4
make version-check
make build
make smoke
```

## Run

```bash
mkdir -p data/dot-dsh data/dot-ssh workspace
cp .env.example .env
docker compose up -d
```

Web listens on host `127.0.0.1:3080`. Inside the container DSH binds loopback; `scripts/dsh-web-relay.cjs` publishes the container interface address.

For a Tailscale / nginx front:

```bash
DSH_WEB_EXTRA_ARGS='--public-url http://100.84.0.2:3080 --trusted-host 100.84.0.2:3080'
```

## Agentbox notes

- Postgres for this harness: see the agentbox workspace `AGENTS.md` (DeepSeek Harness only).
- `compose.yaml` sinkholes `rmb.colinleefish.com` to `0.0.0.0`; pair with host `DOCKER-USER` DROP if you also block by IP.
