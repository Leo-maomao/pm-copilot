#!/usr/bin/env python3
"""Regression tests for paired PRD flowchart rendering."""

from __future__ import annotations

from pathlib import Path
import tempfile

from render_prd_html import group_adjacent_flowcharts, inject_defaults
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
    require(
        "paired_flowcharts_remain_two_columns",
        "grid-template-columns: repeat(2, minmax(0, 1fr));" in renderer_source
        and "grid-template-columns: 1fr;" not in renderer_source,
    )

    single = '<h4>用户流程图</h4><pre class="mermaid">flowchart TD\nA --> B</pre>'
    require("single_flowchart_unchanged", group_adjacent_flowcharts(single) == single)

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

    try:
        check_prd_flow_sections(flow_with_table.split("\n\n| 维度", 1)[0])
    except SystemExit:
        print("PASS flowchart_without_table_rejected")
    else:
        raise AssertionError("FAIL flowchart_without_table_rejected")


if __name__ == "__main__":
    main()
