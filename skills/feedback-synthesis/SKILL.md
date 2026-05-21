---
name: feedback-synthesis
description: Use when synthesizing user interviews, support tickets, sales calls, app reviews, survey exports, Slack feedback, NPS comments, or research notes into product insights.
---

# Feedback Synthesis

## Goal

Turn messy qualitative feedback into prioritized product insights while preserving evidence, segment, confidence, and bias limitations.

## Workflow

1. Identify source type, date range, segment, channel, sample size, and collection bias.
2. Redact sensitive customer data before synthesis when possible.
3. Normalize feedback into atomic observations: user, context, problem, quote or paraphrase, severity, frequency, workaround, desired outcome.
4. Cluster observations by job-to-be-done, journey step, failure mode, product area, or decision theme.
5. Separate user pain from proposed solution. Treat user-suggested features as evidence of a need, not automatic scope.
6. Estimate confidence using frequency, recency, segment relevance, evidence quality, and triangulation with analytics or support data.
7. Identify contradictions and underserved segments.
8. Convert clusters into product implications: fix now, discover more, monitor, reject, or route to another team.
9. Preserve representative quotes only when allowed; otherwise use anonymized paraphrases.

## Boundary

Use this skill to turn raw qualitative feedback into evidence clusters. Use `skills/opportunity-discovery/SKILL.md` to decide which validated opportunities should enter PRD scope. Do not create separate interview-synthesis, ticket-synthesis, or review-mining skills; extend this one.

## Output

- Source inventory and bias note
- Theme clusters with evidence count and confidence
- Problem statements and affected segments
- Opportunity or requirement implications
- Open questions for discovery
- Redaction and privacy notes

## Quality Bar

- The synthesis does not overstate small or biased samples.
- Raw sensitive data is not copied into public artifacts.
- Themes include evidence, not just labels.
- Recommendations distinguish pain severity from build priority.
- Contradictory feedback remains visible.
