# 已发布镜像

镜像 tag 与 [`@deepseek-ai/dsh`](https://www.npmjs.com/package/@deepseek-ai/dsh) 的 npm 版本相同。**最新版本在最前面**。

```bash
docker pull registry.cn-beijing.aliyuncs.com/colinleefish/dsh-image:<版本>
docker pull docker.io/colinleefish/dsh-image:<版本>
```

| 版本 | ACR digest | Docker Hub digest | 构建 commit | 发布于 |
| --- | --- | --- | --- | --- |
| `0.2.3-alpha.2` | `sha256:2d6d8b4246cf0af310bd8a034d5b25912901e4ebf13499dc0dd5f7bddfc4d748` | `sha256:2d6d8b4246cf0af310bd8a034d5b25912901e4ebf13499dc0dd5f7bddfc4d748` | [`c372e45`](https://github.com/colinleefish/dsh-image/commit/c372e456be121673cde02fc63149d011d30412a2) | 2026-11-22T19:34:37Z |
| `0.2.2-rc.5` | `sha256:140ef6df3a339afa5e062ad2ad9f012cad24241768818c6c85ffe247a71841ec` | `sha256:140ef6df3a339afa5e062ad2ad9f012cad24241768818c6c85ffe247a71841ec` | [`0cb2bbb`](https://github.com/colinleefish/dsh-image/commit/0cb2bbb687f44e785d9a8681b2c7ccc76f85057f) | 2026-11-19T13:20:16Z |
| `0.2.2-rc.4` | `sha256:08145f86c22c16b305c9ce10a5514980c4ff4dbf188f81112c2a2418238f2a3c` | `sha256:08145f86c22c16b305c9ce10a5514980c4ff4dbf188f81112c2a2418238f2a3c` | [`0ca5a09`](https://github.com/colinleefish/dsh-image/commit/0ca5a09b663197d78c8b91c98c121868290af7df) | 2026-11-20T00:38:24Z |
| `0.2.2-rc.3` | `sha256:ec8aa592892f4466497d1f85c79ad576aa5f7928bb0ebc72864ce01e00cd0281` | `sha256:ebe0de5363d0066a95caf6de0f91603cfe07e99107239c33c994217bc6e216d9` | [`4ed1df9`](https://github.com/colinleefish/dsh-image/commit/4ed1df927a7ef8b3e362bccbe83f60711e48aa31) | 2026-11-15T06:10:59Z |
| `0.2.2-rc.2` | `sha256:895cf4e70253f410e278d387d5b7cef127f136d7a0b4f38b85900f48112a6a0f` | `sha256:895cf4e70253f410e278d387d5b7cef127f136d7a0b4f38b85900f48112a6a0f` | [`f063af0`](https://github.com/colinleefish/dsh-image/commit/f063af01df42e45db83c300f31362cb39739f5f4) | 2026-11-23T07:34:25Z |
| `0.2.2-rc.1` | `sha256:419aae6eac9130f4ceb3e7d0d2f0fb00b9a6d66624e1ceec6bbc8ae74a365884` | `sha256:419aae6eac9130f4ceb3e7d0d2f0fb00b9a6d66624e1ceec6bbc8ae74a365884` | [`22e9b57`](https://github.com/colinleefish/dsh-image/commit/22e9b57b192aeee98825a0ed241143e68bffa276) | 2026-11-23T23:51:18Z |
| `0.2.2-alpha.3` | `sha256:37fcc017c0fceb57446efec04fbf5f0d81b7078231b823188c3ae2854655c799` | `sha256:37fcc017c0fceb57446efec04fbf5f0d81b7078231b823188c3ae2854655c799` | [`5d8e058`](https://github.com/colinleefish/dsh-image/commit/5d8e058f3840698435d5a719e1dd7cf9ee76ae71) | 2026-11-24T11:20:12Z |

## 跳过

这些版本构建失败，定时任务不会再打。从 `images.json` 删掉后，用 Actions 手动指定该版本才会再试。

| 版本 | 原因 | 记录于 |
| --- | --- | --- |
| `0.2.3-alpha.1` | npm install: @deepseek-ai/cordis-plugin-loader has no export named EntryValidationError | 2026-11-22T06:41:36Z |
