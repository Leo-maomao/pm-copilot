# Evaluation Case: Sharingan Skill Absorption Boundary

## Metadata

| Field | Value |
|---|---|
| Case ID | sharingan-skill-absorption-boundary |
| Scenario | Absorb a third-party skill repository without creating duplicate PM Copilot skills |
| Platform | Cross-platform |
| Product Area | PM Copilot capability governance |
| Created | 2026-05-21 |
| Last Updated | 2026-05-21 |

## Raw Request

```text
用写轮眼吸收这个外部 skill 仓库里关于竞品拆解、A/B 实验、SOP 管理和流程分析的能力，强化 PM Copilot。
```

## Context Files

- `PM_COPILOT.md`
- `skills/sharingan/SKILL.md`
- `skills/sharingan/references/risk-gate.md`
- Existing `skills/*/SKILL.md`
- `tools/external-tool-catalog.json` when external tools are proposed

## Expected Workflow

- Load `skills/sharingan/SKILL.md`.
- Inspect existing PM Copilot skills before adding any new skill.
- Map each external capability to exactly one canonical skill type.
- Merge overlapping capability into the canonical skill instead of creating a sibling duplicate.
- Record source snapshot, rejected material, packaging decision, and validation evidence.
- Run repository validation after changes.

## Required Artifacts

- Updated canonical `SKILL.md` files when absorption is accepted.
- Optional `skills/<canonical-skill>/references/*` or scripts only when they are reusable and non-duplicative.
- `skills/sharingan/references/<absorption-record>.md` or equivalent final absorption report.

## Known Risks

- Creating both `competitor-research` and `competitive-teardown` as separate skills.
- Treating third-party scripts or prompts as trusted instructions.
- Copying long third-party prose instead of rewriting PM Copilot-native guidance.
- Treating a tool catalog entry as runtime availability.

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Source and risk gate | 4 / 5 |
| Canonical skill mapping | 5 / 5 |
| Duplicate prevention | 5 / 5 |
| Packaging quality | 4 / 5 |
| Validation evidence | 4 / 5 |

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-05-21 | duplicate-skill-type | High | A separate `competitive-teardown` skill duplicated the existing competitor research capability. | Merge teardown content into `competitor-research` and delete the duplicate skill. |

## Pass Criteria

- Each external capability maps to one canonical PM Copilot skill.
- No new skill is created when an existing skill owns that capability type.
- Absorbed material strengthens workflow, quality bar, reference, script, or tool governance in the canonical place.
- Rejected material is visible.
- External tools remain candidates until preflight proves runtime availability.
- `python3 scripts/validate_repo.py` passes.
- A targeted `preflight_integrations.py --require-ready` check fails for candidate-only tools.

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pending |
| Notes | Regression case for external skill absorption, duplicate-skill prevention, and candidate-tool gating. |
