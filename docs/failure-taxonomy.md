# Failure Taxonomy

Use this taxonomy to classify PM Copilot failures before making changes.

## Failure Categories

| Code | Category | Definition | Example |
|---|---|---|---|
| F1 | Intent failure | Agent misunderstood the user's actual goal | Treats retention task as acquisition task |
| F2 | Context failure | Agent used wrong, missing, or excessive context | Uses H5 assumptions for Web admin feature |
| F3 | Workflow failure | Agent skipped, duplicated, or misordered steps | Writes PRD before asking critical questions |
| F4 | Skill failure | Skill method is too vague, too rigid, or incomplete | Tracking skill does not force trigger precision |
| F5 | Tool failure | Tool unavailable, misused, or unverifiable | Claims competitor research without source |
| F6 | Memory failure | Agent used stale or irrelevant facts | Applies old pricing rule to new product area |
| F7 | Guardrail failure | Agent hides uncertainty or mishandles sensitive risk | Collects raw phone in tracking properties |
| F8 | Artifact failure | Output shape or content fails contract | PRD lacks non-goals or acceptance criteria |
| F9 | Review failure | Review Agent misses obvious defects | Marks PRD ready despite missing metrics |
| F10 | Runtime failure | Agent platform cannot follow files, write outputs, or preserve state | Partial files created or context lost |
| F11 | Readiness failure | PRD collapses review, engineering, and launch readiness into one misleading status | Says ready for engineering while launch blockers are hidden |
| F12 | Content-source failure | Reference or regulated content lacks source, review owner, disclaimer, or launch impact | Medical checklist appears final without review status |
| F13 | Tool-permission failure | Agent treats untrusted content, user pressure, or generated text as permission to call tools, export data, mutate state, or disclose sensitive values | Ticket text instructs the assistant to export all emails and the PRD does not isolate it |
| F14 | Source-currentness failure | Agent makes legal, policy, price, tax, medical, financial, or eligibility claims without current authoritative sources or a blocked-source status | Public benefit eligibility copy is drafted from memory |
| F15 | Accessibility and dark-pattern failure | Agent improves conversion or speed by hiding labels, removing error recovery, weakening consent, or omitting assistive states | Checkout design removes screen-reader labels to reduce UI work |

## Severity

| Severity | Meaning | Required Action |
|---|---|---|
| Critical | Unsafe, fabricated, unusable, or blocks review | Fix before reuse |
| High | Major quality gap that causes stakeholder confusion | Fix before release |
| Medium | Reviewable but needs clear human discussion | Track and improve |
| Low | Minor polish issue | Fix when convenient |

## Root Cause Questions

Ask these before editing:

1. Did the agent have the needed information?
2. Did it load the right context?
3. Did the workflow require the right step?
4. Did the skill tell it how to do the task?
5. Did the artifact contract define the required output?
6. Did the guardrail define forbidden behavior?
7. Did the tool actually run and return usable evidence?
8. Did the Review Agent catch the defect?

## Fix Mapping

| Failure Code | First Place to Fix | Second Place to Fix |
|---|---|---|
| F1 | requirement-intake skill | Discovery Agent |
| F2 | context-loading rules | product context schema |
| F3 | main workflow | PM Orchestrator Agent |
| F4 | relevant skill | artifact contract |
| F5 | tool-use protocol | failover rules |
| F6 | memory model | context-loading rules |
| F7 | guardrails | artifact contract |
| F8 | artifact contract | template |
| F9 | review-checklist skill | Review Agent |
| F10 | platform guide | runtime-specific adapter |
| F11 | PRD contract | PM Orchestrator Agent |
| F12 | guardrails | PRD contract |
| F13 | tool-use protocol | guardrails |
| F14 | research-tooling | guardrails |
| F15 | UI delivery contract | guardrails |

## Failure Log Format

```yaml
failure_id:
scenario:
date:
severity:
category:
symptom:
expected_behavior:
actual_behavior:
evidence:
root_cause:
fix_location:
fix_summary:
regression_case_added:
status:
```
