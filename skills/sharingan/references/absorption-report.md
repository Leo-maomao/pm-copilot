# Sharingan Absorption Report

Use this structure at the end of a Sharingan run. Keep it short enough to be actionable.

## Decision

Choose one:

- `Absorb`: integrate now.
- `Adapt`: keep the idea but rewrite, narrow, or split it before use.
- `Quarantine`: hold until license, safety, provenance, or compatibility is clarified.
- `Reject`: do not use.

## Source Snapshot

Record:

- Source name and URL/path.
- Author, maintainer, or organization when known.
- Version, commit, release date, or access date when relevant.
- License and reuse constraints.
- Resource type: repo, docs, article, prompt, workflow, script, package, template, design, dataset, or asset.

## Learned Capability

Summarize the durable capability in PM Copilot terms:

- What future task gets easier?
- What workflow, command, pattern, schema, or judgment was extracted?
- What should trigger the capability later?

## Packaging Plan

State where the value belongs:

- Existing skill to update, or new skill to create.
- `SKILL.md` changes for core procedure.
- `references/` files for longer guidance.
- `scripts/` for deterministic automation.
- `assets/` for reusable templates or static files.
- Agents, docs, catalogs, validation scripts, or artifact contracts that need discoverability updates.

## Rejected Material

List what was deliberately not absorbed:

- Unsafe commands.
- License-restricted code or text.
- Stale docs.
- Duplicate advice.
- Branding, hype, or examples that do not generalize.

## Validation

Record checks performed:

- Repository validation.
- Syntax, lint, tests, or dry-run results.
- One realistic task or scenario used to verify the new capability.
- Remaining uncertainty.

## Final Response Shape

```text
Decision: Absorb

I turned the useful part of <source> into <skill/reference/script>. The durable PM Copilot capability is <capability>.

Changed:
- <file>
- <file>

Rejected:
- <reason>

Validated with <command/scenario>. Remaining risk: <risk or "none known">.
```
