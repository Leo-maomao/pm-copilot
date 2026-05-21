---
name: design-system-audit
description: Use when reviewing or deriving UI tokens, component patterns, layout density, accessibility rules, visual consistency, or design-to-development handoff constraints.
---

# Design System Audit

## Goal

Extract and enforce the current product's design system so UI deliverables and PRDs extend the real UI instead of inventing a generic visual language.

## Workflow

1. Inspect available design evidence: Figma, screenshots, Storybook, routes, component files, token files, CSS variables, Tailwind config, theme files, icon libraries, and previous UI deliverables or compatibility prototypes.
2. Capture tokens: colors, typography, spacing, radius, shadows, borders, density, breakpoints, motion, and semantic states.
3. Capture component patterns: navigation, tables, filters, forms, empty states, modals, toasts, cards, tabs, status chips, and permission states.
4. Check accessibility basics: contrast, focus style, keyboard reachability, label association, touch target size, reduced-motion expectation, and error text.
5. Identify drift: one-off colors, inconsistent spacing, mismatched icon styles, duplicate components, unclear state naming, and inaccessible variants.
6. Define UI delivery reuse guidance: components to render or mirror, tokens to reuse, states to include, and visual claims that are not supported by evidence.
7. Record `style_evidence`, `existing_ui_visual_baseline`, and limitations when used for repo-backed UI deliverables.
8. If external design tools such as Figma or v0 are requested, run `skills/tool-vetting/SKILL.md` first.

## Boundary

Use this skill to audit or derive design-system evidence and UI delivery reuse guidance. Use `skills/multi-platform-prototype/SKILL.md` to build the actual UI deliverable. Do not create separate token-audit, visual-consistency, or UI-system-review skills; extend this one.

## Output

- Design evidence inventory
- Token and component summary
- Accessibility and consistency findings
- Reuse guidance for UI deliverables
- Drift or missing-design-system risks
- Handoff notes for design and engineering

## Quality Bar

- Existing UI evidence drives visual choices.
- The audit does not claim pixel parity without a baseline or comparison.
- Accessibility issues are treated as product risks, not polish.
- Generated UI deliverables include only supported style claims.
- External design tools are not assumed available without vetting.
