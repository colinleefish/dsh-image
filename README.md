# dsh-image

在 Docker 里跑 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)（`@deepseek-ai/dsh`）的瘦镜像：Web 控制台和常用命令行工具，不含 Chromium、noVNC、Browser Use。

镜像 tag 与上游 npm 版本相同。Git 发布 tag 为 `dsh-v` 加同一版本。

## 拉镜像

打开 [Releases](https://github.com/colinleefish/dsh-image/releases) 页面。选定版本后，按页里的 `docker pull` 命令拉取（含阿里云 ACR 与 Docker Hub）。

## 和别的镜像比

| | 本镜像 | 常见全家桶镜像 |
| --- | --- | --- |
| 浏览器栈 | 无 | 常含 Chromium + noVNC |
| 版本 | tag 等于打包的 npm 版本 | 视维护者而定 |
| 国内源 | apt / PyPI / 日常 npm 偏国内 | 不一定 |

基板 Node 24（`node:24-trixie`）。镜像内另有 `git`、`curl`、`jq`、`ripgrep`、`psql`、`python3`、`uv`、`pnpm` 等，见 `Dockerfile`。

## 国内软件源

拉下来的是已构建镜像，源在构建时写入，一般不用再改。

| 用途 | 默认 |
| --- | --- |
| apt | 阿里云 Debian |
| pip / uv | 阿里云 PyPI |
| 容器内 npm / pnpm | npmmirror |
| `@deepseek-ai/dsh` | 构建时从 registry.npmjs.org 安装，已写入镜像 |

`dsh` 含 Linux 原生扩展。国内 npm 镜像有时不同步这些扩展包，构建阶段因此只用官方 npm，不用 npmmirror。

## 快速开始

```bash
git clone https://github.com/colinleefish/dsh-image.git
cd dsh-image
cp .env.example .env
mkdir -p data/dot-dsh data/workspace
docker compose up -d
```

在 `.env` 里设置 `DSH_IMAGE_VERSION` 为 [Releases](https://github.com/colinleefish/dsh-image/releases) 中的版本。浏览器打开 `http://127.0.0.1:3080/`。若返回 401，从 `docker compose logs` 查看 Web token。