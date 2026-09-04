---
name: review-checklist
description: Use when reviewing PM artifacts for completeness, ambiguity, missing metrics, edge cases, dependencies, risks, and readiness.
---

# PRD Review

## Goal

Decide whether one PRD delivery is ready for product stakeholder review. The
review covers `prd.md`, `prd.html`, `assets/`, and `run-log.yaml`; it does not
produce implementation handoffs, launch decisions, or standalone UI artifacts.

## Workflow

1. Check the PRD against `artifacts/prd-contract.md` and the confirmed scope.
2. Verify every requirement ID has one matching detail and that a revision has
   not changed unselected requirements.
3. Verify each user-facing state has a real figure, an isolated reconstructed
   figure, or a controlled placeholder beside its requirement detail.
4. Check that figure paths, hashes, captions, and HTML rendering match the
   staged PRD bytes.
5. For implemented-feature PRDs, verify immutable implementation evidence,
   requirement coverage, and figure provenance. Do not treat generated output
   or local scaffolding as product evidence.
6. For composed PRDs, verify every selected source requirement resolves only
   from its immutable source snapshot. For revisions, verify baseline and
   selected-scope evidence.
7. Verify the controller trace records confirmation, lineage, review findings,
   validation results, and a truthful terminal status.
8. Identify Critical, High, Medium, or Low findings. Separate blocking fixes
   from optional improvements and attach evidence to each finding.

## Output

- Summary recommendation
- Findings by severity
- Requirement and figure coverage checklist
- Open decisions or blockers
- Validation results
- Next actions

## Quality Bar

- Findings are actionable and evidence-backed.
- A Critical or High finding blocks PRD promotion until it is fixed, accepted
  explicitly as risk, or returned for clarification.
- A review with no Critical or High findings still records the checks performed
  and residual risk.
