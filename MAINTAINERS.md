# 维护说明

面向 fork 本仓库或发布新镜像的维护者。

## 版本怎么理解（对齐上游 deepseek-harness）

上游仓库见 `temp/deepseek-harness`（本地 `git clone`，已 `gitignore`，仅供对照）。

[deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) 的规则（摘自 `scripts/release/families.ts`、`release-publish.yml`）：

| 用途 | 形式 | 示例 |
| --- | --- | --- |
| npm `@deepseek-ai/dsh` | 纯 semver，**无** `v` | `0.2.3-alpha.2` |
| 上游 Git tag | 前缀 `dsh-v` + 同上 semver | `dsh-v0.2.3-alpha.2` |
| 上游 GitHub Release 标题 | 常写成 `v0.2.3-alpha.2` | 实际 tag 仍是 `dsh-v0.2.3-alpha.2` |
| 上游 npm dist-tag | 预发行走 `next` / `alpha`，`latest` 可能落后于 `next` | 不作为镜像跟随依据 |

本镜像 **严格追随 npm 里的 Harness 版本字符串**：

| 用途 | 形式 | 示例 |
| --- | --- | --- |
| 仓库 pin / `DSH_VERSION` | 清单里最高的已发布版本 | `0.2.3-alpha.2` |
| 镜像 tag（ACR / Docker Hub） | 与 npm 相同（**不要**加 `v`） | `0.2.3-alpha.2` |
| 本仓库记录 | [`IMAGES.md`](IMAGES.md) / `images.json` | 最新版本在最前面 |

镜像 tag 不加 `v`，是因为 Harness 的权威版本号在 **npm 与 `package.json` 的 `"version"` 字段**，不是上游 GitHub Release 标题里的 `v…`。`docker pull …:0.2.3-alpha.2` 应与 `npm i @deepseek-ai/dsh@0.2.3-alpha.2` 同一串数字。

本仓库 **不维护 git tag，也不发 GitHub Release**。已发布镜像只记在 `images.json`（机器可读）和 `IMAGES.md`（目录）。

只改 Dockerfile / 脚本、仍打包同一 npm 版本时：定时任务不会重打。要覆盖同一镜像 tag，用 Actions 手动跑 **Publish image**，填 `version` 并打开 `force`。

升级上游 DSH 时：定时任务会把 pin 改成新的最高已发布版本；不要手工打 `dsh-v*` tag。

校验：

```bash
make version-check
```

## 覆盖推送（同一镜像 tag 再发一版）

Registry（Docker Hub / 个人版 ACR）允许同名 tag 覆盖，但 **定时任务不会重打** 已在 `IMAGES.md` 里的版本。

要重打某一版：Actions → Publish image → `version` 填 npm 版本（如 `0.2.3-alpha.2`）→ 打开 `force`。成功后会更新清单里这一行的 digest 和构建 commit，不改 git tag。

本地 `make push` 仍会推当前 pin，可能覆盖 registry 上的同名 tag；清单不会自动改，需要再跑一次上面的手动流程，或直接改 `images.json` 后执行 `python3 scripts/dsh_catalog.py render`。

## 本地构建与冒烟

```bash
cp .env.example .env
make build
make smoke
```

## 自动跟上游 Harness 发版

不跟 npm 的 `latest` / `next`，只认上游仓库 **Git tag `dsh-v*`**。本仓库只有 `main`。

Workflow：`.github/workflows/publish.yml`（一条）。决策在 `scripts/dsh_catalog.py`。

每次运行最多发布一个版本：

1. 每 6 小时（或手动 **workflow_dispatch**）列出上游 `dsh-v*`。
2. 「新」= 比 `images.json` 里已发布的 **最高版本** 更高。
3. 在这些新版本里取 **最低** 的一个；已在清单里的不打；在跳过表里的不打、也不挡住更高版本。
4. 始终 checkout `main`。若目标版本高于当前 pin，先改 pin，再构建。
5. 两个 registry 都已有该 tag 时，只补记清单，不重建。
6. 构建成功后写入 `images.json` / `IMAGES.md`（最新在前）并推到 `main`。失败则写入跳过表，**不**改 pin。

镜像目录是 [IMAGES.md](IMAGES.md)，不是 GitHub Releases。

手动试跑：Actions → Publish image → `dry_run: true`。指定 `version` 可打某一版；已发布的需要同时打开 `force` 才会重打。

若要临时不跟某一类：改 workflow 里的 `TAG_SUFFIX_PATTERN`。

## CI 发布

Workflow：`.github/workflows/publish.yml`

- 定时或 `workflow_dispatch`，始终在 `main` 上构建。
- 推送镜像：`docker.io/colinleefish/dsh-image:<版本>` 与 `registry.cn-beijing.aliyuncs.com/colinleefish/dsh-image:<版本>`。

### 要不要 `latest`？

**建议默认不要推 Docker `latest`。**

上游 npm 在 RC 阶段用 **`next`** 表示最新预发行，**`latest` 刻意可能旧一档**。镜像若也打 `latest`，会与「跟 npm 版本一一对应」冲突，且无法区分你在跟 `next` 还是稳定线。

务实做法：

- 日常：`docker pull …:0.2.3-alpha.2` 与 npm 同版本。
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