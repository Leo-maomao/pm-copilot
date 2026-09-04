# PM Copilot

PM Copilot 是一个专业 PRD 生成器。它把明确或待澄清的产品目标、已实现功能、既有 PRD 的局部变更，以及一个或多个既有 PRD 中的指定需求，转化为可评审的 PRD 和前端图示证据。

## 四个工作流

| 工作流 | 适用场景 | 确认点 |
| --- | --- | --- |
| `new_prd` | 从模糊目标创建新功能 PRD | 澄清后确认完整范围 |
| `implemented_feature_prd` | 从已实现功能反向还原 PRD | 确认哪些观察行为属于产品能力 |
| `prd_revision` | 修改既有 PRD 的指定需求 | 确认已有需求编号与修改范围 |
| `prd_composition` | 从一个或多个 PRD 提取指定需求生成新 PRD | 确认每份来源、选择范围与冲突处理 |

每次完成交付都包含：

```text
prd.md
prd.html
assets/
run-log.yaml  # 内部追溯证据
```

`prd.md` 以功能逻辑和对应前端状态为中心。能运行的页面使用真实截图；没有可运行页面时，在运行目录中生成仅用于说明的还原图示；都不可用时使用受控占位图并记录补图要求。

## 直接使用

```bash
python3 scripts/prd_request_controller.py --request "为审批人增加待办提醒功能"
```

多来源组合示例：

```bash
python3 scripts/prd_request_controller.py --request "组合已选需求生成新 PRD" \
  --extract-from docs/a/prd.md --extract-from docs/b/prd.md \
  --answers "source-1: 5.2; source-2: 5.4"
```

PM Copilot 只读取宿主项目的代码、页面和资料作为证据，不修改宿主代码、不独立交付 UI 原型、不做研发交接或上线结论。

## 运行时

先读取 [PM_COPILOT.md](PM_COPILOT.md) 和 [运行时路由](indexes/runtime-routing.yaml)。Codex 插件通过 `PM_COPILOT_REPOSITORY` 指向本仓库 checkout；不再维护或同步全局运行时副本。

验证：

```bash
python3 scripts/validate_runtime_routing.py
python3 scripts/validate_repo.py
PYTHONPATH=scripts python3 -m unittest discover -s scripts -p 'test_*.py'
```
