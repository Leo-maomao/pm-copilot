# Evaluation Case: Image Reference UI Reconstruction

## Metadata

| Field | Value |
|---|---|
| Case ID | ui-from-image-reconstruction |
| Scenario | Convert a supplied UI image into a PM Copilot UI deliverable without creating a duplicate skill |
| Platform | Web / H5 / App / Mini Program |
| Product Area | UI Delivery |
| Created | 2026-05-22 |
| Last Updated | 2026-05-22 |

## Raw Request

```text
Use this screenshot as the source of truth and recreate it as an annotated UI deliverable. The output should match the image closely.
```

## Context Files

- `PM_COPILOT.md`
- `agents/prototype-agent.md`
- `skills/multi-platform-prototype/SKILL.md`
- `skills/multi-platform-prototype/references/image-reference-reconstruction.md`
- `artifacts/prototype-contract.md`
- `tools/prototype-tooling.md`
- `artifacts/trace-contract.md`

## Expected Workflow

- Load `skills/multi-platform-prototype/SKILL.md`.
- Activate Image Reference Reconstruction Mode because the image is the visual source of truth.
- Record reference image source, exact dimensions, intended viewport, role, and uncertainty before drafting UI.
- Inventory all visible UI elements before implementation: layout, typography, controls, icons, assets, colors, spacing, scroll regions, and responsive risks.
- If host frontend source exists, preserve source-backed baseline and add the requested reconstruction/delta through an isolated preview mode.
- Match the primary reference viewport first, then verify responsive behavior.
- Capture or record same-viewport implementation screenshot evidence when browser tooling is available.
- Use side-by-side review or visual diff, list mismatches fixed, and record remaining limits.
- Handle missing assets through supplied/host assets, approved generation, or honest placeholders plus one standalone prompt per missing asset.
- Do not create a sibling `skills/ui-from-image/` folder.

## Required Artifacts

- UI deliverable in the selected source-backed or compatibility mode.
- `run-log.yaml` entries for reference source/dimensions, visual inventory, asset handling, comparison method, mismatches fixed, and remaining limitations.
- Visual validation evidence or a concrete skipped-tool reason.
- Annotation markers and notes tied to the reconstructed UI elements.

## Known Risks

- Treating a user-provided target screenshot as permission to ignore source-backed repo rules.
- Claiming high, exact, 1:1, or pixel-level fidelity without same-viewport screenshot comparison evidence.
- Omitting small icons, carets, status dots, chart details, or image crops from the reference.
- Using CSS `zoom`, root transforms, screenshot backgrounds, or an inflated canvas to fake similarity.
- Creating a duplicate image-to-UI skill instead of extending `multi-platform-prototype`.

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Trigger and canonical skill selection | 5 / 5 |
| Reference intake and inventory | 4 / 5 |
| Source-backed compatibility | 5 / 5 |
| Fidelity verification evidence | 4 / 5 |
| Asset handling honesty | 4 / 5 |

## Pass Criteria

- Image-reference reconstruction is handled by `multi-platform-prototype`.
- Reference image dimensions and viewport are recorded before implementation.
- The UI deliverable matches the reference at the primary viewport before responsive refinements.
- Fidelity claims match the available screenshot comparison evidence.
- Missing assets are explicit and have one replacement path each.
- `python3 scripts/validate_repo.py` passes after capability changes.

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pending |
| Notes | Regression case for screenshot/image-to-UI reconstruction and duplicate-skill prevention. |
