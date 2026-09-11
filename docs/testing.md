# 测试约定

## 检查层级

| 层级 | 命令 | 覆盖内容 |
| --- | --- | --- |
| 静态检查 | `pnpm check` | Biome 格式与静态规则、TypeScript strict 类型检查 |
| 单元测试 | `pnpm test:unit` | `packages/core` 纯函数与前端数据源 |
| 端到端测试 | `pnpm test:e2e` | 真正的 Chrome 页面和本机索引服务 |
| 完整验证 | `pnpm test` | 单元测试和端到端测试 |

## 新功能要求

- 新增共享状态、转换规则或纯函数时，在 `packages/core` 添加单元测试。
- 新增或调整前端数据源契约时，在 `packages/core` 添加单元测试。
- 改变用户可见页面、路由或前端数据流时，添加或更新 Playwright 测试。
- 改变本机写入接口、访问权限或持久化格式时，使用隔离的临时项目验证写入结果、刷新后的读取结果，以及局域网请求被服务端拒绝。
- 浏览器相关变更还须在真实浏览器中检查页面、控制台和主要状态。

提交前执行 `pnpm check && pnpm test && pnpm build`。
