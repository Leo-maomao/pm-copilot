# PM Copilot

PM Copilot 是一个专业 PRD 生成器。它把明确或待澄清的产品目标、已实现功能、既有 PRD 的局部变更，以及一个或多个既有 PRD 中的指定需求，转化为可评审的 PRD 和前端图示证据。

## 四个工作流

| 工作流 | 适用场景 | 处理方式 |
| --- | --- | --- |
| `new_prd` | 从模糊目标创建新功能 PRD | 信息充分时直接生成，关键决策缺失时集中提问 |
| `implemented_feature_prd` | 从已实现功能反向还原 PRD | 自动保留生产证据并生成 |
| `prd_revision` | 修改既有 PRD 的指定需求 | 按指定需求 ID 原子更新 |
| `prd_composition` | 从一个或多个 PRD 提取指定需求生成新 PRD | 按来源选择器生成独立 PRD |

每次完成交付都包含：

```text
prd.md
prd.html
assets/
run-log.yaml  # 内部追溯证据
```

`prd.md`、`prd.html`、`assets/` 与 `run-log.yaml` 从同一份结构化需求模型原子生成并共同验证。图示无法取得时保留受控占位文本，并在运行日志中记录人工补图动作；这不阻塞可评审 PRD 的交付。

对已实现功能的原地追加，系统将新增需求固定插入 `5.1` 之后作为 `5.2`，并同步顺延原有的 `5.2+` 清单、详情和引用编号。若本次请求提供了图像资产，会通过同一需求详情内的媒体块渲染到 HTML；没有可用资产时才尝试隔离重建并降级为受控占位。

## v2 交付协议

运行目录使用 v2 确定性交付协议。历史未完成目录不会迁移：请用当前请求重新发起一次 PRD。系统优先从请求、附件、来源 PRD 和可发现证据补齐信息；只有影响范围、权限、定价、合规或核心流程且无法安全推断的决策才会汇总为一次补充问题。信息充分时，所有规范产物直接在暂存目录中生成、进行需求忠实度和模板验证，并原子发布。

## 直接使用

```bash
python3 scripts/prd_request_controller.py --request "为审批人增加待办提醒功能"
```

多来源组合示例：

```bash
python3 scripts/prd_request_controller.py --request "组合已选需求生成新 PRD" \
  --extract-from docs/a/prd.md --extract-from docs/b/prd.md \
  --extract-selector 5.2 --extract-selector 5.4
```

PM Copilot 只读取宿主项目的代码、页面和资料作为证据，不修改宿主代码、不独立交付 UI 原型、不做研发交接或上线结论。

## 运行时

先读取 [PM_COPILOT.md](PM_COPILOT.md) 和 [运行时路由](indexes/runtime-routing.yaml)。Codex 插件从个人市场安装来源自动解析本仓库 checkout；不再维护或同步全局运行时副本，也不要求用户配置运行时路径。

验证：

```bash
python3 scripts/validate_runtime_routing.py
python3 scripts/validate_repo.py
PYTHONPATH=scripts python3 -m unittest discover -s scripts -p 'test_*.py'
```
