# PM Copilot Modes

PM Copilot has four task modes.

| Mode | Use when | Scope rule |
| --- | --- | --- |
| `new_prd` | A feature is only a goal or brief | Clarify and confirm before writing a new PRD. |
| `implemented_feature_prd` | A feature is already implemented | Confirm observed production behavior and exclude scaffolding. |
| `prd_revision` | An existing PRD needs a partial edit | Require existing requirement IDs; freeze all unselected content and assets. |
| `prd_composition` | Selected requirements from one or more PRDs form a new need | Require each source path and requirement ID; snapshot sources and renumber from `5.1`. |

All modes deliver `prd.md`, `prd.html`, `assets/`, and internal `run-log.yaml`. Research, localization, and tracking may be generated as PRD sections when they are decision-relevant; they are not standalone modes.
