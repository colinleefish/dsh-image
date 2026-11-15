# dsh-image

在 Docker 里跑 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)（`@deepseek-ai/dsh`）的**瘦镜像**：Web 控制台 + 常用命令行工具，**不带 Chromium / noVNC / Browser Use**。

适合在本机或一台 Linux 服务器上长期起一份 DSH，数据落在挂载目录里，升级时换掉镜像 tag 即可。

版本号与上游 npm `@deepseek-ai/dsh`、镜像 tag 一致（形如 `0.2.2-rc.3`）；Git 发布 tag 为 `dsh-v` + 同一串。具体版本看 [Releases](https://github.com/colinleefish/dsh-image/releases) 或仓库里的 `.env.example`。

国内拉镜像建议用阿里云 ACR（与 Docker Hub 为同一套构建产物）：

```bash
docker pull registry.cn-beijing.aliyuncs.com/colinleefish/dsh-image:<版本>
```

海外或已有 Docker Hub 习惯：

```bash
docker pull docker.io/colinleefish/dsh-image:<版本>
```

## 和别的镜像比

| | 本镜像 | 常见社区「全家桶」镜像 |
| --- | --- | --- |
| 体积 / 攻击面 | 无浏览器栈，偏瘦 | 常含 Chromium + noVNC |
| 上游 DSH | 镜像 tag 与打包的 npm 版本一致 | 视维护者而定 |
| 国内友好 | 运行态 apt / PyPI / 日常 npm 偏国内源 | 不一定 |

镜像内已带：`git`、`openssh-client`、`curl`、`jq`、`ripgrep`、`postgresql-client`、`python3`、`uv` / `uvx`、`pnpm`、Node 24。

## 国内源：拉镜像之后容器里默认是啥

你 `docker pull` 的是**已经构建好**的镜像，里面的软件源在构建时写死，**一般不用再改**。在国内跑 agent 时，下列路径已偏向国内镜像：

| 用途 | 容器内默认 | 说明 |
| --- | --- | --- |
| Debian `apt` | `mirrors.aliyun.com` | 含 security 源替换 |
| `pip` / `uv` / `uvx` | 阿里云 PyPI | 环境变量 `PIP_INDEX_URL`、`UV_INDEX_URL` |
| 容器里后续 `npm` / `pnpm install` | `registry.npmmirror.com` | `NPM_CONFIG_REGISTRY` |
| **`@deepseek-ai/dsh` 本体** | 构建时从 `registry.npmjs.org` 安装 | 已打进镜像；**运行时不会**再从 npmmirror 重装 |

要点：

- **用镜像的人**：直接得到「国内 apt / PyPI / 日常 npm」+「构建阶段从官方 npm 装好的固定版本 `dsh`」。
- **`dsh` 不走 npmmirror**：`dsh` 带 Linux 原生扩展（C++/Rust 编译产物）。国内 npm 镜像有时只同步了 JS 部分、扩展包不完整，容器里可能启动失败或缺功能；因此**只在打镜像时**从官方 npm 安装，装完写进镜像。
- **自己 `docker build` 本仓库**：默认同上；只有装 `@deepseek-ai/dsh` 的步骤走官方 npm，其余仍可用 build-arg 调整（见 `Dockerfile`、`.env.example`）。

基板：**Node 24**（`node:24-trixie` / Debian 13）；**pnpm**、**uv** 等 pin 见 `.env.example`。

## 快速开始

```bash
git clone https://github.com/colinleefish/dsh-image.git
cd dsh-image
cp .env.example .env
# 在 .env 里设置 DSH_IMAGE_VERSION 为你要拉的 tag
mkdir -p data/dot-dsh data/workspace
docker compose up -d
```

浏览器打开：**http://127.0.0.1:3080/**  
首次访问若返回 401，从容器日志里找 Web token（或按 DSH 文档配置登录门）。

```bash
docker compose logs -f --tail=50 dsh
```