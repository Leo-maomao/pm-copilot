# Tracking Plan Contract

The tracking plan must be reviewable by product, analytics, engineering, and QA.

## Required Columns

```csv
event_name,description,trigger,platform,actor,required_properties,optional_properties,success_criteria,validation_notes,privacy_notes
```

## Rules

- Use snake_case event names unless context overrides the taxonomy.
- Use one event per observable user or system action.
- Include validation notes for QA and analytics verification.
- Do not collect raw payment cards, passwords, government IDs, or unredacted personal identifiers.
- Mark inferred events as assumptions.
