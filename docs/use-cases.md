# PM Copilot Use Cases

## New Feature PRD

```text
为 <目标用户> 在 <产品区域> 增加 <能力>。请先澄清关键范围并确认，再生成 PRD。
```

## Implemented Feature To PRD

```text
请检查已实现的 <功能>，区分真实用户行为与测试或开发脚手架；确认纳入范围后还原 PRD。
```

## Partial PRD Revision

```text
修改 <prd.md> 的 5.2 和 5.4：<变更内容>。保留未选需求和资产不变。
```

## Multi-PRD Composition

```text
从 docs/a/prd.md#5.2 和 docs/b/prd.md#5.4 提取需求，确认冲突和新范围后生成独立 PRD。
```

Each completed request includes a Markdown PRD, rendered HTML, inline figure assets, and an internal trace. A frontend state is represented by a real capture, an isolated reconstructed figure, or a controlled placeholder.
