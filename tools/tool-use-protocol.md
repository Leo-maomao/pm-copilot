# Tool Use Protocol

PM Copilot v1 is platform-neutral. It defines tool behavior without requiring a specific tool runtime.

## Tool Decision Rules

Use tools when they improve factuality, artifact quality, or local output generation.

Do not use tools when:

- The artifact can be produced from user-provided context.
- The tool would expose sensitive data unnecessarily.
- The tool result cannot be cited or inspected.

## Tool Capability Matrix

| Capability | Use Cases | Required Disclosure | Failover |
|---|---|---|---|
| Web search | Competitor research, market examples, source-backed claims | Source title, URL, access date when available | Continue with generic assumptions and mark research unavailable |
| Web page reading | Competitor feature details, docs, pricing, policy | URL and observed facts | Ask user for source or skip source-backed claims |
| File read | Product context, templates, prior examples | File paths loaded | Ask user for missing file or continue with defaults |
| File write | Generated PRD, prototype, run log, optional exports | File paths created | Return content inline if writing is unavailable |
| Mermaid rendering | PRD flow validation | Diagram source | Keep raw Mermaid in PRD if rendering is unavailable |
| HTML preview | Prototype QA | Local file path and checked viewport | Provide static HTML and note preview not verified |

## Tool Call Record

```yaml
tool_name:
purpose:
input_summary:
output_summary:
artifact_created:
limitations:
source_or_path:
```

## Source Rules

- Never cite a source that was not accessed.
- Do not present model memory as current source-backed research.
- If a source is blocked or unavailable, say so.
