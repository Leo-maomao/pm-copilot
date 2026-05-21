# Evaluation Case: Mini Program Style And Callout Annotations

## Metadata

| Field | Value |
|---|---|
| Case ID | mini-program-style-callout-annotation |
| Scenario | public-resources-mini-program-prototype |
| Platform | Mini Program |
| Product Area | Public resources and common tab entry |
| Created | 2026-05-18 |
| Last Updated | 2026-05-19 |

## Raw Request

```text
我们要在当前小程序的常用 tab 下增加公共资料页面，先做 MVP 原型。仓库里已有小程序 demo、页面样式和组件。
```

## Context Files

- Host mini-program page, route, or demo for the affected tab
- Existing screenshot or preview page for the current mini-program visual style
- Existing tab bar, card, typography, icon, and color references

## Expected Workflow

- Classify the run as `repo-backed` or `document-backed` based on available inputs.
- Inspect current mini-program UI evidence before prototyping.
- Preserve the current mini-program style and show the new requirement as a delta.
- Generate a source-rendered Mini Program preview when host source is available, or a fidelity-limited HTML fallback otherwise. Keep the mini-program page at its natural width, with numbered red/white borderless badge markers on the relevant components, marker-triggered dialogs, and a right-edge full-height current-state annotation panel.

## Pass Criteria

- Prototype matches the current mini-program visual style: status bar, capsule/header, tab bar, colors, spacing, typography, icon style, card radius, shadows, and layout density.
- Prototype does not look like a newly invented product shell when existing UI evidence is available.
- Every element requiring logic or interaction explanation has a visible numbered marker such as `1`, `2`, and `3` placed near that element.
- Marker dialogs and the right-edge annotation panel contain matching numbered notes grouped by page or state.
- Annotation notes are concrete and implementation-grade, for example text length limit and ellipsis rule, tap behavior, hover or tooltip behavior when applicable, long-press behavior, empty/error state, data source, permission rule, and tracking hook.
- Long notes are summarized in marker dialogs and expanded through the annotation list instead of being dumped into one generic paragraph.
- Markers and notes do not obscure key page content or controls.
- PRD records the style sources used and any style limitations.

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-05-18 | mini-program-style-drift | High | Prototype ignored the current mini-program style and looked like a different product. | Require style-source inspection and existing-surface visual matching. |
| 2026-05-18 | generic-annotation-panel | High | Notes were generic implementation paragraphs without numbered markers tied to UI elements. | Require component-corner numbered callouts, marker dialogs, and a current-state annotation list. |

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pending |
| Notes | Regression case for mini-program prototype style fidelity and numbered implementation annotations. |
