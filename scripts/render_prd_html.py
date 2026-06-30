#!/usr/bin/env python3
"""Render `prd.md` into a browser-readable `prd.html` with PM Copilot defaults."""

from __future__ import annotations

import argparse
import html as html_lib
import re
import shutil
import subprocess
import sys
from urllib.parse import unquote
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENDORED_MERMAID_RUNTIME = ROOT / "vendor" / "mermaid" / "mermaid.min.js"

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
      margin-left: -6px;
      padding: 3px 6px;
      border-radius: 6px;
      color: #374151;
      text-decoration: none;
    }
    #TOC a:hover {
      background: #eef2ff;
      color: #1d4ed8;
    }
    #TOC a.is-active {
      background: var(--pm-doc-accent-soft);
      color: #1d4ed8;
      font-weight: 700;
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
    td img {
      display: block;
      max-width: 100%;
      max-height: calc(100vh - 160px);
      border: 1px solid var(--pm-doc-border);
      border-radius: 8px;
      background: var(--pm-doc-bg);
      cursor: zoom-in;
      object-fit: contain;
    }
    td img {
      margin: 4px 0;
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
<div class="image-lightbox" id="image-lightbox" aria-hidden="true">
<button type="button">__CLOSE_LABEL__</button>
<img src="__INITIAL_SRC__" data-initial-src="__INITIAL_SRC__" alt="" />
</div>
<script>
(() => {
  const lightbox = document.getElementById('image-lightbox');
  if (!lightbox) return;
  const lightboxImage = lightbox.querySelector('img');
  const closeButton = lightbox.querySelector('button');

  const close = () => {
    lightbox.classList.remove('is-open');
    lightbox.setAttribute('aria-hidden', 'true');
    lightboxImage.src = lightboxImage.dataset.initialSrc || '';
    lightboxImage.setAttribute('alt', '');
  };

  Array.from(document.querySelectorAll('figure img, td img')).forEach((image) => {
    image.addEventListener('click', () => {
      lightboxImage.src = image.src;
      lightboxImage.alt = image.alt || '';
      lightbox.classList.add('is-open');
      lightbox.setAttribute('aria-hidden', 'false');
    });
  });

  closeButton.addEventListener('click', close);
  lightbox.addEventListener('click', (event) => {
    if (event.target === lightbox) close();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') close();
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

  const observer = new IntersectionObserver((entries) => {
    const visible = entries
      .filter((entry) => entry.isIntersecting)
      .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
    if (visible[0]?.target?.id) setActive(visible[0].target.id);
  }, { rootMargin: '-20% 0px -70% 0px', threshold: [0, 1] });

  sections.forEach((section) => observer.observe(section));
  const current = sections.find((section) => section.getBoundingClientRect().top >= 0) || sections[0];
  if (current?.id) setActive(current.id);
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


def html_contains_images(html: str) -> bool:
    return bool(re.search(r"<img\b", html, re.IGNORECASE))


def first_image_src(html: str) -> str:
    match = re.search(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", html, re.IGNORECASE)
    return match.group(1) if match else ""


def markdown_needs_assets_folder(markdown: str) -> bool:
    if re.search(r"占位图[:：]\s*.+?\.(?:png|jpg|jpeg|webp)", markdown):
        return True
    refs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", markdown)
    refs.extend(re.findall(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", markdown, re.IGNORECASE))
    for ref in refs:
        normalized = ref.strip().split("#", 1)[0].split("?", 1)[0].replace("\\", "/")
        if normalized.startswith("./assets/") or normalized.startswith("assets/"):
            return True
    return False


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
        r"<li>\s*<a href=\"#[^\"]+\"[^>]*>.*?</a>\s*<ul>\s*"
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


def normalize_html_shell(html: str) -> str:
    html = html.replace('<html xmlns="http://www.w3.org/1999/xhtml">', "<html>", 1)
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
    r"<img\b|占位图|图片占位|截图占位|image placeholder|screenshot placeholder",
    re.IGNORECASE,
)


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
    html = normalize_html_shell(html)
    html = convert_mermaid_blocks(html)
    html = remove_h1_from_toc(html)
    html = normalize_heading_anchors(html)
    html = merge_requirement_image_table_cells(html)
    html = replace_document_styles(html)
    if html_contains_images(html) and 'id="image-lightbox"' not in html:
        initial_src = html_lib.escape(first_image_src(html), quote=True)
        close_label = html_lib.escape(infer_close_label(markdown), quote=False)
        lightbox_html = (
            LIGHTBOX_HTML_TEMPLATE
            .replace("__CLOSE_LABEL__", close_label)
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
    pandoc = shutil.which("pandoc")
    if not pandoc:
        fail("pandoc is required to render prd.html")

    markdown = prd_path.read_text(encoding="utf-8")
    title = args.title.strip() or first_markdown_h1(markdown)

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
    html_path.write_text(inject_defaults(html, markdown, run_folder), encoding="utf-8")
    print(html_path)


if __name__ == "__main__":
    main()
