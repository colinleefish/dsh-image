# 维护说明

面向 fork 本仓库或发布新镜像的维护者。

## 版本怎么理解（对齐上游 deepseek-harness）

上游仓库见 `temp/deepseek-harness`（本地 `git clone`，已 `gitignore`，仅供对照）。

[deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) 的规则（摘自 `scripts/release/families.ts`、`release-publish.yml`）：

| 用途 | 形式 | 示例 |
| --- | --- | --- |
| npm `@deepseek-ai/dsh` | 纯 semver，**无** `v` | `0.2.2-alpha.3` |
| 上游 Git tag | 前缀 `dsh-v` + 同上 semver | `dsh-v0.2.2-alpha.3` |
| 上游 GitHub Release 标题 | 常写成 `v0.2.2-alpha.3` | 实际 tag 仍是 `dsh-v0.2.2-alpha.3` |
| 上游 npm dist-tag | 预发行走 `next` / `alpha`，`latest` 可能落后于 `next` | 不作为镜像跟随依据 |

本镜像 **严格追随 npm 里的 Harness 版本字符串**：

| 用途 | 形式 | 示例 |
| --- | --- | --- |
| 仓库 pin / `DSH_VERSION` | 与 npm 相同 | `0.2.2-alpha.3` |
| 镜像 tag（ACR / Docker Hub） | 与 npm 相同（**不要**加 `v`） | `0.2.2-alpha.3` |
| 本仓库 Git tag / Release | 与上游一致 | `dsh-v0.2.2-alpha.3` |

镜像 tag 不加 `v`，是因为 Harness 的权威版本号在 **npm 与 `package.json` 的 `"version"` 字段**，不是 GitHub Release 标题里的 `v…`。Git 上的 `dsh-v` / Release 标题里的 `v` 只是发布标记；`docker pull …:0.2.2-alpha.3` 应与 `npm i @deepseek-ai/dsh@0.2.2-alpha.3` 同一串数字。

不再使用 `-r1`、`-r2`，也不再使用本仓库私有的 `image-v…` 双 tag 体系。

只改 Dockerfile / 脚本、仍打包同一 npm 版本时：**保持 `DSH_VERSION` 不变**，修完后对**同一个** Git tag 与镜像 tag 重新发布（见下文覆盖推送）。

升级上游 DSH 时：改全仓 pin 为新的 `DSH_VERSION`，打新的 `dsh-v<新版本>`。

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
git tag -d dsh-v0.2.2-alpha.3
git push origin :refs/tags/dsh-v0.2.2-alpha.3
git tag -a dsh-v0.2.2-alpha.3 -m "dsh-image 0.2.2-alpha.3"
git push origin dsh-v0.2.2-alpha.3
```

或直接用 Actions **workflow_dispatch**（使用 `publish.yml` 里 env 的 `DSH_VERSION`）。

Release 与 `sha256sums.txt` 会按同一 Git tag **更新**，不另起 tag。

## 本地构建与冒烟

```bash
cp .env.example .env
make build
make smoke
```

## 自动跟上游 Harness 发版

不跟 npm 的 `latest` / `next`，只认上游仓库 **Git tag `dsh-v*`**（与 `release-publish.yml` 一致）。

Workflow：`.github/workflows/sync-upstream.yml`。决策在 `scripts/plan_dsh_sync.py`，执行在 `scripts/apply-dsh-sync.sh`。

每次运行只做一件事，按这个顺序挑：

1. 每 6 小时（或手动 **workflow_dispatch**）用 GitHub API 列出上游 `dsh-v*`。`TAG_SUFFIX_PATTERN` 只检查版本是 semver（含 alpha/rc），不把跟随范围锁在某一条小版本上。
2. 当前最高版本 = `main` 上的 `DSH_VERSION` 与本仓库已有 `dsh-v*` tag 里，semver 更高的那个。
3. 上游有更高版本时，取其中**最低**的一个，把 pin 提交到 `main`，打 tag，再触发 `publish.yml`。`main` 只往更高版本走。
4. `main` 的 pin 低于当前最高版本时，把 pin 提交到那个最高版本。已有 tag 留在原来的提交上。
5. `main` 这一版还没有 tag，或 tag 在但 GitHub Release 还没有时，补打 tag 和/或再次触发 `publish.yml`。pin 已经一致、文件没有改动，也会做这一步。
6. 其他 tag 已经在、Release 还没有时，再次触发 `publish.yml`。该版本在最近 12 小时内发布失败的，本轮跳过，继续做下一件事。
7. 比当前最高版本旧、且本仓库还没有的 tag：从当前 `main` 的打包文件做一份临时提交，只改 pin，推 tag，不推 `main`，然后触发 `publish.yml`。一次补这些旧版本里最高的一个。

镜像有没有发布，看这个 tag 的 GitHub Release 在不在。`publish.yml` 在两个 registry 都推完之后才创建 Release。

手动试跑：Actions → Sync upstream dsh release → `dry_run: true`。`version` 填一个上游已有版本时，比 `main` 新的提交到 `main`；比 `main` 旧的只打 tag，不移动 `main`。

tag 推送和 `workflow_dispatch` 会重试几次。`GITHUB_TOKEN` 推上去的 tag 不会触发其他 workflow，所以同步任务自己启动 `publish.yml`。

若要临时不跟某一类：改 workflow 里的 `TAG_SUFFIX_PATTERN`，或给 workflow 加 exclude 列表。

## CI 发布

Workflow：`.github/workflows/publish.yml`

- 推送 **`dsh-v<DSH_VERSION>`**（如 `dsh-v0.2.2-alpha.3`）触发构建；或 workflow_dispatch。
- 推送镜像：`docker.io/colinleefish/dsh-image:<DSH_VERSION>` 与 `registry.cn-beijing.aliyuncs.com/colinleefish/dsh-image:<DSH_VERSION>`。

### 要不要 `latest`？

**建议默认不要推 Docker `latest`。**

上游 npm 在 RC 阶段用 **`next`** 表示最新预发行，**`latest` 刻意可能旧一档**。镜像若也打 `latest`，会与「跟 npm 版本一一对应」冲突，且无法区分你在跟 `next` 还是稳定线。

务实做法：

- 日常：`docker pull …:0.2.2-alpha.3` 与 npm 同版本。
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