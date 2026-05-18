# Prototype Tooling Notes

Prototypes should be generated as self-contained HTML files.

## Requirements

- No build step.
- No external network dependency.
- Inline CSS and JavaScript are acceptable for a prototype artifact.
- Use semantic buttons and links for interactions.
- Include a visible prototype-only / not-production-code boundary.
- When current product UI evidence exists, match the current surface before adding the new requirement.
- Use left-side prototype plus right-side numbered annotation panel by default.
- Use matching numbered callouts such as `①`, `②`, and `③` beside the UI element and in the annotation panel.

## Suggested Verification

- Open the file locally.
- Click through the main path.
- Confirm text does not overflow the mobile frame.
- Confirm the selected platform shape is obvious.
- Confirm numbered callouts map to matching right-side notes.
- Confirm notes describe concrete logic, interaction, text limit, data, permission, state, and tracking rules where relevant.
- Confirm no external image, font, or script is required.

## Platform Hints

- Web: use a desktop-like layout with navigation, panels, tables, or forms.
- H5: use a narrow mobile browser frame with scrollable single-column content.
- App: use a native-style top bar and bottom navigation when relevant.
- Mini Program: include a capsule area and mini-program style top chrome.
