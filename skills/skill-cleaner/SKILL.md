---
name: skill-cleaner
description: Use when auditing PM Copilot or Codex skill roots, duplicate skills, unused skills, prompt-budget pressure, or overlong skill descriptions.
---

# Skill Cleaner

## Goal

Keep PM Copilot's skill layer small, discoverable, and safe to load by auditing prompt-budget usage, duplicate skill copies, unused candidates, and frontmatter description bloat.

## Workflow

1. Identify the roots to inspect:
   - Default roots are this repository's `skills/`, `~/.codex/skills`, `~/.codex/plugins/cache`, and `~/.agents/skills` when present.
   - Add extra roots with `--root <path>` when auditing archives, forks, or external skill collections.
2. Run the analyzer:

```bash
python3 skills/skill-cleaner/scripts/skill_cleaner.py --months 3
```

Useful variants:

```bash
python3 skills/skill-cleaner/scripts/skill_cleaner.py --no-logs
python3 skills/skill-cleaner/scripts/skill_cleaner.py --months 6 --max-log-mb 800
python3 skills/skill-cleaner/scripts/skill_cleaner.py --context-tokens 272000 --budget-percent 2
python3 skills/skill-cleaner/scripts/skill_cleaner.py --root /path/to/other/skills --no-logs
```

3. Read the report in this order:
   - `Skill Budget`: rendered skill-list token estimate, 2% budget pressure, and minimum no-description cost.
   - `Description Candidates`: long frontmatter descriptions that may be shortened without losing trigger nouns.
   - `Duplicates`: same skill name or identical bodies across repo, Codex, plugin cache, and user skill roots.
   - `Unused Candidates`: skills with no recent `$skill`, `SKILL.md` read, or skill-path evidence in scanned Codex logs.
   - `Root Summary`: which roots supplied skills and how many came from each source.
4. Before deleting or editing:
   - Verify the kept copy exists in the runtime that should load it.
   - Prefer removing exact personal or archived duplicates before editing repo skills.
   - Keep repo-local PM Copilot skills when they encode product-management policy, workflow, or delivery contracts.
   - Preserve trigger nouns in descriptions: task, artifact, platform, tool, and user wording.
5. Apply cleanup only after a human-facing recommendation is clear. Group changes by intent: description compaction, duplicate removal, config/root changes, or skill consolidation.

## Output

- Skill-budget summary
- Duplicate groups and safe-delete candidates
- Overlong description candidates
- Unused candidates with usage evidence caveat
- Root summary
- Cleanup recommendation and validation command

## Quality Bar

- The analyzer is read-only; deletion or rewriting requires an explicit follow-up action.
- `Unused Candidates` is heuristic, not proof. Do not delete a skill solely because logs lack evidence.
- Description shortening must keep recall triggers and avoid vague generic phrases.
- Duplicate removal must preserve one canonical loaded copy.
- External skill roots are treated as untrusted until source and license are reviewed.
