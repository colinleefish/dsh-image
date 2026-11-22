# 维护说明

面向 fork 本仓库或发布新镜像的维护者。

## 版本怎么理解（对齐上游 deepseek-harness）

上游仓库见 `temp/deepseek-harness`（本地 `git clone`，已 `gitignore`，仅供对照）。

[deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) 的规则（摘自 `scripts/release/families.ts`、`release-publish.yml`）：

| 用途 | 形式 | 示例 |
| --- | --- | --- |
| npm `@deepseek-ai/dsh` | 纯 semver，**无** `v` | `0.2.3-alpha.1` |
| 上游 Git tag | 前缀 `dsh-v` + 同上 semver | `dsh-v0.2.3-alpha.1` |
| 上游 GitHub Release 标题 | 常写成 `v0.2.3-alpha.1` | 实际 tag 仍是 `dsh-v0.2.3-alpha.1` |
| 上游 npm dist-tag | 预发行走 `next` / `alpha`，`latest` 可能落后于 `next` | 当前 `next`→`0.2.3-alpha.1`，`latest`→`0.2.2-rc.1` |

本镜像 **严格追随 npm 里的 Harness 版本字符串**：

| 用途 | 形式 | 示例 |
| --- | --- | --- |
| 仓库 pin / `DSH_VERSION` | 与 npm 相同 | `0.2.3-alpha.1` |
| 镜像 tag（ACR / Docker Hub） | 与 npm 相同（**不要**加 `v`） | `0.2.3-alpha.1` |
| 本仓库 Git tag / Release | 与上游一致 | `dsh-v0.2.3-alpha.1` |

镜像 tag 不加 `v`，是因为 Harness 的权威版本号在 **npm 与 `package.json` 的 `"version"` 字段**，不是 GitHub Release 标题里的 `v…`。Git 上的 `dsh-v` / Release 标题里的 `v` 只是发布标记；`docker pull …:0.2.3-alpha.1` 应与 `npm i @deepseek-ai/dsh@0.2.3-alpha.1` 同一串数字。

不再使用 `-r1`、`-r2`，也不再使用本仓库私有的 `image-v…` 双 tag 体系。

只改 Dockerfile / 脚本、仍打包同一 npm 版本时：**保持 `DSH_VERSION` 不变**，修完后对**同一个** Git tag 与镜像 tag 重新发布（见下文覆盖推送）。

升级上游 DSH 时：改全仓 pin 为新的 `DSH_VERSION`，打新的 `v<新版本>`。

校验：

```bash
make version-check
```

## 覆盖推送（同一 tag 再发一版）

Registry（Docker Hub / 个人版 ACR）已配置为**允许同名 tag 覆盖**时：

- CI 每次运行都会 **build + push**，不会跳过。
- 本地 `make push` 同样不再检测 tag 是否已存在。

Git 侧若要重跑 Actions 触发同一 Harness 版本：

```bash
git tag -d dsh-v0.2.3-alpha.1
git push origin :refs/tags/dsh-v0.2.3-alpha.1
git tag -a dsh-v0.2.3-alpha.1 -m "dsh-image 0.2.3-alpha.1"
git push origin dsh-v0.2.3-alpha.1
```

或直接用 Actions **workflow_dispatch**（使用 `publish.yml` 里 env 的 `DSH_VERSION`）。

Release 与 `sha256sums.txt` 会按同一 Git tag **更新**，不另起 tag。

## 本地构建与冒烟

```bash
cp .env.example .env
make build
make smoke
```

## 自动跟上游 Harness 发版（可选）

不跟 npm 的 `latest` / `next`，只认上游仓库 **Git tag `dsh-v*`**（与 `release-publish.yml` 一致）。

Workflow：`.github/workflows/sync-upstream.yml`

1. 每 6 小时（或手动 **workflow_dispatch**）用 GitHub API 拉 `deepseek-ai/deepseek-harness` 的 `dsh-v*` 列表。
2. 默认**全跟**上游所有 `dsh-v*`（含 alpha/rc）；仅跳过本仓库已有的 tag。`TAG_SUFFIX_PATTERN` 只做 sanity check（标准 semver 形），不是用来锁死在 0.2.2 线。
3. 每次运行最多处理**一个**缺失版本：在「尚未同步」的 tag 里取 **semver 最高** 的那条，避免一次 commit 跳过多版。
4. bump → commit → `dsh-v<版本>` → **`publish.yml` 自动构建** 镜像 `…:<版本>`。

手动试跑：Actions → Sync upstream dsh release → `dry_run: true`；或 `version: 0.2.3-alpha.1` 强制某一版。

若要临时不跟某一类（极少需要）：再改 workflow 里的 `TAG_SUFFIX_PATTERN` 或给 workflow 加 exclude 列表。

若仓库在 GitLab：同样逻辑放在 scheduled pipeline + `rules: if: $CI_COMMIT_TAG =~ /^dsh-v/` 即可；本仓库当前是 **GitHub Actions**。

## CI 发布

Workflow：`.github/workflows/publish.yml`

- 推送 **`dsh-v<DSH_VERSION>`**（如 `dsh-v0.2.3-alpha.1`）触发构建；或 workflow_dispatch。
- 推送镜像：`docker.io/colinleefish/dsh-image:<DSH_VERSION>` 与 `registry.cn-beijing.aliyuncs.com/colinleefish/dsh-image:<DSH_VERSION>`。

### 要不要 `latest`？

**建议默认不要推 Docker `latest`。**

上游 npm 在 RC 阶段用 **`next`** 表示最新预发行，**`latest` 刻意可能旧一档**（例如 `next`→`0.2.3-alpha.1` 而 `latest` 仍停在 `0.2.2-rc.1`）。镜像若也打 `latest`，会与「跟 npm 版本一一对应」冲突，且无法区分你在跟 `next` 还是稳定线。

务实做法：

- 日常：`docker pull …:0.2.3-alpha.1` 与 npm 同版本。
- 若你希望「始终等于仓库当前 pin」：在 compose 里写死 `DSH_IMAGE_VERSION`，升级时改 pin + 重拉，而不是依赖 `latest`。
- 以后若稳定版 `0.2.x` 出洞且只维护一条推荐线，可**额外**推 `latest` 指向该稳定 semver；RC 阶段若要滚动跟踪，可考虑模仿上游推别名 **`next`**（指向当前 `DSH_VERSION`），仍不推荐 `latest`。

### GitHub Actions secrets

| Secret | 用途 |
| --- | --- |
| `DOCKERHUB_USERNAME` | Docker Hub 用户名 |
| `DOCKERHUB_TOKEN` | Docker Hub access token |
| `ACR_USERNAME` | **个人版 ACR** 登录名 = 阿里云账号全名（如 `colinleefish@aliyun.com`），不是命名空间名，也不是 AccessKey |
| `ACR_PASSWORD` | 容器镜像服务 → 访问凭证中的**镜像仓库独立密码** |

Registry 使用 `registry.cn-beijing.aliyuncs.com`（个人版北京），不要填企业版 `*.cr.aliyuncs.com`。

```bash
gh secret set DOCKERHUB_USERNAME -R colinleefish/dsh-image
gh secret set DOCKERHUB_TOKEN -R colinleefish/dsh-image
gh secret set ACR_USERNAME -R colinleefish/dsh-image -b 'colinleefish@aliyun.com'
gh secret set ACR_PASSWORD -R colinleefish/dsh-image
```

## 实现备忘

- 持久化：compose 只挂 `./data/home:/home/node`（`HOME=/home/node`，`WORKDIR=/home/node/workspace`，`DSH_HOME=/home/node/.dsh`）。勿再使用 `HOME=/workspace` 双卷布局。
- pnpm：`XDG_CONFIG_HOME=/home/node/.config`，`store-dir` 在镜像内写入 `pnpm/rc`，空卷首次启动时由 `entrypoint.sh` 补写；store 在 `${DSH_HOME}/pnpm-store`。
- 从旧布局迁移：把原 `data/dot-dsh` 挪到 `data/home/.dsh`，原 `data/workspace` 挪到 `data/home/workspace`，删掉 compose 里分卷挂载。
- Web 对外：`scripts/dsh-web-relay.cjs` 在容器内把回环上的 DSH Web 转到容器网络接口。
- 全局 `dsh` 可执行文件为 wrapper（`scripts/dsh`），避免在只读根文件系统下从 `noexec` 的 `/tmp` 加载 native addon。
- `@deepseek-ai/dsh` 必须从 `registry.npmjs.org` 安装；其它 npm 包可走 `registry.npmmirror.com`。