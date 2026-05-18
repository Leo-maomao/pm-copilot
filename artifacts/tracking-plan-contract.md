# Tracking Plan Contract

The tracking plan must be reviewable by product, analytics, engineering, and QA.

## Required Outputs

- `tracking-plan.md` as the primary human-readable artifact.
- `tracking-plan.csv` as the machine-readable export.

## Event Table Columns

The Markdown plan must include a complete event table:

```csv
event_name,description,trigger,platform,actor,required_properties,optional_properties,success_criteria,validation_notes,privacy_notes
```

## Property Dictionary Columns

The Markdown plan must include a property dictionary:

```csv
property_name,type,required,example,description,allowed_values,privacy_level,source
```

## Rules

- Use snake_case event names unless context overrides the taxonomy.
- Use one event per observable user or system action.
- Do not describe events as loose bullet points. Use tables.
- Each event must include trigger timing, actor, platform, required properties, optional properties, validation notes, and privacy notes.
- Every property used by any event must be defined in the property dictionary.
- Include validation notes for QA and analytics verification.
- Do not collect raw payment cards, passwords, government IDs, or unredacted personal identifiers.
- Mark inferred events as assumptions.
