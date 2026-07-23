# Rule Governance

## Canonical Rule Rule

Every active runtime rule has one canonical owner. The owner is a policy, workflow, artifact contract, guardrail, tool protocol, or skill selected by `indexes/runtime-routing.yaml`.

Each active rule must declare or be registered with:

- a stable `id`
- one `canonical_for` responsibility
- `status: active`
- the applicable task modes or workflow stages
- a validation method or explicit human-review boundary

## Document Responsibilities

| Document type | Owns | Does not own |
|---|---|---|
| Policy / guardrail | role boundaries, priorities, safety constraints | task-specific repair steps |
| Workflow | stage transitions, inputs, outputs, stop conditions | artifact-field definitions |
| Artifact contract | required fields and quality gates | tool setup or implementation instructions |
| Skill | when to apply a capability and its PM method | duplicate policy or contract rules |
| Tool document | tool capability, evidence, and safe fallback | product decisions or host mutations |
| Change record | failure evidence, rule references, applied change, validation | a second copy of active runtime rules |

## Historical Material

Archived plans and optimization cycles are evidence, not runtime instructions. They must be marked archived, referenced only for retrospective or self-improvement work, and point to the active canonical rule instead of restating it.

## Change Discipline

When a new failure is found:

1. Classify the failed rule or missing capability.
2. Update the single canonical owner.
3. Record the change in an optimization cycle with the canonical rule ID or path.
4. Add or update a deterministic validation when practical.

Do not add a file-specific repair instruction to a general policy merely because it fixed one run.
