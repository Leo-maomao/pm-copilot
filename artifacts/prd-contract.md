# PRD Contract

Use this contract when generating or reviewing a PRD.

## Required Output

The following outline defines semantic sections, not literal English headings. Localize human-facing headings and table labels into the user's language.

```markdown
# <localized feature name> PRD

## <localized status and owners>
## <localized background>
## <localized problem statement>
## <localized goals>
## <localized non-goals>
## <localized target users>
## <localized user scenarios>
## <localized scope>
## <localized requirements>
## <localized edge cases>
## <localized metrics>
## <localized dependencies>
## <localized risks>
## <localized open questions>
## <localized acceptance criteria>
```

## Rules

- Write requirements as testable statements.
- Use tables when comparing scenarios, variants, or priorities.
- Use tables for goals, scope, requirements, dependencies, risks, and acceptance criteria when there are multiple items.
- Use stable requirement IDs such as `R1`, `R2`, and `R3`.
- Include priority, owner, status, and verification columns where they help review.
- Use short narrative paragraphs for background and problem statement.
- Avoid long unordered lists as the main PRD structure.
- Mark assumptions explicitly.
- Do not bury unresolved decisions in the requirements.
- Include non-goals to prevent scope drift.
- Localize headings and table labels into the user's language. Keep requirement IDs and other machine-readable identifiers ASCII.
