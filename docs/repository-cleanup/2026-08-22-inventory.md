# Repository Cleanup Inventory

Date: 2026-08-22

This is an audit record for the repository cleanup. It is not a PM Copilot
runtime instruction and is not used by routing.

## Scope and Evidence

- The repository has no tracked files under `outputs/`; generated output is
  ignored by `.gitignore`.
- Before cleanup, `outputs/` contained 234 run directories, 1,013 files, and
  approximately 62 MB.
- No source, routing index, test, or documentation references a concrete
  output directory name. References are generic `outputs/<run-id>` contracts.
- No byte-identical duplicate was found across `skills/`, `agents/`,
  `artifacts/`, `templates/`, `workflow/`, `guardrails/`, `policies/`, or
  `prompts/`.

## Completed Batches

| Batch | Classification | Action | Evidence |
|---|---|---|---|
| 1 | Runtime garbage | Removed 73 empty directories under `outputs/` and two untracked `.DS_Store` files | No files, no references, not tracked |
| 2 | Runtime garbage | Removed 56 `.portfolio.lock` files | No evaluation process was running; lock files contain no result data |
| 3 | Failed/incomplete generated runs | Moved 119 directories to `outputs/.failed-runs/archive-2026-08-22/` | No complete PRD/reference/UI contract, no active process, and no concrete source/document reference |
| 4 | Duplicate complete generated runs | Moved 21 older same-scenario copies to `outputs/.failed-runs/duplicate-archive-2026-08-22/` | Kept one highest-completeness/latest candidate per scenario group |
| 5 | Confirmed test leftovers | Removed the 119 previously archived failed/incomplete directories | User confirmed these were test leftovers; archive was empty of active references and its contents were already classified |
| 6 | Final generated-output cleanup | Removed all remaining contents of `outputs/`, including the 21 duplicate archive directories and retained historical outputs | No active evaluator process; no concrete output-directory references; user authorized one-step removal of test artifacts |

## Current Output Inventory

After the final cleanup, `outputs/` is an empty runtime entry directory:

- All generated PRD, reference, UI, trace, portfolio, failure, and duplicate
  artifacts were removed. They were not tracked by Git and are not runtime
  instructions or source inputs.
- Future runs may recreate `outputs/<run-id>/` as needed.
- Source files with low textual reference counts were not deleted: CLI entry
  points can be invoked externally, and static search cannot prove they are
  unused.

## Next Safe Action

Generated-output retention is now an explicit user decision: the repository
keeps no local run artifacts by default. Do not treat a newly generated output
as source-of-truth code or a runtime rule.
