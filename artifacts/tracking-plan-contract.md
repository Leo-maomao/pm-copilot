# Tracking Plan Contract

The tracking plan must be reviewable by product, analytics, engineering, and QA.

## Required Outputs

- The PRD uses only the concise event table defined by `artifacts/prd-contract.md`: `事件`、`事件名称`、`上报时机`、`附加参数`、`备注`.
- Create `tracking-plan.md` only when the user explicitly requests a separate analytics or engineering handoff. A detailed event/property dictionary belongs there, not in `prd.md`.
- Create `tracking-plan.csv` only when a machine-readable export is useful or requested.

## Event Table Columns

For an explicitly requested detailed tracking handoff, the Markdown plan may include a complete event table with these machine names:

```csv
event_name,description,trigger,platform,actor,required_properties,optional_properties,success_criteria,validation_notes,privacy_notes
```

## Property Dictionary Columns

For an explicitly requested detailed tracking handoff, the Markdown plan may include a property dictionary with these machine names:

```csv
property_name,type,required,example,description,allowed_values,privacy_level,source
```

## Rules

- Use snake_case event names unless context overrides the taxonomy.
- Use the existing taxonomy when it is available. When no taxonomy is available, use semantic `feature_action` event names without adding “拟议” or approval narration to the PRD; record uncertainty only in the internal trace or detailed handoff.
- Use one event per observable user or system action.
- Do not describe events as loose bullet points. Use tables.
- In a PRD, each event includes only its concise observable timing, event-external additional properties, and an optional useful note. Actor, platform, property dictionaries, validation notes, and privacy notes belong only in an explicitly requested detailed handoff.
- Every property used by a detailed handoff event must be defined in that handoff's property dictionary.
- Do not collect raw payment cards, passwords, government IDs, or unredacted personal identifiers.
- Do not present unsupported events in the PRD; omit them or record the evidence gap internally.
- If an event only applies to optional scope, mark it as conditional and do not present it as required MVP instrumentation.
