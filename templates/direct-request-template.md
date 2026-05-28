# Direct Request Template

Use this when you want to paste a request directly into an agent.

```text
<paste the product request here>

Context I know:
- Product:
- Target users:
- Platform:
- Goal:
- Constraints:
- Existing data:
- Product docs or references:

Please inspect relevant current product context first.
If there is no code repository, use the PRDs, product docs, screenshots, analytics exports, support tickets, meeting notes, or other documents I provide as current product context.
Please ask clarification questions first if any missing information materially affects current product fit, scope, metrics, tracking, UI delivery, privacy, payment, legal, compliance, or security.
If must-answer questions or unresolved `must confirm before development or launch` blockers exist, stop and wait for my answer before generating downstream artifacts.
If enough information is available, create `prd.md` and the matching UI deliverable in my request language, including localized headings, labels, statuses, UI notes, and numbered annotations. When the request is a structured reference or document handoff and I say no PRD is needed, use `catalog.md`/`reference.md` and optional document prototype HTML as the primary delivery instead. When frontend source exists, use source-backed preview/delta files; use `prototype-<platform>.html` only for no-source, explicit portable HTML, explicit redesign/greenfield, concrete source-rendering blockers, or document prototype review.
Keep confirmed MVP scope separate from optional or future scope, and mark any proposed analytics taxonomy if no existing convention is available.
Record PRD, engineering handoff, and launch readiness separately. If reference or regulated content is involved, record source, review owner, review status, disclaimer status, and launch impact.
For document-class artifacts, distinguish extracted `source_facts` from final `product_decisions`, preserve object/field/rule hierarchy, record typed `attention_points`, and keep presentation-only edits from changing content.
Do not create `task-brief.md`, `clarifying-questions.md`, `assumptions.md`, `pm-package.md`, or split Markdown files unless I ask for them or they are needed as exports.
```
