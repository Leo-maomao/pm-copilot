# Quality Rubric

Use this rubric for manual evaluation. PM Copilot v1 does not include automated quality scoring, but every artifact should be reviewable against these standards.

## Scoring Scale

| Score | Meaning |
|---|---|
| 0 | Missing or unusable |
| 1 | Present but vague, risky, or incomplete |
| 2 | Usable draft with clear gaps |
| 3 | Review-ready with minor issues |
| 4 | Strong, specific, and ready for cross-functional review |

## Package-Level Rubric

| Dimension | 0 | 2 | 4 |
|---|---|---|---|
| Workflow completeness | Missing major artifacts | Most artifacts exist | All required artifacts exist and connect logically |
| Assumption handling | Assumptions hidden | Some assumptions visible | Facts, assumptions, and open questions are clearly separated |
| Cross-functional readiness | Only product can understand it | Some functions can review | Product, design, engineering, QA, and analytics can review |
| Guardrail compliance | Fabricates or hides risk | Some risks listed | Privacy, legal, payment, source, and tool limits are explicit |
| Artifact consistency | Artifacts contradict each other | Minor inconsistencies | PRD, metrics, tracking, flow, and prototype align |

Minimum recommended package score for alpha usage: 14 / 20.

## PRD Rubric

| Dimension | 0 | 2 | 4 |
|---|---|---|---|
| Problem clarity | Problem is unclear | Problem exists but lacks context | Problem, user, and business context are clear |
| Goals and non-goals | Missing | Present but vague | Measurable goals and explicit non-goals |
| Scope | Unbounded | Scope exists but has gaps | In-scope, out-of-scope, and future scope are clear |
| Requirements | Vague ideas | Mostly testable | Requirements are specific, prioritized, and testable |
| Edge cases | Missing | Some common cases | Error, empty, permission, payment, rollback, and platform cases where relevant |
| Acceptance criteria | Missing | Some criteria | QA-ready pass/fail criteria |

Minimum recommended PRD score: 18 / 24.

## Metrics and Tracking Rubric

| Dimension | 0 | 2 | 4 |
|---|---|---|---|
| Metric logic | Metrics unrelated to goal | Partial mapping | Primary, secondary, guardrail, and diagnostic metrics map clearly |
| Event coverage | Core actions missing | Most actions covered | All core user/system actions covered or explicitly omitted |
| Trigger precision | Ambiguous triggers | Some triggers specific | Every event has precise trigger timing |
| Property quality | Sensitive or vague properties | Mostly usable | Required/optional properties are minimal, useful, and privacy-aware |
| Validation | Missing | Basic notes | QA and analytics validation notes are actionable |
| Table completeness | Events are prose or fragmented | Event table exists but fields are incomplete | Event table and property dictionary are complete and reviewable |

Minimum recommended analytics score: 18 / 24.

## Prototype Rubric

| Dimension | 0 | 2 | 4 |
|---|---|---|---|
| Platform fit | Wrong platform | Platform roughly fits | Web/H5/App/Mini Program container matches scenario |
| Core flow | Missing | Main path visible | Main path is interactable |
| States | Only happy path | Some states | Relevant loading, empty, error, permission, confirmation, or success states |
| Local usability | Does not open | Opens with issues | Self-contained HTML with no build step |
| Fidelity and handoff clarity | Pretends to be production or is too vague to implement | Prototype is usable but lacks annotations or key states | Clearly labeled prototype with appropriate fidelity, annotations, and implementation notes |

Minimum recommended prototype score: 14 / 20.

## Review Checklist Rubric

| Dimension | 0 | 2 | 4 |
|---|---|---|---|
| Severity | No severity | Severity inconsistent | Findings grouped by Critical, High, Medium, Low |
| Actionability | Vague comments | Some actions clear | Each finding has owner and next action |
| Risk coverage | Misses key risks | Covers obvious risks | Covers product, analytics, privacy, legal, engineering, and rollout risks |
| Go/no-go clarity | Missing | Ambiguous | Clear status: Ready, Ready with risks, or Not ready |

Minimum recommended review score: 12 / 16.

## Common Failure Patterns

- PRD looks complete but goals cannot be measured.
- Tracking plan includes events but trigger timing is vague.
- Prototype shows screens but not state transitions.
- Competitor claims have no sources.
- Legal or payment risk is buried in prose.
- Open questions are not visible in the final package.
- Agent generates all artifacts without first clarifying the task.

## Manual Evaluation Template

```markdown
# PM Copilot Quality Review

## Package
- Workflow completeness:
- Assumption handling:
- Cross-functional readiness:
- Guardrail compliance:
- Artifact consistency:

## PRD
- Problem clarity:
- Goals and non-goals:
- Scope:
- Requirements:
- Edge cases:
- Acceptance criteria:

## Metrics and Tracking
- Metric logic:
- Event coverage:
- Trigger precision:
- Property quality:
- Validation:
- Table completeness:

## Prototype
- Platform fit:
- Core flow:
- States:
- Local usability:
- Fidelity and handoff clarity:

## Review Checklist
- Severity:
- Actionability:
- Risk coverage:
- Go/no-go clarity:

## Overall Decision
- Ready / Ready with risks / Not ready
```
