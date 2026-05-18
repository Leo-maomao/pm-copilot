# Platform Guides

PM Copilot can be used in any file-aware agent environment. The repository is designed so the agent reads Markdown contracts and writes artifacts.

## Codex

Standalone prompt when opening the `pm-copilot` repository directly:

```text
I need a PRD and tracking plan for checkout coupon optimization.
```

Notes:

- Codex can edit files directly in the workspace.
- Codex reads `AGENTS.md` automatically when launched from the repository. PM Copilot's `AGENTS.md` points to `PM_COPILOT.md`.
- When PM Copilot is nested inside another project, install the adapter with `python3 scripts/install_adapter.py --host /path/to/host-repo --tool codex`.
- Users should not need to say `Use PM Copilot` after the adapter is installed.
- Ask it to run `python3 scripts/validate_repo.py` after changes.
- For local HTML prototypes, ask it to verify the file with available local tools.

## Claude Code

Suggested prompt:

```text
I need the PRD, tracking plan, user flow, and prototype for team permission management.
```

Notes:

- Install the adapter with `python3 scripts/install_adapter.py --host /path/to/host-repo --tool claude-code`.
- The adapter delegates PM work to `pm-copilot/PM_COPILOT.md`.
- If you use web research, require source URLs in the output.

## Cursor

Suggested prompt:

```text
I need a product requirements package for mini-program appointment booking.
```

Notes:

- Install the adapter with `python3 scripts/install_adapter.py --host /path/to/host-repo --tool cursor`.
- Ask Cursor to preserve repository structure and avoid changing templates unless requested.

## Internal Agent Platforms

Map PM Copilot folders to your platform concepts:

| PM Copilot | Agent Platform Equivalent |
|---|---|
| `agents/` | role prompts or agent definitions |
| `skills/` | reusable skills, procedures, or prompt modules |
| `context/` | memory, knowledge base, or profile config |
| `workflow/` | orchestration state machine |
| `artifacts/` | output schemas or validators |
| `tools/` | tool policy and tool descriptions |
| `guardrails/` | policy, safety, and approval rules |
| `examples/` | test tasks |
| `outputs/` | golden examples or generated artifacts |

## Common Mistakes

- Loading all examples as current product facts.
- Letting the agent skip clarification for ambiguous requests.
- Treating HTML prototypes as production implementation.
- Allowing source-free competitor claims.
- Adding sensitive tracking properties without privacy review.
