# Direct Use

This is the recommended user experience for product managers.

Instead of manually copying templates and creating task folders, open this repository in an agent workspace and say what you need.

## One-Shot Prompt

```text
<write your product request here>

If important information is missing, ask me first.
If enough information is available, create `prd.md` and the matching UI deliverable.
If must-answer questions or unresolved `must confirm before development or launch` blockers exist, stop and wait for my answer before generating downstream artifacts.
Use my local product context if it exists; otherwise use the example context and mark assumptions.
Use my request language for headings, labels, statuses, notes, and UI delivery annotations.
```

The agent should automatically follow `PM_COPILOT.md` and:

- Infer a scenario name and dated ASCII run id, such as `membership-renewal-2026-05-18`.
- Create all generated run artifacts under `outputs/<run-id>/`.
- When the feature is already implemented in the current branch, inspect the branch diff, changed files, UI surfaces, screenshots/assets, tests, and validation evidence before asking questions or drafting.
- Ask must-answer clarification questions before downstream generation.
- Stop and wait when critical information is missing or an unresolved development/launch confirmation blocks the requested readiness.
- Generate `prd.md`, a UI deliverable when relevant, optional exports when useful, and an internal run log.
- Generate `prd.html` when you ask for a browser-readable or externally deliverable PRD document.
- Keep requirement input, clarified answers, assumptions, source-backed research/reference findings, metrics, tracking plan tables, flow diagrams, risks, acceptance criteria, and validation results inside `prd.md` by default.
- For document-class handoffs such as parameter references, API capability catalogs, vendor tables, payment/risk rules, data dictionaries, SOPs/runbooks, or migration inventories, generate `catalog.md` or `reference.md` and optional browser-readable HTML instead of forcing the request into a PRD. Include source facts, product decisions, source/review status, owner, access date, attention points, change log, completeness check, and engineering notes.
- Treat repository files as current-product context, not as competitor or benchmark research. When external research is unavailable, mark recommendations as assumption-based.
- For repo-backed UI delivery, read the real host frontend code, component library, styles, icons, assets, route/page/screen files, and render entry before drafting; pass the requirement or target surface into frontend inventory when available; keep host production flows read-only by default.
- For repo-backed UI delivery, use a source-rendered delta patch, preview route, Storybook/demo, Mini Program preview page, or App preview screen whenever host frontend source exists. The original baseline should be imported/rendered from the host project; only the new requirement goes into isolated delta files by default. If the user asks to implement or adjust the target UI in the current repo before handoff, record that user-approved source-change scope, run the implemented UI, then use `source_extract_html` and `extract_ui_region.py` to extract the selected region into `prototype-<platform>.html` or offline `index.html` with annotation metadata. Standalone compatibility HTML is only a portable/fallback approximation when the raw request asks for portable/standalone/HTML output without source implementation, explicitly asks to redesign/rebuild/from-scratch/stop reusing the original UI, or when source rendering was attempted and concretely blocked, and must be labeled fidelity-limited in metadata/run logs rather than visible product UI. "Only generate a prototype" means review scope only, not standalone HTML.
- Source-backed UI preview handoff must include the changed preview/delta or user-approved implementation files, route/screen/story, and run command. Do not hand off only a localhost URL. Source-extracted HTML handoff must also include the source target, selector, extraction command, region screenshot, generated HTML path, style capture method, asset handling, editable annotation layer, source-change scope, validation report, and limitations. If direct HTML is explicitly requested without source implementation, generate compatibility HTML only when source-level parity can be limited or source rendering is not required. Offline folder handoffs may use `index.html` as the entry file, but the artifact must still be an interactive HTML prototype, not a screenshot-only page.
- Product-surface copy should be launch-like and realistic. Do not scatter visible "example", "demo", "not production", or equivalent labels through UI; use annotations, PRD notes, comments, or metadata for delivery boundaries.
- For repo-backed UI delivery, import/render the original UI as `baseline_import` and add the new feature as `delta_patch`; only the delta patch should carry visible markers, explanation dialogs, backend notes, tracking notes, and edge-case annotations.
- For UI delivery, use visible red/white borderless component markers, body-only click-open/click-again-close local annotation popovers beside each marker, a short `注释`/`Notes` floating control, and a right-edge full-height current-state annotation panel. Marker popovers must not repeat the number, title/name, or close button. The side panel may include numbered notes and titles, and it should close through its close control or by clicking outside the panel. Required states should be driven by realistic controls or mocked data/API transitions; reviewer state switching controls, if present, stay fixed, collapsed, marked `data-reviewer-only="true"`, and outside the product layout.
- Run tool preflight and validation when required by `tools/tool-registry.yaml`.
- Prefer `python3 scripts/run_delivery_checks.py outputs/<run-id> --language <zh|en>` before final delivery.
- Run browser screenshot/visual diff validation for UI deliverables, including DOM smoke and access-state checks when applicable. Use `validate_prototype_visual.py` for compatibility HTML; use the host dev/preview/Storybook/simulator path for source-backed previews and `validate_ui_preview.py` when a browser URL or local preview file is available. If Playwright/browser tooling is missing, first run or guide `python3 scripts/setup_visual_validation.py`; skip only when setup fails, the environment forbids browser launch, or the user declines installation.
- Generate `dev-tasks.yaml` or `launch-decision.yaml` only when you ask for engineering handoff, issue planning, release readiness, or launch decision support.

## Implemented Feature To PRD

Use this when the product or engineering work has already happened and you need a professional PRD package for review or external delivery.

```text
当前分支已经完成了这个功能。请读取当前分支 diff、相关代码、截图/资源和验证结果，把功能完整还原成中文 PRD Markdown，并生成同目录下可浏览的 `prd.html`。

图片如果还没最终确定，请在对应需求位置放内联占位，后续我人工替换；不要额外放图片列表。
内容要完整，不要让我再人工查漏补缺。
```

Expected output:

```text
outputs/<feature-slug>-YYYY-MM-DD/prd.md
outputs/<feature-slug>-YYYY-MM-DD/prd.html
outputs/<feature-slug>-YYYY-MM-DD/assets/        # only when local images/scripts are needed
outputs/<feature-slug>-YYYY-MM-DD/run-log.yaml
```

The agent should treat implementation evidence as observed truth and product intent as unverified unless the code, docs, or user confirms it. The PRD should include an evidence/coverage map that links changed files, screenshots, tests, or observed UI behavior to requirement IDs. `prd.html` should read like a normal document with a left table of contents if useful; it should not use decorative cards, mixed module blocks, unusual background colors, or nested scroll containers. Images and placeholders belong inline at the relevant requirement or table row, and Mermaid diagrams should render correctly.

Use `templates/implemented-feature-prd-template.md` as the default structure and generate or refresh HTML with:

```bash
python3 scripts/render_prd_html.py outputs/<run-id>
```

When a screenshot is missing in a Chinese PRD, insert only this block at the exact requirement position:

```markdown
> 占位图：文件上传-上传中.png
> 用途：展示文件上传过程中的进度、按钮状态和不可重复提交规则。
```

After the user saves the screenshot under `assets/`, replace the block with `![文件上传-上传中](./assets/文件上传-上传中.png)`. Name screenshots by content and concrete state, such as `文件上传-上传中.png` or `文件上传-上传失败.png`, not `文件上传-状态.png`.

## Direct Entry

The canonical entry is:

```text
PM_COPILOT.md
```

If your agent does not automatically inspect repository instructions, tell it to read `PM_COPILOT.md` before handling the request.

If PM Copilot is nested inside another development repository, use `docs/embedded-use.md` and the adapter templates in `adapters/`.

For one-command adapter installation, run:

```bash
python3 scripts/install_adapter.py --host /path/to/host-repo --tool all
```

Avoid putting PM Copilot's full workflow into the root `AGENTS.md` of an unrelated software repository. Use a small delegation adapter instead.

## Recommended Workspace Setup

Put `pm-copilot` in a place your agent can access, for example:

```text
/Users/<you>/Desktop/product_manage/pm-copilot
```

Then open the folder in your agent environment.

## Using Product Documents Instead of a Repository

You can use PM Copilot without a software repository. Put relevant product documents in the workspace or attach them in the agent conversation, then ask for the PRD and UI deliverable.

Good context sources include:

- Historical PRDs, specs, release notes, and roadmap docs
- Screenshots, wireframes, UI delivery notes, and UX review notes
- Research summaries, customer feedback, support tickets, and meeting notes
- Analytics exports, KPI definitions, and tracking plans
- Business rules, pricing notes, compliance constraints, and rollout plans

The agent should treat those documents as current product context, ask must-answer questions if they do not answer core product-fit questions, and wait before downstream generation when critical context is missing.

## Optional Product Context

For better results, create:

```text
context/product-context.local.yaml
```

You do not need to do this before the first run. If it is missing, the agent should use the example context and mark assumptions.

For long-term use, create memory files from the examples:

```text
context/product-memory.local.yaml
context/user-preferences.local.yaml
context/decision-log.local.yaml
```

These files let PM Copilot remember stable product facts, your writing/UI-delivery preferences, and durable product decisions. They are ignored by Git.

## Expected Flow

```text
User gives request
-> Agent reads PM_COPILOT.md directly or through an adapter
-> Agent loads workflow, guardrails, contracts, and context
-> Agent asks high-impact clarification questions before generation
-> User answers or explicitly says to proceed as a draft with assumption or confirmation risk
-> Agent creates PRD/UI-delivery outputs, or structured reference/document prototype outputs, under one run folder
-> Agent checks delivery consistency
-> Agent returns artifact paths and blockers
```

When `scripts/validate_outputs.py` is available, the final check should include the generated output folder:

```bash
python3 scripts/preflight_tools.py
python3 scripts/run_delivery_checks.py outputs/<run-id> --language zh
```

For explicit self-iteration or benchmark runs where you ask the agent to choose recommended defaults, the agent should still generate the full `prd.md`, UI deliverable, and `run-log.yaml` for each round, record the default choices in the run log, and keep unresolved launch or sensitive approvals visible.

If you ask for unattended development handoff, PM Copilot can generate issue-ready task candidates, but blocked work remains blocked. If you ask for unattended launch decision support, PM Copilot can generate a conservative gate result; it cannot approve launch-sensitive gates from defaults.

## Example

```text
We want to improve the H5 membership auto-renewal experience. Users say renewal reminders are unclear, the cancellation entry is hard to find, and support tickets are increasing.

If you need current billing rules, reminder timing, cancellation paths, support scripts, legal requirements, or metric definitions, ask me first.
```

Expected generated paths:

```text
outputs/membership-renewal/prd.md
outputs/membership-renewal/prototype-h5.html
outputs/membership-renewal/run-log.yaml
```

If the same dated scenario already exists, the agent should create a collision-suffixed run folder such as:

```text
outputs/membership-renewal-2026-05-18-2/prd.md
outputs/membership-renewal-2026-05-18-2/prototype-h5.html
```

## When to Prepare Extra Context

Extra setup is still useful when:

- You want to prepare a carefully written task brief before running the agent.
- You are building regression evals.
- You want to compare outputs across multiple agent platforms.
- You want a continuous-improvement scorecard from `python3 scripts/agent_improvement_scorecard.py`.

In those cases, put the extra source material in the workspace and reference it in the request. The default delivery should still be `prd.md` plus a UI deliverable unless you ask for a specific export.
