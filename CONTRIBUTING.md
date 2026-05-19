# 贡献指南

<p align="center"><strong>简体中文</strong> | <a href="docs/en/contributing-guide.md">English</a></p>

<a id="zh-cn"></a>

PM Copilot 欢迎对 Agent、技能、模板、护栏、评估用例和文档进行改进。

## 贡献原则

- 保持项目平台中立。
- 优先使用清晰契约，而不是隐藏假设。
- 保持技能简洁、可复用。
- 长篇回归用例应放在 `evals/`，不要写进技能正文。
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

## 如何新增评估用例

使用 `templates/evaluation-case-template.md` 作为起点。

评估用例应描述原始请求、上下文来源、预期工作流、必需产物、已知风险、通过标准和失败历史。不要把生成的 `outputs/` 产物作为示例提交。

只使用匿名化数据和合成数据。

## 如何修改产物契约

产物契约是公开接口。修改它们可能破坏用户工作流。

修改契约前：

1. 判断这次修改是否属于破坏性变更。
2. 更新模板。
3. 当变更会阻止或捕获回归时，更新评估用例。
4. 更新 `CHANGELOG.md`。
5. 准备发版时更新 `VERSION`。

## 校验

运行：

```bash
python3 scripts/validate_repo.py
```

安装了 `tidy` 时，可选运行 HTML 检查：

```bash
tidy -q -e templates/prototype-template.html
```

## Pull Request 清单

- 除非明确说明，否则变更应保持平台中立。
- 新技能包含有效 frontmatter。
- 新埋点方案可按 CSV 解析。
- 面向用户的变更已更新 Changelog。
- 未提交敏感数据。
