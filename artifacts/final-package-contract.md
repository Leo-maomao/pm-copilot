# Final Package Contract

The final package must help reviewers understand the requirement without opening many small files.

## Primary Artifact

Generate:

```text
outputs/<run-id>/pm-package.md
```

`final-package-summary.md` may remain as a short index or legacy summary, but `pm-package.md` is the primary reviewer-facing artifact.

Default runs should not create many separate Markdown files. Generate split source files only when the user requests them, when an external workflow needs them, or when an export is materially useful.

## Required Sections

- Executive summary
- Context and current-state fit
- Clarification status
- PRD summary and full requirement detail
- Metrics tree
- Tracking plan table
- User flow diagram
- Prototype link, annotations, and implementation notes
- Artifact index
- Key product decisions
- Metrics and tracking summary
- Prototype summary
- Review status
- Assumptions
- Open questions
- Risks
- Recommended review agenda
- Next actions

## Rules

- Link or reference each artifact by filename.
- Keep unresolved items visible.
- Do not mark the package as ready if critical issues remain.
- Separate `must answer before generation`, `can draft with stated assumption`, and `must confirm before development or launch`.
- Do not mark the package as `Ready for engineering` while any `must confirm before development or launch` item is unresolved.
- Do not make the reviewer assemble the core story from many separate files.
- Localize all human-facing headings and labels to the user's language.
