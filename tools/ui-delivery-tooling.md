# UI Delivery Tooling

## Scope

Tools support evidence collection and review-artifact validation. They must not be used to modify a host product, create feature code, deploy a release, or imply that a requested feature exists.

## Read-Only Evidence Tools

- `scripts/inspect_host_frontend.py` discovers relevant host UI files and runtime entry points.
- Browser or screenshot tooling may inspect existing rendered screens and capture evidence under `outputs/<run-id>/`.
- `scripts/extract_ui_region.py` may extract an existing rendered region into the run folder as `existing_ui_extract`; it cannot be used as proof of a proposed feature.

## Review Artifact Tools

- `scripts/validate_prototype_visual.py outputs/<run-id>` checks portable review artifacts.
- `scripts/validate_ui_preview.py <preview-url-or-file> --run-folder outputs/<run-id>` may check an existing preview supplied by the host project or user.
- `scripts/setup_visual_validation.py` prepares optional browser validation when available.

## Recording Rules

- Record source URL or file, selector when used, capture time, and fidelity limitation in the run log.
- Keep generated screenshots, extracts, and HTML under `outputs/<run-id>/`.
- Label proposed UI separately from existing evidence and name the human owner who will implement it.
- If evidence is unavailable, continue with a conceptual artifact only when the user accepts that limitation.
