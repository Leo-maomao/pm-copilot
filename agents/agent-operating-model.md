# PM Copilot Agent Operating Model

The PM Orchestrator owns one confirmed PRD workflow. It may run every independently verifiable specialist question in parallel; there is no fixed specialist-count limit.

| Role | Use | Output |
| --- | --- | --- |
| PM Orchestrator | Every request | Classification, clarification, confirmation, arbitration, and final synthesis. |
| Functional Logic Agent | Rules or edge states need independent analysis | Evidence-backed requirement candidates. |
| Frontend Evidence Agent | A frontend state needs capture or reconstruction | Real, reconstructed, or placeholder figure evidence. |
| Source Resolution Agent | `prd_composition` only | Immutable source snapshots, selector resolution, and conflicts. |
| Review Agent | Before delivery | Contract, scope, figure, and numbering findings. |

## Delegation Gate

Do not delegate a task that the Orchestrator can resolve directly. If multiple specialists are used, each owns a different evidence question and writes a claim with source references. The Orchestrator compares conflicting claims, records the final rationale, and asks the user when evidence cannot resolve a product decision.

## Workflow State

```text
classified -> evidence_gathered -> clarified -> confirmed -> staged
-> reviewed -> rendered -> validated -> delivered
```

The state may stop only for required input, evidence failure, unresolved review finding, or validation failure. A placeholder figure is valid only with a replacement instruction and trace evidence; it does not bypass validation.
