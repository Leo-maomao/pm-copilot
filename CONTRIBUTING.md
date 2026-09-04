# 贡献指南

PM Copilot 欢迎对四条 PRD 流程、管理器、证据链、模板和文档进行改进。
当前文档对应版本：`7.0.2`。

## 分支策略

本项目只保留一个长期分支：`main`。所有开发、验证和迭代都直接基于
`main`，完成验证后提交并推送到 `origin/main`。不要创建或保留长期功能
分支；临时分支在合并完成后应立即删除。

## 贡献原则

- 只支持新 PRD、已实现功能还原、局部修订和多源组合。
- 优先删除无流程映射的能力，而不是保留兼容层。
- 保持运行时、技能和 trace 契约简洁。
- 不要添加专有产品数据、私有凭证或真实用户数据。

## 如何新增技能

1. 创建 `skills/<skill-name>/SKILL.md`。
2. 添加包含 `name` 和 `description` 的 YAML frontmatter。
3. 让正文聚焦于：
   - 目标
   - 工作流
   - 输出
   - 质量标准
4. 不要在技能目录中添加无关 README 文件。
5. 运行 `python3 scripts/validate_repo.py`。

## 如何新增 Agent

1. 创建 `agents/<agent-name>.md`。
2. 包含：
   - 目的
   - 职责
   - 输入
   - 输出
   - 完成标准
   - 交接
   - 故障转移（如适用）
3. 如果 Agent 改变默认流程，请更新 `README.md` 和工作流文档。

## 如何修改产物契约

产物契约是公开接口。修改它们可能破坏用户工作流。

修改契约前：

1. 判断这次修改是否属于破坏性变更。
2. 更新模板。
3. 当变更会阻止或捕获回归时，更新最小回归测试。
4. 更新 `CHANGELOG.md`。
5. 准备发版时更新 `VERSION`。

## 校验

运行：

```bash
python3 scripts/validate_repo.py
python3 scripts/validate_runtime_routing.py
python3 -m unittest discover -s scripts -p 'test_*.py'
```

本地开发机首次使用时执行 `git config core.hooksPath .githooks`。之后提交包含
`VERSION` 的变更会自动更新并暂存 Codex 插件 cachebuster，提交后会刷新本机
个人市场中的 PM Copilot 插件缓存。

## Pull Request 清单

- 变更只服务四条 PRD 流程或 PRD 管理器。
- 新技能包含有效 frontmatter，且已加入运行时路由。
- 面向用户的变更已更新 Changelog。
- 未提交敏感数据。
