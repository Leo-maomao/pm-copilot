#!/usr/bin/env python3
"""Render `prd.md` into a browser-readable `prd.html` with PM Copilot defaults."""

from __future__ import annotations

import argparse
import html as html_lib
import re
import shutil
import subprocess
import sys
from urllib.parse import unquote, urlparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENDORED_MERMAID_RUNTIME = ROOT / "vendor" / "mermaid" / "mermaid.min.js"
VIDEO_EXTENSIONS = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".m4v": "video/x-m4v",
    ".ogv": "video/ogg",
    ".ogg": "video/ogg",
}

DOCUMENT_CSS = """
    :root {
      color-scheme: light;
      --pm-doc-bg: #fff;
      --pm-doc-text: #1f2937;
      --pm-doc-muted: #6b7280;
      --pm-doc-border: #e5e7eb;
      --pm-doc-soft: #f9fafb;
      --pm-doc-soft-strong: #f3f4f6;
      --pm-doc-accent: #2563eb;
      --pm-doc-accent-soft: #e8f0ff;
    }
    html {
      background: var(--pm-doc-bg);
      scroll-behavior: smooth;
    }
    body {
      box-sizing: border-box;
      width: auto;
      max-width: none;
      min-height: 100vh;
      margin: 0;
      padding: 40px 56px 80px 308px;
      background: var(--pm-doc-bg);
      color: var(--pm-doc-text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      font-size: 15px;
      line-height: 1.68;
      overflow-wrap: anywhere;
    }
    h1 {
      margin: 0 0 28px;
      font-size: 34px;
      line-height: 1.2;
    }
    h2 {
      margin-top: 40px;
      padding-top: 12px;
      border-top: 1px solid var(--pm-doc-border);
      font-size: 24px;
    }
    h3 {
      margin-top: 28px;
      font-size: 18px;
    }
    .prd-flow-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      margin: 16px 0;
    }
    .prd-flow-pane {
      min-width: 0;
      padding: 16px;
      border: 1px solid var(--pm-doc-border);
      background: var(--pm-doc-soft);
    }
    .prd-flow-pane h4 {
      margin: 0 0 12px;
      font-size: 15px;
    }
    .prd-flow-pane pre.mermaid {
      margin: 0;
      overflow: auto;
    }
    h1[id],
    h2[id],
    h3[id],
    h4[id],
    h5[id],
    h6[id] {
      scroll-margin-top: 16px;
    }
    a {
      color: var(--pm-doc-accent);
    }
    code {
      padding: 1px 4px;
      border-radius: 4px;
      background: var(--pm-doc-soft-strong);
      color: #111827;
      overflow-wrap: anywhere;
      word-break: break-word;
      line-height: 1.65;
    }
    pre code {
      padding: 0;
      background: transparent;
    }
    #TOC {
      position: fixed;
      top: 0;
      bottom: 0;
      left: 0;
      width: 252px;
      box-sizing: border-box;
      padding: 24px 18px 32px;
      overflow: auto;
      border-right: 1px solid var(--pm-doc-border);
      background: var(--pm-doc-soft);
      font-size: 13px;
      line-height: 1.45;
    }
    #TOC::before {
      content: "目录";
      display: block;
      margin: 0 0 14px;
      color: #111827;
      font-size: 14px;
      font-weight: 700;
    }
    #TOC > ul {
      margin: 0;
      padding-left: 0;
    }
    #TOC li {
      margin: 6px 0;
      list-style: none;
    }
    #TOC ul ul {
      padding-left: 14px;
    }
    #TOC ul ul ul {
      padding-left: 12px;
      font-size: 12px;
    }
    #TOC ul ul ul li {
      margin: 4px 0;
    }
    #TOC a {
      display: block;
      box-sizing: border-box;
      margin-left: -6px;
      padding: 3px 6px;
      width: calc(100% + 12px);
      border-radius: 6px;
      color: #374151;
      font-weight: 400;
      text-decoration: none;
      overflow-wrap: anywhere;
      word-break: break-word;
    }
    #TOC a * {
      font-weight: 400;
    }
    #TOC a:hover {
      background: #eef2ff;
      color: #1d4ed8;
    }
    #TOC a.is-active {
      background: var(--pm-doc-accent-soft);
      color: #1d4ed8;
    }
    #TOC a code {
      padding: 0;
      background: transparent;
      color: inherit;
      font: inherit;
    }
    @media (max-width: 900px) {
      body {
        padding: 32px 28px 64px;
      }
      #TOC {
        position: static;
        width: auto;
        margin: 0 0 28px;
        border: 1px solid var(--pm-doc-border);
      }
    }
    table {
      display: table;
      width: 100%;
      table-layout: auto;
      border-collapse: collapse;
      border: 1px solid var(--pm-doc-border);
      font-size: 13px;
    }
    colgroup col {
      width: auto !important;
    }
    table:has(th:nth-child(2):last-child) th:first-child,
    table:has(th:nth-child(2):last-child) td:first-child {
      width: 24%;
      min-width: 168px;
      max-width: 320px;
      white-space: nowrap;
    }
    table:has(th:nth-child(2):last-child) th:nth-child(2),
    table:has(th:nth-child(2):last-child) td:nth-child(2) {
      width: auto;
    }
    thead {
      background: var(--pm-doc-soft-strong);
    }
    tbody {
      border: 0;
    }
    th,
    td {
      border: 1px solid var(--pm-doc-border);
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
      overflow-wrap: anywhere;
      word-break: break-word;
    }
    figure {
      margin: 16px 0 24px;
    }
    figure img,
    td img,
    figure video,
    td video {
      display: block;
      max-width: 100%;
      max-height: calc(100vh - 160px);
      border: 1px solid var(--pm-doc-border);
      border-radius: 8px;
      background: var(--pm-doc-bg);
      cursor: zoom-in;
      object-fit: contain;
    }
    figure video,
    td video {
      width: min(100%, 960px);
      min-height: 180px;
      background: #111827;
      cursor: default;
    }
    td img {
      margin: 0;
      max-height: none;
      height: auto;
    }
    td img + small,
    td video + small {
      display: block;
      margin-top: 2px;
      color: var(--pm-doc-muted);
      font-size: 12px;
      line-height: 1.5;
    }
    .prd-figure-grid {
      display: flex;
      flex-direction: column;
      gap: 16px;
      margin: 0;
    }
    .prd-figure-item {
      min-width: 0;
    }
    .prd-figure-item.is-wide {
      grid-column: 1 / -1;
    }
    .prd-figure-item img,
    .prd-figure-item video {
      display: block;
      width: 100%;
      max-width: 100%;
      height: auto;
      margin: 0;
      max-height: none;
    }
    .prd-figure-item small {
      display: block;
      margin-top: 2px;
      color: var(--pm-doc-muted);
      font-size: 12px;
      line-height: 1.5;
    }
    .prd-detail-media-stack {
      display: flex;
      flex-direction: column;
      gap: 18px;
    }
    .prd-detail-text-block {
      padding: 0 0 18px;
      border-bottom: 1px solid var(--pm-doc-border);
    }
    .prd-detail-text-block:last-child {
      padding-bottom: 0;
      border-bottom: 0;
    }
    .prd-detail-media-block {
      display: grid;
      grid-template-columns: 240px minmax(0, 1fr);
      gap: 24px;
      align-items: start;
      padding: 0 0 18px;
      border-bottom: 1px solid var(--pm-doc-border);
    }
    .prd-detail-media-block:last-child {
      padding-bottom: 0;
      border-bottom: 0;
    }
    .prd-detail-media-block .prd-detail-media {
      width: 240px;
      min-height: 140px;
      display: grid;
      place-items: start center;
    }
    .prd-detail-media-block img,
    .prd-detail-media-block video {
      width: auto;
      max-width: 240px;
      max-height: 260px;
      margin: 0;
    }
    .prd-detail-media-block .prd-detail-copy {
      min-width: 0;
    }
    .prd-detail-media-block .prd-detail-copy small {
      display: none;
    }
    @media (max-width: 900px) {
      .prd-detail-media-block {
        grid-template-columns: 1fr;
      }
      .prd-detail-media-block .prd-detail-media {
        width: 100%;
      }
    }
    figcaption {
      margin-top: 8px;
      color: var(--pm-doc-muted);
      font-size: 13px;
      text-align: left;
    }
    .image-lightbox {
      position: fixed;
      inset: 0;
      z-index: 1000;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 32px;
      background: rgba(17, 24, 39, 0.82);
    }
    .image-lightbox.is-open {
      display: flex;
    }
    .image-lightbox img {
      max-width: 96vw;
      max-height: 92vh;
      border-radius: 8px;
      background: #fff;
      box-shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
      object-fit: contain;
    }
    .image-lightbox button {
      position: fixed;
      top: 18px;
      right: 18px;
      min-width: 72px;
      height: 36px;
      border: 0;
      border-radius: 6px;
      background: #fff;
      color: #111827;
      font-size: 14px;
      cursor: pointer;
    }
    .mermaid {
      margin: 18px 0 24px;
      padding: 16px;
      overflow-x: auto;
      border: 1px solid var(--pm-doc-border);
      border-radius: 8px;
      background: var(--pm-doc-soft);
      text-align: center;
    }
    .mermaid svg {
      max-width: 100%;
      height: auto;
    }
    @media (max-width: 900px) {
      body {
        padding: 24px 16px 56px;
        font-size: 14px;
      }
      #TOC {
        position: static;
        width: auto;
        margin: -24px -16px 24px;
        border-right: 0;
        border-bottom: 1px solid var(--pm-doc-border);
      }
      h1 {
        font-size: 28px;
      }
      table {
        display: block;
        overflow-x: auto;
        table-layout: auto;
        white-space: normal;
      }
    }
"""


LIGHTBOX_HTML_TEMPLATE = """
<div class="image-lightbox" id="image-lightbox" role="dialog" aria-modal="true" aria-label="__DIALOG_LABEL__" aria-hidden="true">
<button type="button">__CLOSE_LABEL__</button>
<img src="__INITIAL_SRC__" data-initial-src="__INITIAL_SRC__" alt="" />
</div>
<script>
(() => {
  const lightbox = document.getElementById('image-lightbox');
  if (!lightbox) return;
  const lightboxImage = lightbox.querySelector('img');
  const closeButton = lightbox.querySelector('button');
  let triggerImage = null;

  const close = () => {
    if (!lightbox.classList.contains('is-open')) return;
    lightbox.classList.remove('is-open');
    lightbox.setAttribute('aria-hidden', 'true');
    lightboxImage.src = lightboxImage.dataset.initialSrc || '';
    lightboxImage.setAttribute('alt', '');
    triggerImage?.focus({ preventScroll: true });
    triggerImage = null;
  };

  Array.from(document.querySelectorAll('figure img, td img')).forEach((image) => {
    const open = () => {
      triggerImage = image;
      lightboxImage.src = image.src;
      lightboxImage.alt = image.alt || '';
      lightbox.classList.add('is-open');
      lightbox.setAttribute('aria-hidden', 'false');
      closeButton.focus({ preventScroll: true });
    };
    image.setAttribute('tabindex', '0');
    image.setAttribute('role', 'button');
    image.setAttribute('aria-haspopup', 'dialog');
    image.setAttribute('aria-label', image.alt || '__OPEN_IMAGE_LABEL__');
    image.addEventListener('click', open);
    image.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        open();
      }
    });
  });

  closeButton.addEventListener('click', close);
  lightbox.addEventListener('click', (event) => {
    if (event.target === lightbox) close();
  });
  document.addEventListener('keydown', (event) => {
    if (!lightbox.classList.contains('is-open')) return;
    if (event.key === 'Escape') close();
    if (event.key === 'Tab') {
      event.preventDefault();
      closeButton.focus({ preventScroll: true });
    }
  });
})();
</script>
"""


TOC_TRACKING_SCRIPT = """
<script>
(() => {
  const toc = document.getElementById('TOC');
  if (!toc) return;
  const links = Array.from(toc.querySelectorAll('a[href^="#"]'));
  const sections = Array.from(document.querySelectorAll('h2[id], h3[id], h4[id]'));
  if (!links.length || !sections.length) return;
  const linkById = new Map(
    links.map((link) => [decodeURIComponent(link.getAttribute('href').slice(1)), link])
  );

  const setActive = (id) => {
    links.forEach((link) => link.classList.remove('is-active'));
    const active = linkById.get(id);
    if (!active) return;
    active.classList.add('is-active');
    active.scrollIntoView({ block: 'nearest' });
  };

  // Use one geometric rule for every scroll position. Observer entry order is
  // not stable when adjacent headings cross the observation band together.
  let activeId = '';
  let updateScheduled = false;
  const updateActive = () => {
    updateScheduled = false;
    const threshold = 32;
    let current = sections[0];
    sections.forEach((section) => {
      if (section.getBoundingClientRect().top <= threshold) current = section;
    });
    if (current?.id && current.id !== activeId) {
      activeId = current.id;
      setActive(activeId);
    }
  };
  const scheduleUpdate = () => {
    if (updateScheduled) return;
    updateScheduled = true;
    window.requestAnimationFrame(updateActive);
  };

  const observer = new IntersectionObserver((entries) => {
    if (entries.length) scheduleUpdate();
  }, { rootMargin: '-20% 0px -70% 0px', threshold: [0, 1] });

  sections.forEach((section) => observer.observe(section));
  window.addEventListener('scroll', scheduleUpdate, { passive: true });
  window.addEventListener('resize', scheduleUpdate, { passive: true });
  updateActive();
})();
</script>
"""


MERMAID_INIT_SCRIPT = """
<script src="./assets/mermaid.min.js"></script>
<script>
(() => {
  if (!window.mermaid) return;
  window.mermaid.initialize({
    startOnLoad: true,
    securityLevel: 'strict',
    theme: 'default',
    flowchart: { htmlLabels: false, curve: 'basis' }
  });
})();
</script>
"""


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    sys.exit(1)


def first_markdown_h1(text: str) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
    if not match:
        return "PM Copilot PRD"
    return re.sub(r"\s+", " ", match.group(1)).strip()


def infer_close_label(markdown: str) -> str:
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", markdown))
    latin_words = len(re.findall(r"\b[A-Za-z]{3,}\b", markdown))
    return "关闭" if chinese_chars >= latin_words else "Close"


def infer_document_language(markdown: str) -> str:
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", markdown))
    latin_words = len(re.findall(r"\b[A-Za-z]{3,}\b", markdown))
    return "zh-CN" if chinese_chars >= latin_words else "en"


def html_contains_images(html: str) -> bool:
    return bool(re.search(r"<img\b", html, re.IGNORECASE))


def first_image_src(html: str) -> str:
    match = re.search(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", html, re.IGNORECASE)
    return match.group(1) if match else ""


def markdown_needs_assets_folder(markdown: str) -> bool:
    refs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", markdown)
    refs.extend(re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", markdown))
    refs.extend(re.findall(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", markdown, re.IGNORECASE))
    for ref in refs:
        normalized = ref.strip().split("#", 1)[0].split("?", 1)[0].replace("\\", "/")
        if normalized.startswith("./assets/") or normalized.startswith("assets/"):
            return True
    return False


def video_mime_type(target: str) -> str:
    normalized = unquote(html_lib.unescape(target)).split("#", 1)[0].split("?", 1)[0]
    return VIDEO_EXTENSIONS.get(Path(normalized).suffix.lower(), "")


def browser_video_target(target: str, run_folder: Path | None) -> tuple[str, str]:
    mime_type = video_mime_type(target)
    if not run_folder or mime_type not in {"video/quicktime", "video/x-m4v"}:
        return target, mime_type

    decoded = unquote(html_lib.unescape(target))
    clean_target = decoded.split("#", 1)[0].split("?", 1)[0]
    source_path = (run_folder / clean_target).resolve()
    try:
        source_path.relative_to(run_folder.resolve())
    except ValueError:
        return target, mime_type
    if not source_path.is_file():
        return target, mime_type

    output_path = source_path.with_name(f"{source_path.stem}.browser.mp4")
    if not output_path.is_file() or output_path.stat().st_mtime < source_path.stat().st_mtime:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return target, mime_type
        remux = subprocess.run(
            [
                ffmpeg, "-y", "-i", str(source_path), "-map", "0:v:0", "-map", "0:a?",
                "-c", "copy", "-movflags", "+faststart", str(output_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if remux.returncode != 0:
            transcode = subprocess.run(
                [
                    ffmpeg, "-y", "-i", str(source_path), "-map", "0:v:0", "-map", "0:a?",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-movflags", "+faststart", str(output_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if transcode.returncode != 0:
                output_path.unlink(missing_ok=True)
                return target, mime_type

    relative_output = output_path.relative_to(run_folder.resolve()).as_posix()
    if clean_target.startswith("./"):
        relative_output = f"./{relative_output}"
    return relative_output, "video/mp4"


def convert_video_links(html: str, run_folder: Path | None = None) -> str:
    link_pattern = re.compile(
        r"<a(?P<attrs>[^>]*?)\bhref=(?P<quote>[\"'])(?P<href>[^\"']+)(?P=quote)(?P<tail>[^>]*)>"
        r"(?P<label>.*?)</a>",
        re.IGNORECASE | re.DOTALL,
    )

    def player(target: str, label_text: str) -> str:
        playback_href, playback_mime_type = browser_video_target(target, run_folder)
        escaped_href = html_lib.escape(html_lib.unescape(target), quote=True)
        escaped_playback_href = html_lib.escape(html_lib.unescape(playback_href), quote=True)
        escaped_label = html_lib.escape(label_text, quote=False)
        return (
            f'<video class="prd-video" controls preload="metadata" playsinline '
            f'aria-label="{html_lib.escape(label_text, quote=True)}">'
            f'<source src="{escaped_playback_href}" type="{playback_mime_type}" />'
            f'<span>当前浏览器无法直接播放此视频。'
            f'<a href="{escaped_href}">打开 {escaped_label}</a></span>'
            f'</video>'
        )

    def replace_link(match: re.Match[str]) -> str:
        href = match.group("href")
        if not video_mime_type(href):
            return match.group(0)
        label_text = visible_text_from_html(match.group("label")) or Path(unquote(href)).name
        return player(href, label_text)

    image_pattern = re.compile(
        r"<img(?P<attrs>[^>]*?)\bsrc=(?P<quote>[\"'])(?P<src>[^\"']+)(?P=quote)(?P<tail>[^>]*)/?>",
        re.IGNORECASE | re.DOTALL,
    )

    def replace_image(match: re.Match[str]) -> str:
        src = match.group("src")
        if not video_mime_type(src):
            return match.group(0)
        alt_match = re.search(
            r"\balt=(?P<quote>[\"'])(?P<alt>[^\"']*)(?P=quote)",
            match.group(0),
            re.IGNORECASE,
        )
        label_text = html_lib.unescape(alt_match.group("alt")) if alt_match else Path(unquote(src)).name
        return player(src, label_text or Path(unquote(src)).name)

    return image_pattern.sub(replace_image, link_pattern.sub(replace_link, html))


def ensure_assets_dir(run_folder: Path) -> Path:
    assets_dir = run_folder / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    return assets_dir


def convert_mermaid_blocks(html: str) -> str:
    pattern = re.compile(
        r"<pre([^>]*)class=[\"']([^\"']*\bmermaid\b[^\"']*)[\"']([^>]*)>\s*"
        r"<code[^>]*>(.*?)</code>\s*</pre>",
        re.IGNORECASE | re.DOTALL,
    )

    def replace(match: re.Match[str]) -> str:
        before_attrs = match.group(1)
        classes = match.group(2)
        after_attrs = match.group(3)
        code = html_lib.unescape(match.group(4)).strip()
        return f'<pre{before_attrs}class="{classes}"{after_attrs}>{html_lib.escape(code)}</pre>'

    return pattern.sub(replace, html)


def group_adjacent_flowcharts(html: str) -> str:
    mermaid_pre = r"<pre\b[^>]*\bclass=[\"'][^\"']*\bmermaid\b[^\"']*[\"'][^>]*>.*?</pre>"
    heading = r"<h4\b[^>]*>.*?</h4>"
    pattern = re.compile(
        rf"(?P<user>{heading}\s*{mermaid_pre})\s*(?P<operation>{heading}\s*{mermaid_pre})",
        re.IGNORECASE | re.DOTALL,
    )

    def title_of(block: str) -> str:
        match = re.search(r"<h4\b[^>]*>(.*?)</h4>", block, re.IGNORECASE | re.DOTALL)
        return visible_text_from_html(match.group(1)) if match else ""

    def replace(match: re.Match[str]) -> str:
        user = match.group("user")
        operation = match.group("operation")
        titles = {title_of(user), title_of(operation)}
        if titles != {"用户流程图", "操作流程图"}:
            return match.group(0)
        return (
            '<div class="prd-flow-grid" role="group" aria-label="流程图">'
            f'<div class="prd-flow-pane">{user}</div>'
            f'<div class="prd-flow-pane">{operation}</div>'
            "</div>"
        )

    return pattern.sub(replace, html)


def remove_h1_from_toc(html: str) -> str:
    toc_match = re.search(
        r"<(?P<tag>nav|div)\b(?P<attrs>[^>]*)\bid=\"TOC\"(?P<attrs_after>[^>]*)>.*?</(?P=tag)>",
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if not toc_match:
        return html
    toc = toc_match.group(0)
    compact_match = re.fullmatch(
        r"(?P<prefix><(?P<tag>nav|div)\b[^>]*\bid=\"TOC\"[^>]*>\s*<ul>\s*)"
        r"<li>\s*<a\b(?=[^>]*\bhref\s*=\s*[\"']#document-title[\"'])[^>]*>.*?</a>\s*<ul>\s*"
        r"(?P<items>.*?)"
        r"\s*</ul>\s*</li>\s*"
        r"(?P<suffix></ul>\s*</(?P=tag)>)",
        toc,
        re.IGNORECASE | re.DOTALL,
    )
    if not compact_match:
        return html
    cleaned_toc = compact_match.group("prefix") + compact_match.group("items") + compact_match.group("suffix")
    return html[:toc_match.start()] + cleaned_toc + html[toc_match.end():]


def normalize_html_shell(html: str, language: str) -> str:
    html = re.sub(r"<html\b[^>]*>", f'<html lang="{language}">', html, count=1, flags=re.IGNORECASE)
    html = html.replace("<body>", '<body data-pm-copilot-prd-doc="true">', 1)
    html = re.sub(
        r"<nav\b([^>]*)\bid=\"TOC\"([^>]*)>",
        r'<div\1id="TOC"\2 data-pm-copilot-toc="fixed">',
        html,
        count=1,
        flags=re.IGNORECASE,
    )
    html = re.sub(r"</nav>", "</div>", html, count=1, flags=re.IGNORECASE)
    html = re.sub(
        r"\s*\*\* See https://pandoc\.org/MANUAL\.html#variables-for-html for config info\.\n",
        "\n",
        html,
        count=1,
    )
    return html


def replace_document_styles(html: str) -> str:
    style = f"<style>\n{DOCUMENT_CSS}\n  </style>"
    if re.search(r"<style\b[^>]*>.*?</style>", html, re.IGNORECASE | re.DOTALL):
        return re.sub(
            r"<style\b[^>]*>.*?</style>",
            style,
            html,
            count=1,
            flags=re.IGNORECASE | re.DOTALL,
        )
    return html.replace("</head>", f"{style}\n</head>", 1)


def visible_text_from_html(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html_lib.unescape(text)).strip()


REQUIREMENT_IMAGE_LABEL_RE = re.compile(
    r"^(?:需求图|截图|图示|图片|requirement image|screenshot|figure|image)$",
    re.IGNORECASE,
)
TABLE_ROW_RE = re.compile(r"<tr\b[^>]*>.*?</tr>", re.IGNORECASE | re.DOTALL)
TABLE_CELL_RE = re.compile(r"<td(?P<attrs>[^>]*)>(?P<body>.*?)</td>", re.IGNORECASE | re.DOTALL)
REQUIREMENT_IMAGE_CELL_RE = re.compile(
    r"<img\b|<video\b|占位图|图片占位|截图占位|image placeholder|screenshot placeholder",
    re.IGNORECASE,
)
FIGURE_PAIR_RE = re.compile(
    r"(?P<image><(?:img\b[^>]*>|video\b[^>]*>.*?</video>))\s*(?P<caption><small>.*?</small>)",
    re.IGNORECASE | re.DOTALL,
)
DETAIL_MEDIA_PAIR_RE = re.compile(
    r"(?P<image><(?:img\b[^>]*>|video\b[^>]*>.*?</video>))\s*"
    r"(?:<small>.*?</small>)?\s*(?:<br\s*/?>\s*)*(?P<copy><sub>.*?</sub>)?",
    re.IGNORECASE | re.DOTALL,
)
IMAGE_SRC_RE = re.compile(r"\bsrc\s*=\s*([\"'])(?P<src>.*?)\1", re.IGNORECASE | re.DOTALL)
WIDE_FIGURE_MIN_WIDTH = 1000
WIDE_FIGURE_MIN_RATIO = 1.45


def html_cell_is_empty(body: str) -> bool:
    return not visible_text_from_html(body).replace("\xa0", "").strip() and not REQUIREMENT_IMAGE_CELL_RE.search(body)


def set_colspan(attrs: str, colspan: int) -> str:
    if re.search(r"\bcolspan\s*=", attrs, re.IGNORECASE):
        return re.sub(
            r"\scolspan\s*=\s*([\"'])[^\"']*\1",
            f' colspan="{colspan}"',
            attrs,
            count=1,
            flags=re.IGNORECASE,
        )
    return f'{attrs} colspan="{colspan}"'


def merge_requirement_image_table_cells(html: str) -> str:
    """Make figure-only table rows span all content columns after the label cell."""

    def replace_row(match: re.Match[str]) -> str:
        row = match.group(0)
        cells = list(TABLE_CELL_RE.finditer(row))
        if len(cells) < 3:
            return row

        label = visible_text_from_html(cells[0].group("body"))
        if not REQUIREMENT_IMAGE_LABEL_RE.fullmatch(label):
            return row

        image_index = next(
            (
                index
                for index, cell in enumerate(cells[1:], start=1)
                if REQUIREMENT_IMAGE_CELL_RE.search(cell.group("body"))
            ),
            None,
        )
        if image_index is None or image_index >= len(cells) - 1:
            return row

        trailing_cells = cells[image_index + 1:]
        if not trailing_cells or not all(html_cell_is_empty(cell.group("body")) for cell in trailing_cells):
            return row

        image_cell = cells[image_index]
        colspan = len(cells) - image_index
        merged_attrs = set_colspan(image_cell.group("attrs"), colspan)
        merged_cell = f'<td{merged_attrs}>{image_cell.group("body")}</td>'
        return row[:image_cell.start()] + merged_cell + row[cells[-1].end():]

    return TABLE_ROW_RE.sub(replace_row, html)


def local_image_dimensions(path: Path) -> tuple[int, int] | None:
    """Read common raster dimensions without optional image-processing dependencies."""
    try:
        header = path.read_bytes()[:64]
    except OSError:
        return None

    if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
        return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")
    if header.startswith((b"GIF87a", b"GIF89a")) and len(header) >= 10:
        return int.from_bytes(header[6:8], "little"), int.from_bytes(header[8:10], "little")
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP" and len(header) >= 30:
        chunk_type = header[12:16]
        if chunk_type == b"VP8X":
            return (
                int.from_bytes(header[24:27], "little") + 1,
                int.from_bytes(header[27:30], "little") + 1,
            )
        if chunk_type == b"VP8 ":
            return (
                int.from_bytes(header[26:28], "little") & 0x3FFF,
                int.from_bytes(header[28:30], "little") & 0x3FFF,
            )
        if chunk_type == b"VP8L" and len(header) >= 25:
            bits = int.from_bytes(header[21:25], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if header.startswith(b"\xff\xd8"):
        try:
            with path.open("rb") as image_file:
                image_file.read(2)
                while True:
                    marker_prefix = image_file.read(1)
                    while marker_prefix == b"\xff":
                        marker_prefix = image_file.read(1)
                    if not marker_prefix:
                        return None
                    marker = marker_prefix[0]
                    if marker in {0xD8, 0xD9}:
                        continue
                    size = int.from_bytes(image_file.read(2), "big")
                    if size < 2:
                        return None
                    if 0xC0 <= marker <= 0xC3 or 0xC5 <= marker <= 0xC7 or 0xC9 <= marker <= 0xCB or 0xCD <= marker <= 0xCF:
                        data = image_file.read(5)
                        if len(data) != 5:
                            return None
                        return int.from_bytes(data[3:5], "big"), int.from_bytes(data[1:3], "big")
                    image_file.seek(size - 2, 1)
        except OSError:
            return None
    return None


def figure_item_class(image_html: str, run_folder: Path | None) -> str:
    """Keep unreadable or unknown images full-width; group compact evidence side by side."""
    if run_folder is None:
        return "prd-figure-item"
    src_match = IMAGE_SRC_RE.search(image_html)
    if src_match is None:
        return "prd-figure-item is-wide"
    parsed = urlparse(html_lib.unescape(src_match.group("src")))
    if parsed.scheme or parsed.netloc:
        return "prd-figure-item is-wide"
    source = unquote(parsed.path)
    image_path = (run_folder / source).resolve()
    try:
        image_path.relative_to(run_folder.resolve())
    except ValueError:
        return "prd-figure-item is-wide"
    dimensions = local_image_dimensions(image_path)
    if dimensions is None:
        return "prd-figure-item is-wide"
    width, height = dimensions
    ratio = width / max(height, 1)
    if width >= WIDE_FIGURE_MIN_WIDTH or ratio >= WIDE_FIGURE_MIN_RATIO:
        return "prd-figure-item is-wide"
    return "prd-figure-item"


def group_requirement_figure_pairs(html: str, run_folder: Path | None = None) -> str:
    """Render multiple image-caption pairs in one detail cell as an adaptive figure grid."""

    def replace_cell(match: re.Match[str]) -> str:
        body = match.group("body")
        pairs = list(FIGURE_PAIR_RE.finditer(body))
        if len(pairs) < 2:
            return match.group(0)
        remainder = FIGURE_PAIR_RE.sub("", body)
        remainder = re.sub(r"<br\s*/?>", "", remainder, flags=re.IGNORECASE)
        if visible_text_from_html(remainder).replace("\xa0", "").strip():
            return match.group(0)
        items = "".join(
            f'<div class="{figure_item_class(pair.group("image"), run_folder)}">'
            f'{pair.group("image")}{pair.group("caption")}'
            "</div>"
            for pair in pairs
        )
        return f'<td{match.group("attrs")}><div class="prd-figure-grid">{items}</div></td>'

    return TABLE_CELL_RE.sub(replace_cell, html)


def merge_legacy_requirement_detail_media(html: str) -> str:
    """Move legacy standalone figure rows into the single detail cell as fixed-column blocks."""

    def replace_table(table_match: re.Match[str]) -> str:
        table = table_match.group(0)
        rows = list(TABLE_ROW_RE.finditer(table))
        detail_indices = []
        figure_index = None
        for index, row_match in enumerate(rows):
            cells = list(TABLE_CELL_RE.finditer(row_match.group(0)))
            if len(cells) != 2:
                continue
            label = visible_text_from_html(cells[0].group("body"))
            if label == "需求详情":
                detail_indices.append(index)
            elif REQUIREMENT_IMAGE_LABEL_RE.fullmatch(label):
                figure_index = index
        if not detail_indices or figure_index is None or figure_index <= detail_indices[-1]:
            return table
        detail_index = detail_indices[-1]
        detail_cells = list(TABLE_CELL_RE.finditer(rows[detail_index].group(0)))
        figure_cells = list(TABLE_CELL_RE.finditer(rows[figure_index].group(0)))
        if len(detail_cells) != 2 or len(figure_cells) != 2:
            return table
        figures = list(DETAIL_MEDIA_PAIR_RE.finditer(figure_cells[1].group("body")))
        if not figures:
            return table
        blocks = []
        for figure in figures:
            copy = figure.group("copy") or ""
            copy = re.sub(r"</?sub\b[^>]*>", "", copy, flags=re.IGNORECASE)
            copy = re.sub(r"^\s*用途\s*[:：]\s*", "", copy)
            copy = copy.strip()
            copy_html = f'<div class="prd-detail-copy">{copy}</div>' if copy else ""
            blocks.append(
                '<div class="prd-detail-media-block">'
                f'<div class="prd-detail-media">{figure.group("image")}</div>'
                f'{copy_html}'
                "</div>"
            )
        detail_body = detail_cells[1].group("body")
        # Legacy PRDs kept all rules in one text cell and captions in a later
        # figure row. Split the rule groups across figures so no image inherits
        # the entire requirement narrative. The explicit media-block syntax in
        # new PRDs remains the preferred source format.
        groups = re.split(r"(?=<strong>[^<]+</strong>)", detail_body)
        groups = [group.strip() for group in groups if visible_text_from_html(group).strip()]
        if len(groups) > 1 and len(figures) > 1:
            buckets = ["" for _ in figures]
            for index, group in enumerate(groups):
                bucket = min(index * len(figures) // len(groups), len(figures) - 1)
                buckets[bucket] += ("<br>" if buckets[bucket] else "") + group
        else:
            buckets = [detail_body] + ["" for _ in figures[1:]]
        blocks = []
        for index, figure in enumerate(figures):
            copy = buckets[index]
            headings = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
            heading_index = 0
            def renumber_heading(_: re.Match[str]) -> str:
                nonlocal heading_index
                value = headings[min(heading_index, len(headings) - 1)]
                heading_index += 1
                return f"<strong>{value}、"
            copy = re.sub(r"<strong>[^<、]+、", renumber_heading, copy)
            copy = re.sub(r"<small>.*?</small>", "", copy, flags=re.IGNORECASE | re.DOTALL)
            copy = re.sub(r"^\s*用途\s*[:：]\s*", "", copy)
            copy_html = f'<div class="prd-detail-copy">{copy}</div>' if copy else ""
            blocks.append(
                '<div class="prd-detail-media-block">'
                f'<div class="prd-detail-media">{figure.group("image")}</div>'
                f'{copy_html}'
                "</div>"
            )
        prior_text_blocks = []
        for prior_index in detail_indices[:-1]:
            prior_cells = list(TABLE_CELL_RE.finditer(rows[prior_index].group(0)))
            if len(prior_cells) == 2:
                prior_text_blocks.append(
                    f'<div class="prd-detail-text-block">{prior_cells[1].group("body")}</div>'
                )
        detail_body = '<div class="prd-detail-media-stack">' + "".join(prior_text_blocks + blocks) + "</div>"
        first_detail_index = detail_indices[0]
        first_detail_row = rows[first_detail_index].group(0)
        first_detail_cells = list(TABLE_CELL_RE.finditer(first_detail_row))
        detail_cell = first_detail_cells[1]
        replacement = f'<td{detail_cell.group("attrs")}>{detail_body}</td>'
        table = table.replace(
            first_detail_row,
            first_detail_row[:detail_cell.start()] + replacement + first_detail_row[detail_cell.end():],
            1,
        )
        for prior_index in detail_indices[1:]:
            table = table.replace(rows[prior_index].group(0), "", 1)
        figure_row = rows[figure_index].group(0)
        table = table.replace(figure_row, "", 1)
        return table

    return re.sub(r"<table\b[^>]*>.*?</table>", replace_table, html, flags=re.IGNORECASE | re.DOTALL)


def stable_heading_id(level: int, text: str, counters: dict[int, int], used_ids: set[str]) -> str:
    if level == 1:
        base = "document-title"
    else:
        number_match = re.match(r"^(\d+(?:\.\d+)*)\s*[.、]?\s*", text)
        if number_match:
            base = "sec-" + number_match.group(1).replace(".", "-")
        else:
            counters[level] = counters.get(level, 0) + 1
            for deeper_level in range(level + 1, 7):
                counters.pop(deeper_level, None)
            path = [str(counters.get(current_level, 1)) for current_level in range(2, level + 1)]
            base = "sec-" + "-".join(path)
    candidate = base
    suffix = 2
    while candidate in used_ids:
        candidate = f"{base}-{suffix}"
        suffix += 1
    used_ids.add(candidate)
    return candidate


def normalize_heading_anchors(html: str) -> str:
    heading_re = re.compile(
        r"<h(?P<level>[1-6])(?P<before>[^>]*)\bid=\"(?P<old_id>[^\"]+)\"(?P<after>[^>]*)>"
        r"(?P<body>.*?)</h(?P=level)>",
        re.IGNORECASE | re.DOTALL,
    )
    id_map: dict[str, str] = {}
    counters: dict[int, int] = {}
    used_ids: set[str] = set()

    def replace_heading(match: re.Match[str]) -> str:
        level = int(match.group("level"))
        old_id = html_lib.unescape(match.group("old_id"))
        text = visible_text_from_html(match.group("body"))
        new_id = stable_heading_id(level, text, counters, used_ids)
        id_map[old_id] = new_id
        return (
            f'<h{level}{match.group("before")}id="{new_id}"{match.group("after")}>'
            f'{match.group("body")}</h{level}>'
        )

    html = heading_re.sub(replace_heading, html)
    if not id_map:
        return html

    def replace_href(match: re.Match[str]) -> str:
        quote = match.group("quote")
        target = match.group("target")
        decoded = html_lib.unescape(unquote(target))
        new_target = id_map.get(decoded)
        if not new_target:
            return match.group(0)
        return f'href={quote}#{new_target}{quote}'

    def replace_toc_id(match: re.Match[str]) -> str:
        quote = match.group("quote")
        target = match.group("target")
        decoded = html_lib.unescape(unquote(target))
        new_target = id_map.get(decoded)
        if not new_target:
            return match.group(0)
        return f'id={quote}toc-{new_target}{quote}'

    html = re.sub(
        r"href=(?P<quote>[\"'])#(?P<target>[^\"']+)(?P=quote)",
        replace_href,
        html,
    )
    html = re.sub(
        r"id=(?P<quote>[\"'])toc-(?P<target>[^\"']+)(?P=quote)",
        replace_toc_id,
        html,
    )
    return html


def copy_mermaid_runtime(run_folder: Path) -> None:
    if not VENDORED_MERMAID_RUNTIME.is_file():
        fail(f"Missing vendored Mermaid runtime: {VENDORED_MERMAID_RUNTIME}")
    assets_dir = ensure_assets_dir(run_folder)
    shutil.copy2(VENDORED_MERMAID_RUNTIME, assets_dir / "mermaid.min.js")


def inject_defaults(html: str, markdown: str, run_folder: Path) -> str:
    if markdown_needs_assets_folder(markdown):
        ensure_assets_dir(run_folder)
    html = normalize_html_shell(html, infer_document_language(markdown))
    html = convert_mermaid_blocks(html)
    html = group_adjacent_flowcharts(html)
    html = convert_video_links(html, run_folder)
    html = normalize_heading_anchors(html)
    html = remove_h1_from_toc(html)
    html = merge_requirement_image_table_cells(html)
    html = merge_legacy_requirement_detail_media(html)
    html = group_requirement_figure_pairs(html, run_folder)
    html = replace_document_styles(html)
    if html_contains_images(html) and 'id="image-lightbox"' not in html:
        initial_src = html_lib.escape(first_image_src(html), quote=True)
        close_label = html_lib.escape(infer_close_label(markdown), quote=False)
        lightbox_html = (
            LIGHTBOX_HTML_TEMPLATE
            .replace("__CLOSE_LABEL__", close_label)
            .replace("__DIALOG_LABEL__", "图片预览" if close_label == "关闭" else "Image preview")
            .replace("__OPEN_IMAGE_LABEL__", "打开图片预览" if close_label == "关闭" else "Open image preview")
            .replace("__INITIAL_SRC__", initial_src)
        )
        html = html.replace("</body>", lightbox_html + "\n</body>", 1)
    if "id=\"TOC\"" in html and "IntersectionObserver" not in html:
        html = html.replace("</body>", TOC_TRACKING_SCRIPT + "\n</body>", 1)
    if "```mermaid" in markdown:
        copy_mermaid_runtime(run_folder)
        if "mermaid.initialize" not in html:
            html = html.replace("</body>", MERMAID_INIT_SCRIPT + "\n</body>", 1)
    return html


def render_inline_markdown(text: str) -> str:
    """Render the constrained Markdown used by PM Copilot PRDs without Pandoc."""
    escaped = html_lib.escape(text, quote=False)
    escaped = re.sub(r"&lt;br\s*/?&gt;", "<br>", escaped, flags=re.IGNORECASE)
    escaped = escaped.replace("&lt;small&gt;", "<small>").replace("&lt;/small&gt;", "</small>")
    escaped = re.sub(
        r"!\[([^]]*)\]\(([^)\s]+)(?:\s+[^)]*)?\)",
        lambda match: f'<img src="{html_lib.escape(match.group(2), quote=True)}" alt="{html_lib.escape(match.group(1), quote=True)}" />',
        escaped,
    )
    escaped = re.sub(
        r"\[([^]]+)\]\(([^)\s]+)(?:\s+[^)]*)?\)",
        lambda match: f'<a href="{html_lib.escape(match.group(2), quote=True)}">{match.group(1)}</a>',
        escaped,
    )
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def is_table_separator(line: str) -> bool:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def table_row(line: str, cell_tag: str) -> str:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return "<tr>" + "".join(f"<{cell_tag}>{render_inline_markdown(cell)}</{cell_tag}>" for cell in cells) + "</tr>"


def render_markdown_locally(markdown: str, title: str) -> str:
    """Small dependency-free renderer for PM Copilot's document-shaped Markdown."""
    lines = markdown.splitlines()
    blocks: list[str] = []
    toc: list[tuple[int, str, str]] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    list_tag = "ul"
    index = 0

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            blocks.append(f"<p>{render_inline_markdown('<br>'.join(paragraph))}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            blocks.append(f"<{list_tag}>" + "".join(list_items) + f"</{list_tag}>")
            list_items = []

    while index < len(lines):
        line = lines[index]
        fence = re.match(r"^```([^`]*)$", line.strip())
        if fence:
            flush_paragraph()
            flush_list()
            language = fence.group(1).strip().lower()
            index += 1
            code_lines: list[str] = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            class_name = ' class="mermaid"' if language == "mermaid" else ""
            blocks.append(f"<pre{class_name}><code>{html_lib.escape(chr(10).join(code_lines))}</code></pre>")
            index += 1
            continue

        heading = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if heading:
            flush_paragraph()
            flush_list()
            level = len(heading.group(1))
            text = heading.group(2)
            anchor = f"heading-{len(toc) + 1}"
            blocks.append(f"<h{level} id=\"{anchor}\">{render_inline_markdown(text)}</h{level}>")
            if 2 <= level <= 4:
                toc.append((level, anchor, re.sub(r"<[^>]+>", "", render_inline_markdown(text))))
            index += 1
            continue

        if line.strip().startswith("|") and index + 1 < len(lines) and is_table_separator(lines[index + 1]):
            flush_paragraph()
            flush_list()
            rows = ["<thead>", table_row(line, "th"), "</thead><tbody>"]
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(table_row(lines[index], "td"))
                index += 1
            blocks.append("<table>" + "".join(rows) + "</tbody></table>")
            continue

        item = re.match(r"^\s*([-*+]|\d+[.)])\s+(.+)$", line)
        if item:
            flush_paragraph()
            next_tag = "ol" if re.match(r"\d", item.group(1)) else "ul"
            if list_items and next_tag != list_tag:
                flush_list()
            list_tag = next_tag
            list_items.append(f"<li>{render_inline_markdown(item.group(2))}</li>")
            index += 1
            continue

        if not line.strip():
            flush_paragraph()
            flush_list()
            index += 1
            continue
        paragraph.append(line.strip())
        index += 1

    flush_paragraph()
    flush_list()
    toc_html = "".join(
        f'<li class="toc-level-{level}"><a href="#{anchor}">{label}</a></li>'
        for level, anchor, label in toc
    )
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<title>{html_lib.escape(title)}</title></head><body>"
        f"<nav id=\"TOC\"><ul>{toc_html}</ul></nav><main>{''.join(blocks)}</main></body></html>"
    )


def resolve_pandoc() -> str | None:
    local_pandoc = Path.home() / ".local" / "bin" / "pandoc"
    pandoc = shutil.which("pandoc") or (str(local_pandoc) if local_pandoc.is_file() else None)
    if pandoc:
        return pandoc
    setup_script = ROOT / "scripts" / "setup_prd_renderer.py"
    if not setup_script.is_file():
        return None
    result = subprocess.run(
        [sys.executable, str(setup_script), "--install"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.stdout.strip():
        print(result.stdout.strip(), file=sys.stderr)
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    if result.returncode != 0:
        return None
    return shutil.which("pandoc") or (str(local_pandoc) if local_pandoc.is_file() else None)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_folder", type=Path, help="Output run folder containing prd.md")
    parser.add_argument("--title", default="", help="Optional browser title. Defaults to the first Markdown H1.")
    args = parser.parse_args()

    run_folder = args.run_folder.resolve()
    prd_path = run_folder / "prd.md"
    html_path = run_folder / "prd.html"
    if not prd_path.is_file():
        fail(f"Missing prd.md: {prd_path}")
    markdown = prd_path.read_text(encoding="utf-8")
    title = args.title.strip() or first_markdown_h1(markdown)
    pandoc = resolve_pandoc()
    if pandoc:
        command = [
            pandoc,
            str(prd_path),
            "--standalone",
            "--to",
            "html5",
            "--toc",
            "--toc-depth=4",
            "--metadata",
            f"pagetitle={title}",
            "-o",
            str(html_path),
        ]
        result = subprocess.run(command, cwd=run_folder, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            sys.stderr.write(result.stderr)
            fail("pandoc failed")
        html = html_path.read_text(encoding="utf-8")
    else:
        html = render_markdown_locally(markdown, title)
    html_path.write_text(inject_defaults(html, markdown, run_folder), encoding="utf-8")
    print(html_path)


if __name__ == "__main__":
    main()
