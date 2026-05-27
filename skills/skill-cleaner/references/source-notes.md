# Skill Cleaner Source Notes

## Source Snapshot

- Source: <https://github.com/steipete/agent-scripts/blob/main/skills/skill-cleaner/SKILL.md>
- Repository: <https://github.com/steipete/agent-scripts>
- Maintainer: Peter Steinberger / `steipete`
- Access date: 2026-05-26
- Observed main commit: `39cc3a18aac4d0901241c0f56233c4939252bbf6`
- License: MIT License, copyright 2026 Peter Steinberger
- Resource type: Codex skill plus analyzer script

## Absorption Decision

Decision: `Absorb` by adaptation.

PM Copilot absorbed the durable capability, not the upstream implementation verbatim. The local version keeps the same useful audit shape: skill roots, prompt-budget pressure, description length, duplicate copies, log-based usage evidence, and root summary.

## Adaptation Notes

- Rewrote the analyzer in Python standard library to match this repository's existing validation tooling.
- Added `~/.agents/skills` to the default roots because this workstation uses both `.codex` and `.agents` skill directories.
- Kept the command read-only and made deletion a separate human-approved cleanup step.
- Kept source and license notes here instead of copying upstream prose or TypeScript wholesale.

## Rejected Material

- OpenClaw-specific wording that is not needed for PM Copilot users.
- Any implication that unused-log evidence is sufficient for deletion.
- Automatic edits, deletion, or config mutation.
- Overly generic generated description suggestions; PM Copilot should preserve domain-specific trigger nouns.
