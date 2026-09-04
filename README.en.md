# PM Copilot

PM Copilot is a professional PRD generator. It creates reviewable product requirements and frontend figure evidence from clarified goals, implemented behavior, scoped PRD changes, or selected requirements from one or more PRDs.

## Workflows

| Mode | Use | Required confirmation |
| --- | --- | --- |
| `new_prd` | Create a feature PRD from a goal or brief | Confirm the clarified scope. |
| `implemented_feature_prd` | Restore a PRD from completed behavior | Confirm retained production behavior. |
| `prd_revision` | Edit selected requirements in one PRD | Confirm existing requirement IDs and change boundary. |
| `prd_composition` | Compose a new PRD from selected requirements in one or more PRDs | Confirm each source, selection, and conflict resolution. |

Every completed run contains `prd.md`, `prd.html`, `assets/`, and internal `run-log.yaml`. Figures are real captures when a frontend runs, isolated reconstructed evidence when it does not, or controlled placeholders with a replacement instruction.

```bash
python3 scripts/prd_request_controller.py --request "Create a PRD for approval reminders"
```

Host repositories are read-only evidence. PM Copilot does not modify host code, ship independent UI prototypes, create engineering handoffs, or decide launches.

The Codex plugin resolves this checkout only from its installed personal-marketplace source. It does not use a copied global runtime or an environment-variable override.
