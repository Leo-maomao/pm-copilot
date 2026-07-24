# Third-Party Skill Intake — 2026-07-24

## Decision

**Adapt.** The requested skills strengthen existing PM Copilot capabilities, but they must be made portable through this repository's canonical skills and routing index rather than through machine-local installation.

## Source Snapshot

| Upstream source | Pinned commit | Requested skills | Reuse decision |
| --- | --- | --- | --- |
| `anthropics/skills` | `1f630fdf9259cec4a14913127dfd7c3b69ef72eb` | `frontend-design` | No upstream license file was detected in the inspected snapshot. Do not copy prose; adapt the high-level visual-direction practice into `skills/design-system-audit/SKILL.md`. |
| `vercel-labs/agent-skills` | `fb0282c76b8bbd709e1a5dadb32bb4aa463cdd9b` | `web-design-guidelines` | No upstream license file was detected in the inspected snapshot. Do not copy prose or fetch rules implicitly; adapt stable audit concerns into local review skills. |
| `mattpocock/skills` | `ed37663cc5fbef691ddfecd080dff42f7e7e350d` | `tdd`, `grill-me`, `grill-with-docs`, `improve-codebase-architecture` | MIT license detected. Use original local guidance instead of vendoring full upstream workflows so PM Copilot boundaries remain authoritative. |

## Capability Mapping

| Requested capability | Local canonical owner | Invocation boundary |
| --- | --- | --- |
| Distinct visual direction | `skills/design-system-audit/SKILL.md` | UI delivery or product review only |
| UI quality and accessibility audit | `skills/design-system-audit/SKILL.md` and `skills/review-checklist/SKILL.md` | UI delivery or product review only |
| Structured decision interview and decision notes | `skills/requirement-intake/SKILL.md` | Requirement, PRD, handoff, or review decisions |
| Test-first maintenance | `skills/test-first-maintenance/SKILL.md` | PM Copilot self-improvement only |
| Repository architecture review | `skills/repository-architecture-review/SKILL.md` | PM Copilot self-improvement only |

## Deliberately Not Absorbed

- Direct host-code implementation, deployment, cloud provisioning, and external side effects.
- Automatic writing of external ADRs, glossaries, tickets, or durable decisions without user confirmation.
- Upstream command setup, package installation, or dynamic rule fetching as a hidden runtime dependency.
- Full upstream prose or templates where reuse rights were not established.

## Validation

The local skills are registered through `indexes/runtime-routing.yaml` capability selectors. `scripts/validate_runtime_routing.py` verifies selector shape, active-document resolution, and task-mode scope.
