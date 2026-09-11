# 采用 pnpm 工作区技术基线

- 状态：已废弃；现行技术基线由 `AGENTS.md`、工作区配置与后续 ADR 维护
- 日期：2026-09-09

## 背景

项目曾计划包含 Codex 插件、本地服务、管理页和可复用代码，需要在不引入云服务的前提下保持边界清晰。

## 决策

初始方案采用 Node 24、pnpm workspace、TypeScript strict mode、React + Vite、Fastify、Zod、Biome、Vitest 和 Playwright。文档持久化的具体业务方案暂不实现，且不引入数据库或 ORM。

## 后果

该初始方案中的 Fastify、Zod 与纯前端替代路径均未成为现行实现。Node 本机服务由 `0006-local-index-service.md` 定义；后续引入持久化格式或跨包接口时必须补充 ADR。
