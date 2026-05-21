# Quality Rubric

Use this rubric for manual evaluation. PM Copilot records score fields and thresholds, but it does not automatically judge artifact quality; every artifact should be reviewable against these standards.

## Scoring Scale

| Score | Meaning |
|---|---|
| 0 | Missing or unusable |
| 1 | Present but vague, risky, or incomplete |
| 2 | Usable draft with clear gaps |
| 3 | Review-ready with minor issues |
| 4 | Strong, specific, and ready for cross-functional review |

## Delivery-Level Rubric

| Dimension | 0 | 2 | 4 |
|---|---|---|---|
| Workflow completeness | Missing major artifacts | Most artifacts exist | All required artifacts exist and connect logically |
| Assumption handling | Assumptions hidden | Some assumptions visible | Facts, assumptions, and open questions are clearly separated |
| Cross-functional readiness | Only product can understand it | Some functions can review | Product, design, engineering, QA, and analytics can review |
| Readiness separation | One vague ready/not-ready label | Some blocker phase detail exists | PRD, engineering handoff, and launch readiness are separate and non-contradictory |
| Guardrail compliance | Fabricates or hides risk | Some risks listed | Privacy, legal, payment, source, and tool limits are explicit |
| Artifact consistency | Artifacts contradict each other | Minor inconsistencies | PRD, metrics, tracking, flow, and prototype align |
| Tool evidence | Tools are claimed without evidence | Some commands recorded | Required tools have preflight, command results, artifacts, and limitations recorded |
| Language consistency | Headings and body mix languages unintentionally | Mostly localized with some template leakage | Headings, labels, statuses, notes, and body match the user's language |

Minimum recommended delivery score for early usage: 23 / 32.

## PRD Rubric

| Dimension | 0 | 2 | 4 |
|---|---|---|---|
| Problem clarity | Problem is unclear | Problem exists but lacks context | Problem, user, and business context are clear |
| Goals and non-goals | Missing | Present but vague | Measurable goals and explicit non-goals |
| Scope | Unbounded | Scope exists but has gaps | In-scope, out-of-scope, and future scope are clear |
| Surface and access fit | Missing | Entry or permission state partly covered | Entry point, navigation visibility, eligibility, permission, and fallback states are clear |
| Content/source readiness | Missing for content-backed features | Content status partly visible | Source, review owner, review status, disclaimer, and launch impact are explicit when relevant |
| Requirements | Vague ideas | Mostly testable | Requirements are specific, prioritized, and testable |
| Requirement details | Missing details | Some logic or rule detail | Function, scenario, entry, content, logic, interaction, data, permission, edge, tracking, and acceptance links are explicit where relevant |
| Edge cases | Missing | Some common cases | Error, empty, permission, payment, rollback, and platform cases where relevant |
| Acceptance criteria | Missing | Some criteria | QA-ready pass/fail criteria |
| Readability | Wall of bullets | Some tables and structure | Scannable tables, IDs, priorities, owners, and short narrative sections |

Minimum recommended PRD score: 31 / 40.

## Metrics and Tracking Rubric

| Dimension | 0 | 2 | 4 |
|---|---|---|---|
| Metric logic | Metrics unrelated to goal | Partial mapping | Primary, secondary, guardrail, and diagnostic metrics map clearly |
| Event coverage | Core actions missing | Most actions covered | All core user/system actions covered or explicitly omitted |
| Taxonomy source | Claims standard without source | Source status unclear | Existing taxonomy source is recorded or proposed taxonomy is labeled for approval |
| Trigger precision | Ambiguous triggers | Some triggers specific | Every event has precise trigger timing |
| Property quality | Sensitive or vague properties | Mostly usable | Required/optional properties are minimal, useful, and privacy-aware |
| Validation | Missing | Basic notes | QA and analytics validation notes are actionable |
| Table completeness | Events are prose or fragmented | Event table exists but fields are incomplete | Event table and property dictionary are complete and reviewable |

Minimum recommended analytics score: 21 / 28.

## Prototype Rubric

| Dimension | 0 | 2 | 4 |
|---|---|---|---|
| Platform fit | Wrong platform | Platform roughly fits | Web/H5/App/Mini Program container matches scenario |
| Core flow | Missing | Main path visible | Main path is interactable |
| States | Only happy path | Some states | Relevant loading, empty, error, permission, confirmation, or success states |
| Access/content states | Missing | Only some gated or draft states visible | Gated eligibility and placeholder or unreviewed content states are represented when relevant |
| Local usability | Does not open | Opens with issues | Self-contained HTML with no build step |
| Fidelity and handoff clarity | Pretends to be production or is too vague to implement | Prototype is usable but lacks annotations or key states | Clearly labeled prototype with appropriate fidelity, annotations, and implementation notes |
| Existing surface fit | Invents unrelated product UI, mutates production files unexpectedly, or mixes prototype notes into unchanged UI | Some existing context reflected | Preserves baseline UI in an isolated demo and shows the new requirement delta with separate markers/dialogs |
| Annotation mapping | Notes are detached from UI | Some notes tied to controls | Page-scoped annotations are reachable from specific UI elements or transitions |

Minimum recommended prototype score: 24 / 32.

## Delivery Review Rubric

| Dimension | 0 | 2 | 4 |
|---|---|---|---|
| Severity | No severity | Severity inconsistent | Findings grouped by Critical, High, Medium, Low |
| Actionability | Vague comments | Some actions clear | Each finding has owner and next action |
| Risk coverage | Misses key risks | Covers obvious risks | Covers product, analytics, privacy, legal, engineering, and rollout risks |
| Evidence and phase | Missing | Some evidence or phase detail | Each finding includes artifact, evidence, owner, required-before phase, and status |
| Go/no-go clarity | Missing | Ambiguous | PRD, engineering handoff, and launch recommendations are clear |

Minimum recommended review score: 15 / 20.

## Common Failure Patterns

- PRD looks complete but goals cannot be measured.
- Tracking plan includes events but trigger timing is vague.
- Prototype shows screens but not state transitions.
- Logged-out or guest prototype states reveal signed-in account data or account-management actions.
- Competitor claims have no sources.
- Legal or payment risk is buried in prose.
- Launch blockers are hidden behind `Ready for engineering`.
- Unreviewed reference content looks like final approved guidance.
- Open questions are not visible in the PRD.
- Agent generates all artifacts without first clarifying the task.

## Manual Evaluation Template

```markdown
# PM Copilot Quality Review

## Delivery
- Workflow completeness:
- Assumption handling:
- Cross-functional readiness:
- Readiness separation:
- Guardrail compliance:
- Artifact consistency:

## PRD
- Problem clarity:
- Goals and non-goals:
- Scope:
- Surface and access fit:
- Content/source readiness:
- Requirements:
- Edge cases:
- Acceptance criteria:

## Metrics and Tracking
- Metric logic:
- Event coverage:
- Taxonomy source:
- Trigger precision:
- Property quality:
- Validation:
- Table completeness:

## Prototype
- Platform fit:
- Core flow:
- States:
- Access/content states:
- Local usability:
- Fidelity and handoff clarity:

## Delivery Review Inside PRD
- Severity:
- Actionability:
- Risk coverage:
- Evidence and phase:
- Go/no-go clarity:

## Overall Decision
- PRD:
- Engineering handoff:
- Launch:
```
