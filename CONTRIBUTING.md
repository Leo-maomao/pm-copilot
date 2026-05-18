# Contributing

PM Copilot welcomes improvements to agents, skills, templates, examples, guardrails, and documentation.

## Contribution Principles

- Keep the project platform-neutral.
- Prefer clear contracts over hidden assumptions.
- Keep skills concise and reusable.
- Put long examples in `examples/` or `outputs/`, not inside skill bodies.
- Do not add proprietary product data, private credentials, or real user data.

## How to Add a Skill

1. Create `skills/<skill-name>/SKILL.md`.
2. Add YAML frontmatter with `name` and `description`.
3. Keep the body focused on:
   - goal
   - workflow
   - output
   - quality bar
4. Do not add unrelated README files inside skill folders.
5. Run `python3 scripts/validate_repo.py`.

## How to Add an Agent

1. Create `agents/<agent-name>.md`.
2. Include:
   - purpose
   - responsibilities
   - inputs
   - outputs
   - completion criteria
   - handoffs
   - failover, when applicable
3. Update `README.md` and workflow docs if the agent changes the default flow.

## How to Add an Example

Each scenario should include:

- `examples/<scenario>/task-brief.md`
- `outputs/<scenario>/clarifying-questions.md`
- `outputs/<scenario>/assumptions.md`
- `outputs/<scenario>/pm-package.md`
- one prototype file when relevant
- optional split source or export files such as `tracking-plan.csv` or `user-flow.mmd` only when useful

Use anonymized and synthetic data only.

## How to Change Artifact Contracts

Artifact contracts are public interfaces. Changing them can break user workflows.

Before changing a contract:

1. Decide whether the change is breaking.
2. Update templates.
3. Update examples.
4. Update `CHANGELOG.md`.
5. Update `VERSION` when preparing a release.

## Validation

Run:

```bash
python3 scripts/validate_repo.py
```

Optional HTML checks when `tidy` is installed:

```bash
tidy -q -e outputs/membership-auto-renewal/prototype-h5.html
tidy -q -e templates/prototype-template.html
```

## Pull Request Checklist

- The change is platform-neutral unless explicitly documented.
- New skills include valid frontmatter.
- New examples include task brief and output package.
- New tracking plans parse as CSV.
- Changelog is updated for user-visible changes.
- No sensitive data is committed.
