# 本地需求管理器

本地优先的产品助理仓库，包含 Codex 插件、需求管理页和私有统一需求库。需求是唯一业务对象。

`apps/manager-web` 提供阅读与本机管理页，`services/local-server` 提供统一需求库索引和受限写入，`packages/core` 提供共享模型，`plugins/pm-copilot` 在目标项目中调用。

```sh
pnpm install
pnpm start
```

管理器默认只读。点击“需求管理器”并输入本机编辑口令后，当前浏览器可以持续编辑，服务重启后无需重复输入；局域网访问者未解锁时只能阅读。可用 `PM_COPILOT_PORT`、`PM_COPILOT_HOST`、`PM_COPILOT_LIBRARY_ROOT` 和 `PM_COPILOT_HISTORY_ROOT` 覆盖默认设置。详见 [统一需求库规范](./docs/requirements-storage.md) 和 [插件工作流](./docs/plugin-workflows.md)。
