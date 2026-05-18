# Prompt System

This file defines how PM Copilot turns repository rules, memory, user requests, and tool results into agent behavior. It is not a user-facing artifact template.

## Prompt Stack

Use this order when building the active task prompt:

1. System and platform instructions from the active agent runtime.
2. Host project instructions, when PM Copilot is embedded.
3. PM Copilot entry: `PM_COPILOT.md`.
4. Workflow rules from `workflow/`.
5. Guardrails from `guardrails/`.
6. Artifact contracts from `artifacts/`.
7. Relevant agent role files from `agents/`.
8. Relevant skills from `skills/`.
9. Memory from `context/*.local.yaml`, when present.
10. Current user request and current user answers.
11. Current host repository or user-provided product documents.
12. Tool observations from the current run.

Current user instruction and current product evidence override memory. Memory is context, not authority.

## Request Classification

Classify the request before drafting:

| Class | Examples | Required Behavior |
|---|---|---|
| PM delivery | PRD, prototype, tracking, requirement, product review | Run PM Copilot workflow |
| Clarification only | "Help me ask questions first" | Stop after questions and optional run log |
| Review only | "Review this PRD/prototype" | Use review agent and write findings |
| Memory update | "Remember this preference" | Update or propose updates to local memory |
| Non-PM task | Coding, infra, unrelated writing | Do not force PM Copilot |

## Prompt Assembly Rules

- Keep prompts task-specific. Do not load every file by default.
- Load only the agent and skill files needed for the current workflow step.
- Use memory summaries, not full memory dumps, when only a few facts are relevant.
- Keep the user's language for all human-facing generated content.
- Keep file names, event names, property names, Mermaid node IDs, and other machine identifiers in ASCII.
- Do not copy English template headings into Chinese artifacts.

## Memory Use

Use memory to reduce repeated questions and match the user's working style:

- Product memory can supply stable product facts, modules, roles, permissions, analytics conventions, and design-system preferences.
- User preference memory can supply language, PRD style, prototype fidelity, annotation style, and delivery preferences.
- Decision log memory can supply prior confirmed decisions, rejected options, and unresolved strategic questions.

Do not use memory to bypass the clarification gate when the current request, current repository, or current documents are unclear. If memory conflicts with current context, say what conflicts and ask or choose the higher-priority source according to `workflow/context-loading.md`.

## Clarification Prompt Rules

Ask questions before generation when missing information materially affects:

- Product goal
- Target user
- Scope boundary
- Platform
- Current product fit
- Metrics or tracking
- Prototype direction
- Privacy, payment, legal, compliance, security, financial, or operational risk

Question buckets must be mutually exclusive:

- `must answer before generation`
- `can draft with stated assumption`
- `must confirm before development or launch`

Do not ask large question dumps. Ask the smallest set that prevents misleading output.

## Generation Prompt Rules

When the clarification gate passes, generate:

- `outputs/<run-id>/prd.md`
- `outputs/<run-id>/prototype-<platform>.html` when UI is in scope
- `outputs/<run-id>/run-log.yaml` when a trace is useful

Do not create split Markdown files by default. Put metrics, tracking, flows, risks, review findings, validation results, clarified answers, and assumptions inside `prd.md`.

## Memory Update Prompt Rules

At the end of a run, identify reusable facts or preferences learned during the task. Classify each candidate:

| Candidate Type | Default Action |
|---|---|
| Stable product fact | Suggest writing to `product-memory.local.yaml` |
| User style preference | Suggest writing to `user-preferences.local.yaml` |
| Confirmed product decision | Suggest writing to `decision-log.local.yaml` |
| Sensitive or private detail | Ask before writing |
| One-off task detail | Keep only in `run-log.yaml` |

Never silently store sensitive data. Never write `.local.yaml` examples into public committed files.

## Tool Prompt Rules

- Use file reads to inspect current context before drafting.
- Use web research only when source-backed research is requested or needed.
- Use validation tools after writing files when available.
- Record tool commands actually run in `run-log.yaml` and PRD validation results.
- Do not claim a tool was used if it was skipped.

## Failover Prompt Rules

If required context is missing, ask and stop. If the user explicitly requests a draft with risk, downgrade readiness and keep blockers visible.

If memory is missing, continue without it. If memory is malformed, ignore the malformed section, record the issue in the run log when one exists, and continue with current context.
