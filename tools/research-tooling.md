# Research Tooling

Research tools are required when the output makes source-backed claims or when competitor, benchmark, comparable feature behavior, policy, pricing, medical, legal, financial, safety, or regulated content affects the product decision.

For PRD solution shaping, external product research is expected unless the user explicitly skips it or tooling/network access is unavailable. Host repository files are current-product context, not external research evidence.

## Required Evidence

For each source-backed claim, record:

- source title
- URL or document path
- access date
- observed fact
- product implication
- confidence and limitation

## Rules

- Never cite a source that was not opened or otherwise inspected.
- If web access is unavailable, remove source-backed claims or label them as assumptions.
- Do not use model memory as current market or policy evidence.
- For high-stakes policy, medical, legal, financial, or safety claims, prefer primary or official sources.

## Output Placement

- Summarize conclusions in the PRD research/reference section.
- Store source/tool evidence in `run-log.yaml.tools_used`.
- Keep launch blockers visible when source review or content approval is missing.
