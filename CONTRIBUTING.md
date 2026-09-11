# 贡献约定

## 分支与提交

- 新分支使用 `codex/` 前缀。
- 提交使用 Conventional Commit，例如 `feat: add local server health check`。
- 一个提交只解决一个可说明的变更，不混入格式化噪声或无关重构。

## 完成标准

提交前执行：

```sh
pnpm check
pnpm test
pnpm build
```

若变更引入依赖、网络监听、持久化格式、权限或跨工作区接口，请同时新增一份 ADR。
