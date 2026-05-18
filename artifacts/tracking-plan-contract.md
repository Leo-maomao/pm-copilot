# Tracking Plan Contract

The tracking plan must be reviewable by product, analytics, engineering, and QA.

## Required Outputs

- Markdown event and property tables as the primary human-readable artifact. By default, place them in `prd.md`.
- Create `tracking-plan.md` only when a separate analytics or engineering handoff file is useful or requested.
- Create `tracking-plan.csv` only when a machine-readable export is useful or requested.

## Event Table Columns

The Markdown plan must include a complete event table. Localize reviewer-facing labels, and keep these machine names visible in code formatting when the artifact is not a CSV export:

```csv
event_name,description,trigger,platform,actor,required_properties,optional_properties,success_criteria,validation_notes,privacy_notes
```

## Property Dictionary Columns

The Markdown plan must include a property dictionary. Localize reviewer-facing labels, and keep these machine names visible in code formatting when the artifact is not a CSV export:

```csv
property_name,type,required,example,description,allowed_values,privacy_level,source
```

## Rules

- Use snake_case event names unless context overrides the taxonomy.
- Record the taxonomy source. If no existing analytics taxonomy or event naming convention was found, label the table as a proposed taxonomy and state that analytics/engineering must approve it before implementation.
- Use one event per observable user or system action.
- Do not describe events as loose bullet points. Use tables.
- Each event must include trigger timing, actor, platform, required properties, optional properties, validation notes, and privacy notes.
- Every property used by any event must be defined in the property dictionary.
- Include validation notes for QA and analytics verification.
- Do not collect raw payment cards, passwords, government IDs, or unredacted personal identifiers.
- Mark inferred events as assumptions.
- If an event only applies to optional scope, mark it as conditional and do not present it as required MVP instrumentation.
