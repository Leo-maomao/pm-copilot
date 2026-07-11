#!/usr/bin/env python3
"""Regression-test inline PRD video rendering and inspection semantics."""

from __future__ import annotations

import tempfile
from pathlib import Path

from render_prd_html import convert_video_links
from validate_outputs import PRDHTMLInspectionParser


def require(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(f"FAIL {name}")
    print(f"PASS {name}")


def main() -> None:
    mov_link = '<a href="./assets/快捷键面板-底部居中.mov">快捷键面板-底部居中.mov</a>'
    rendered_mov = convert_video_links(mov_link)
    require("mov_becomes_video", '<video class="prd-video"' in rendered_mov)
    require("mov_has_controls", "controls" in rendered_mov and "playsinline" in rendered_mov)
    require("mov_has_mime", 'type="video/quicktime"' in rendered_mov)
    require("mov_keeps_fallback_link", '<a href="./assets/快捷键面板-底部居中.mov">' in rendered_mov)

    rendered_mp4 = convert_video_links('<a href="./assets/demo.mp4">Demo</a>')
    require("mp4_has_mime", 'type="video/mp4"' in rendered_mp4)

    normal_link = '<a href="./assets/spec.pdf">Specification</a>'
    require("non_video_link_unchanged", convert_video_links(normal_link) == normal_link)

    parser = PRDHTMLInspectionParser()
    parser.feed(rendered_mov)
    parser.close()
    require("video_detected", len(parser.videos) == 1)
    video = parser.videos[0]
    require("video_controls_detected", bool(video.get("controls")))
    require("video_playsinline_detected", bool(video.get("playsinline")))
    require("video_source_detected", bool(video.get("sources")))

    with tempfile.TemporaryDirectory() as directory:
        run_folder = Path(directory)
        assets = run_folder / "assets"
        assets.mkdir()
        source = assets / "sample.mov"
        source.write_bytes(b"not-a-real-video")
        unconverted = convert_video_links(
            '<a href="./assets/sample.mov">Sample</a>',
            run_folder,
        )
        require("failed_conversion_keeps_source", 'type="video/quicktime"' in unconverted)


if __name__ == "__main__":
    main()
