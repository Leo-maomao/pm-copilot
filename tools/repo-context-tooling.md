# Repository Context Tooling

Repository context tools help PM Copilot fit a requirement into the current product instead of inventing a greenfield solution.

## Required Context Pass

In repo-backed or embedded mode, inspect only relevant files:

- README, product docs, route maps, package metadata, or app entry points
- Existing page/component/service/API files near the requested area
- Analytics/event naming conventions
- Permission, auth, role, tenant, or account-boundary code when the feature affects access
- Existing PRDs, specs, or release notes when present

## Evidence To Record

Use `artifacts/tool-result-contract.md` for context evidence:

- file path
- observed current-state fact
- confidence
- implication for the new requirement

## Boundaries

- Do not treat PM Copilot templates or eval cases as host product facts.
- Do not scan unrelated source trees exhaustively when a targeted search is enough.
- If current-product fit cannot be determined, ask a must-answer question or mark the run as brief-only/document-backed.
