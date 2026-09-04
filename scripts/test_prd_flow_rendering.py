#!/usr/bin/env python3
"""Regression tests for paired PRD flowchart rendering."""

from __future__ import annotations

from pathlib import Path
import re
import tempfile

from render_prd_html import group_adjacent_flowcharts, inject_defaults, render_markdown_locally
from validate_outputs import check_prd_flow_sections


def require(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(f"FAIL {name}")
    print(f"PASS {name}")


def main() -> None:
    paired = (
        '<h4 id="user-flow">用户流程图</h4><pre class="mermaid">flowchart TD\nA --> B</pre>'
        '<h4 id="operation-flow">操作流程图</h4><pre class="mermaid">flowchart TD\nC --> D</pre>'
    )
    rendered = group_adjacent_flowcharts(paired)
    require("paired_flowcharts_use_grid", 'class="prd-flow-grid"' in rendered)
    require("paired_flowcharts_use_div_container", '<div class="prd-flow-grid"' in rendered)
    require("paired_flowcharts_keep_titles", "用户流程图" in rendered and "操作流程图" in rendered)
    renderer_source = Path(__file__).with_name("render_prd_html.py").read_text()
    flow_grid_rules = re.findall(r"\.prd-flow-grid\s*\{(?P<declarations>[^}]*)\}", renderer_source)
    require(
        "paired_flowcharts_remain_two_columns",
        any("grid-template-columns: repeat(2, minmax(0, 1fr));" in rule for rule in flow_grid_rules)
        and all("grid-template-columns: 1fr;" not in rule for rule in flow_grid_rules),
    )

    single = '<h4>用户流程图</h4><pre class="mermaid">flowchart TD\nA --> B</pre>'
    require("single_flowchart_unchanged", group_adjacent_flowcharts(single) == single)

    fallback = render_markdown_locally(
        """# 本地渲染测试

## 一、文档说明

| 字段 | 值 |
| --- | --- |
| 状态 | 可评审 |

```mermaid
flowchart TD
  A --> B
```

![入口](./assets/入口.png)
""",
        "本地渲染测试",
    )
    require(
        "local_renderer_preserves_prd_structure_without_pandoc",
        '<nav id="TOC">' in fallback
        and "<table>" in fallback
        and '<pre class="mermaid">' in fallback
        and '<img src="./assets/入口.png" alt="入口" />' in fallback,
    )
    with tempfile.TemporaryDirectory() as directory:
        final_fallback = inject_defaults(
            fallback,
            "# 本地渲染测试\n\n```mermaid\nflowchart TD\n  A --> B\n```\n",
            Path(directory),
        )
    require(
        "local_renderer_reaches_final_document_pipeline",
        "data-pm-copilot-prd-doc=\"true\"" in final_fallback
        and 'src="./assets/mermaid.min.js"' in final_fallback
        and "--pm-doc-bg" in final_fallback,
    )

    flow_with_table = """#### 用户流程图

```mermaid
flowchart TD
  A --> B
```

| 维度 | 需求说明 |
| --- | --- |
| 用户与场景 | 示例 |
"""
    check_prd_flow_sections(flow_with_table)
    require("flowchart_with_table_accepted", True)

    paired_flow_with_table = """#### 用户流程图

```mermaid
flowchart TD
  A --> B
```

#### 操作流程图

```mermaid
flowchart TD
  C --> D
```

| 维度 | 需求说明 |
| --- | --- |
| 用户与场景 | 示例 |
"""
    check_prd_flow_sections(paired_flow_with_table)
    require("paired_flowcharts_with_table_accepted", True)

    with tempfile.TemporaryDirectory() as directory:
        rendered_document = inject_defaults(
            '<html><head></head><body><h4>用户流程图</h4><pre class="mermaid"><code>flowchart TD\nA --&gt; B</code></pre>'
            '<h4>操作流程图</h4><pre class="mermaid"><code>flowchart TD\nC --&gt; D</code></pre></body></html>',
            "# 流程测试 - 2026-07-30",
            Path(directory),
        )
    require("inject_defaults_converts_and_groups_flowcharts", 'class="prd-flow-grid"' in rendered_document)
    require("inject_defaults_keeps_mermaid_fallback", '<pre class="mermaid">' in rendered_document)

    with tempfile.TemporaryDirectory() as directory:
        rendered_video = inject_defaults(
            '<html><head></head><body><img src="assets/拖拽演示.mp4" alt="分组框-拖拽演示" /></body></html>',
            "# 视频图示测试 - 2026-08-03",
            Path(directory),
        )
    require(
        "image_syntax_video_becomes_player",
        '<video class="prd-video" controls preload="metadata" playsinline ' in rendered_video
        and '<source src="assets/拖拽演示.mp4" type="video/mp4" />' in rendered_video
        and 'img src="assets/拖拽演示.mp4"' not in rendered_video,
    )

    with tempfile.TemporaryDirectory() as directory:
        rendered_mixed_media = inject_defaults(
            '<html><head></head><body><table><tr><td>图示</td><td>'
            '<video controls playsinline src="assets/分组框-拖拽演示.mp4"></video><small>分组框-拖拽演示</small><br>'
            '<img src="assets/分组框-颜色翻译.png" alt="分组框-颜色翻译" /><small>分组框-颜色翻译</small>'
            '</td></tr></table></body></html>',
            "# 混合图示测试 - 2026-08-03",
            Path(directory),
        )
    require(
        "mixed_media_uses_shared_caption_and_spacing",
        rendered_mixed_media.count('<div class="prd-figure-item is-wide">') == 2
        and "td video + small" in rendered_mixed_media
        and "flex-direction: column;" in rendered_mixed_media
        and "gap: 16px;" in rendered_mixed_media
        and ".prd-figure-item video" in rendered_mixed_media,
    )

    try:
        check_prd_flow_sections(flow_with_table.split("\n\n| 维度", 1)[0])
    except SystemExit:
        print("PASS flowchart_without_table_rejected")
    else:
        raise AssertionError("FAIL flowchart_without_table_rejected")


if __name__ == "__main__":
    main()
