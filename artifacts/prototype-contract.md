# Prototype Contract

Low-fidelity prototypes are local HTML artifacts used for review, not production implementation.

## Platform Selection

| Platform | Use When | Required Simulation |
|---|---|---|
| Web | Desktop admin, SaaS, dashboards, content management | Desktop viewport, sidebar or top navigation, tables/forms |
| H5 | Mobile browser, landing pages, lightweight checkout, campaigns | Mobile browser frame, URL/header hint, single-column layout |
| App | Native mobile product flows | App frame, top bar, bottom tabs or native navigation |
| Mini Program | Mini-program style flows | Capsule area, page stack feel, authorization and lightweight forms |

## Required Interaction

- Main path must be clickable.
- At least one non-happy state must be represented when relevant.
- Buttons and links must have visible outcomes.
- Copy must fit on mobile-sized frames.

## Output Rule

Generate a single self-contained `.html` file unless the task explicitly asks for multiple platform prototypes.
