# Direct Use

From this repository, start every PRD request through the canonical controller:

```bash
python3 scripts/prd_request_controller.py --request "为团队成员新增审批提醒功能"
```

信息充分时控制器会直接交付；仅在缺少关键产品决策时暂停一次澄清。通过运行目录补充答案：

```bash
python3 scripts/prd_request_controller.py --run-folder <run-folder> --answers "<answer>"
```

For composition, repeat the source argument and use source-qualified selectors:

```bash
python3 scripts/prd_request_controller.py --request "组合已选需求生成新 PRD" \
  --extract-from docs/a/prd.md --extract-from docs/b/prd.md \
  --extract-selector 5.2 --extract-selector 5.4
```

The generated run folder is the only delivery location. PM Copilot reads host projects as evidence and never writes into their product source tree.
