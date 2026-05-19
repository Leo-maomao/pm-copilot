# Tool Use Protocol

PM Copilot is platform-neutral. It defines tool behavior without requiring a specific tool runtime, but tool use must still be discoverable, preflighted, and auditable.

Use `tools/tool-registry.yaml` as the canonical capability list. Use `artifacts/tool-result-contract.md` as the canonical result shape.

Before full-loop iteration, embedded host evaluation, or final delivery, run:

```bash
python3 scripts/preflight_tools.py
```

For release validation or any run where missing required tooling should stop delivery, run:

```bash
python3 scripts/preflight_tools.py --strict
```

If external research is required, include a concrete network check:

```bash
python3 scripts/preflight_tools.py --check-network <url> --require-network --strict
```

Before final delivery of a generated run folder, run:

```bash
python3 scripts/run_delivery_checks.py outputs/<run-id> --language <zh|en>
```

## Tool Decision Rules

Use tools when they improve factuality, artifact quality, or local output generation.

Do not use optional evidence-gathering tools when:

- The artifact can be produced from user-provided context.
- The tool would expose sensitive data unnecessarily.
- The tool result cannot be cited or inspected.

This does not exempt required preflight, validation, visual QA, or delivery checks for generated artifacts.

## Tool Capability Matrix

| Capability | Use Cases | Required Disclosure | Failover |
|---|---|---|---|
| Web search | Competitor research, market examples, source-backed claims | Source title, URL, access date when available | Continue with generic assumptions and mark research unavailable |
| Web page reading | Competitor feature details, docs, pricing, policy | URL and observed facts | Ask user for source or skip source-backed claims |
| File read | Product context, templates, prior examples | File paths loaded | Ask user for missing file or continue with defaults |
| File write | Generated PRD, prototype, run log, optional exports | File paths created | Return content inline if writing is unavailable |
| Mermaid rendering | PRD flow validation | Diagram source | Keep raw Mermaid in PRD if rendering is unavailable |
| HTML preview | Prototype QA | Local file path and checked viewport | Provide static HTML and note preview not verified |
| Browser screenshot and visual diff | Prototype visual QA and regression checks | Prototype path, viewport names, screenshot paths, report path, baseline path, diff result | Run or guide `setup_visual_validation.py`; record skipped status only if setup fails, browser launch is forbidden, or user declines |
| Tool preflight | Check local tool readiness before a full run | Preflight report path or console summary | Record setup-required tools and run setup when possible |
| Delivery orchestrator | Run repo, output, visual, and HTML checks together | `tool-results/delivery-check-report.json` | Run individual commands only when the orchestrator cannot run |
| Development handoff export | Engineering issue planning | `dev-tasks.yaml` path, blockers, ready task count | Keep tasks in PRD only if file writing is unavailable |
| Launch decision support | Release readiness and go/no-go support | `launch-decision.yaml` path, gate statuses, blockers, required approvals | Downgrade to review recommendation when approval evidence is missing |

## Tool Call Record

Use `artifacts/tool-result-contract.md` for the full result schema. At minimum record `tool_id`, `purpose`, `command`, `status`, `artifacts_created`, and `limitations`.

Preflight status is an availability status. Use only registered status values such as `available`, `setup_required`, `unavailable`, `skipped`, `external_runtime`, or `not_applicable`; do not invent values such as `not_checked`. Use `external_runtime` only for agent-native capabilities that cannot be probed locally. When `--strict` is used, required capabilities in `setup_required`, `unavailable`, or `skipped` status must block the run until fixed or explicitly downgraded with a recorded limitation.

## Validation Finalization

Validation tools often run after the first PRD or prototype draft is written. When that happens, update every generated artifact that mentions validation so the final delivery contains only actual states:

- `passed` when the command completed successfully.
- `failed` when the command returned an error or incompatible-tool result.
- `skipped` when the command was unavailable or intentionally not run, with the reason.

Do not leave `pending`, `待执行`, `should run`, or equivalent placeholders after the command has already run or been skipped. If an older tool cannot parse modern HTML, record both the tool failure and any fallback parser or preview check that was actually performed.

For UI prototypes, run `python3 scripts/validate_prototype_visual.py outputs/<run-id>`. With no `--prototype` argument, the visual validator checks every supported prototype file in the run folder and writes one aggregate `visual-report.json`. If the command cannot run because the dependency or browser is unavailable, first run `python3 scripts/setup_visual_validation.py` or guide the user through the same setup. If an auto-detected system browser fails to launch, the validator should try the bundled/default Chromium path before failing. Record visual validation as `skipped` only if setup fails, browser launch is forbidden, or the user declines; do not let the absence of visual QA look like a passed browser review.

For development handoff and launch decision artifacts, record whether they were generated as `human_confirmed` or `unattended_candidate`. Tool output must not claim issue creation, deployment, or launch approval unless those actions were actually performed.

## Source Rules

- Never cite a source that was not accessed.
- Do not present model memory as current source-backed research.
- If a source is blocked or unavailable, say so.
