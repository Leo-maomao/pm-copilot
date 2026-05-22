# UI From Image Absorption Report

## Decision

`Adapt`: integrate the transferable workflow into PM Copilot's existing UI Delivery capability instead of adding a duplicate `ui-from-image` skill.

## Source Snapshot

- Source: `https://github.com/Ixe1/ui-from-image`
- Resource type: Codex skill repository with references, examples, registration metadata, and an optional screenshot comparison helper.
- Maintainer/author observed from git metadata: Paul Lewis.
- Commit inspected: `87ebe2e9b99ae22ae76deaa2a20aae66b43adb63`
- Commit date: 2026-04-22.
- Access date: 2026-05-22.
- License: no license file found in the inspected repository. Treat direct code, template, and substantial prose reuse as not permitted unless clarified later.

## Learned Capability

Future UI delivery tasks that start from screenshots, generated UI concepts, mockups, or cropped images should run a stricter image-reference reconstruction mode:

- Treat the latest supplied image as the visual source of truth for the requested surface or delta.
- Record reference dimensions and intended viewport before implementation.
- Inventory all visible UI elements, typography, iconography, assets, spacing, and responsive risks before writing UI.
- Match the primary reference viewport before responsive refinements.
- Verify with same-viewport screenshots and visual comparison when tooling is available.
- Handle missing assets explicitly through host/supplied assets, approved image generation, or honest placeholders plus one prompt per missing asset.

Trigger this capability through `skills/multi-platform-prototype/SKILL.md` when users ask for image-to-UI, screenshot reconstruction, target mockup matching, or "图片还原".

## Packaging Plan

Integrated into the canonical UI Delivery capability:

- `skills/multi-platform-prototype/SKILL.md`: added Image Reference Reconstruction Mode and output/quality requirements.
- `skills/multi-platform-prototype/references/image-reference-reconstruction.md`: added the detailed workflow reference.
- `agents/prototype-agent.md`: added responsibilities, outputs, and completion criteria for image-reference reconstruction.
- `artifacts/prototype-contract.md`: added contract rules for screenshot/mockup target fidelity and comparison evidence.
- `tools/prototype-tooling.md`: added implementation and verification checklist items.
- `artifacts/trace-contract.md` and `templates/agent-run-log-template.yaml`: added trace expectations and fields for reference dimensions, comparison, and fidelity limits.
- `PM_COPILOT.md`, `README.md`, and `README.en.md`: updated discoverability without creating a duplicate skill entry.
- `evals/ui-from-image-reconstruction-eval.md`: added a regression case.

## Rejected Material

- Did not copy the external `compare_screenshots.py` helper because the source repo has no declared license and PM Copilot already has screenshot/diff validation through `scripts/validate_prototype_visual.py`.
- Did not copy `AGENTS.md.template` or external registration metadata because PM Copilot already has platform-neutral adapters and agent contracts.
- Did not import example images or repository branding because they are not needed for durable PM Copilot behavior.
- Did not add a sibling `skills/ui-from-image/` folder because this overlaps the canonical `multi-platform-prototype` UI Delivery skill.

## Validation

Validation completed:

```bash
python3 scripts/validate_repo.py
git diff --check
python3 -m py_compile scripts/inspect_host_frontend.py scripts/validate_outputs.py scripts/validate_repo.py scripts/preflight_tools.py scripts/preflight_integrations.py scripts/run_delivery_checks.py scripts/validate_prototype_visual.py scripts/setup_visual_validation.py scripts/install_adapter.py
```

Realistic scenario covered by the new eval: a user provides a dashboard screenshot and asks PM Copilot to restore it as UI. Expected behavior is to load UI Delivery, use image-reference reconstruction mode, preserve source-backed rules in repo-backed contexts, record reference dimensions and comparison evidence, and avoid creating a duplicate skill.
