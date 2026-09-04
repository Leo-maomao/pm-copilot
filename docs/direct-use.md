# Direct Use

From this repository, start every PRD request through the canonical controller:

```bash
python3 scripts/prd_request_controller.py --request "为团队成员新增审批提醒功能"
```

The controller pauses for clarification and explicit confirmation where the selected flow requires them. Resume an existing run through its run folder:

```bash
python3 scripts/run_interactive_request.py --run-folder <run-folder> --status
python3 scripts/run_interactive_request.py --run-folder <run-folder> --answer "<answer>"
python3 scripts/run_interactive_request.py --run-folder <run-folder> --confirm
```

For composition, repeat the source argument and use source-qualified selectors:

```bash
python3 scripts/prd_request_controller.py --request "组合已选需求生成新 PRD" \
  --extract-from docs/a/prd.md --extract-from docs/b/prd.md \
  --answers "source-1: 5.2; source-2: 5.4"
```

The generated run folder is the only delivery location. PM Copilot reads host projects as evidence and never writes into their product source tree.
