#!/usr/bin/env python3
"""Render `prd.md` into a browser-readable `prd.html` with PM Copilot defaults."""

from __future__ import annotations

import argparse
import html as html_lib
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENDORED_MERMAID_RUNTIME = ROOT / "vendor" / "mermaid" / "mermaid.min.js"

DOCUMENT_CSS = """
    :root {
      color-scheme: light;
    }
    html {
      background: #fff;
    }
    body {
      box-sizing: border-box;
      width: auto;
      max-width: none;
      min-height: 100vh;
      margin: 0;
      padding: 40px 56px 80px 308px;
      background: #fff;
      color: #1f2937;
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
      border-top: 1px solid #e5e7eb;
      font-size: 24px;
    }
    h3 {
      margin-top: 28px;
      font-size: 18px;
    }
    a {
      color: #2563eb;
    }
    code {
      padding: 1px 4px;
      border-radius: 4px;
      background: #f3f4f6;
      color: #111827;
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
      border-right: 1px solid #e5e7eb;
      background: #f9fafb;
      font-size: 13px;
      line-height: 1.45;
    }
    #TOC > ul {
      margin: 0;
    }
    #TOC li {
      margin: 6px 0;
    }
    #TOC a {
      color: #374151;
      text-decoration: none;
    }
    #TOC a:hover {
      color: #111827;
    }
    #TOC a.is-active {
      color: #111827;
      font-weight: 700;
    }
    table {
      display: table;
      width: 100%;
      table-layout: auto;
      border-collapse: collapse;
      border: 1px solid #e5e7eb;
      font-size: 13px;
    }
    table:has(th:nth-child(2):last-child) th:first-child,
    table:has(th:nth-child(2):last-child) td:first-child {
      width: 112px;
      min-width: 96px;
      max-width: 160px;
      white-space: nowrap;
    }
    table:has(th:nth-child(2):last-child) th:nth-child(2),
    table:has(th:nth-child(2):last-child) td:nth-child(2) {
      width: auto;
    }
    thead {
      background: #f3f4f6;
    }
    tbody {
      border: 0;
    }
    th,
    td {
      border: 1px solid #e5e7eb;
      padding: 8px 10px;
      vertical-align: top;
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
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      background: #fff;
      cursor: zoom-in;
      object-fit: contain;
    }
    td img {
      margin: 4px 0;
    }
    figcaption {
      margin-top: 8px;
      color: #6b7280;
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
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      background: #f9fafb;
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
        border-bottom: 1px solid #e5e7eb;
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
  const sections = Array.from(document.querySelectorAll('h2[id], h3[id]'));
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
    if re.search(r"^>\s*占位图[:：]\s*.+?\.(?:png|jpg|jpeg|webp)\s*$", markdown, re.MULTILINE):
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
    nav_match = re.search(r"<nav id=\"TOC\".*?</nav>", html, re.IGNORECASE | re.DOTALL)
    if not nav_match:
        return html
    toc = nav_match.group(0)
    compact_match = re.fullmatch(
        r"(?P<prefix><nav id=\"TOC\"[^>]*>\s*<ul>\s*)"
        r"<li><a href=\"#[^\"]+\"[^>]*>.*?</a>\s*<ul>\s*"
        r"(?P<items>.*)"
        r"\s*</ul>\s*</li>\s*"
        r"(?P<suffix></ul>\s*</nav>)",
        toc,
        re.IGNORECASE | re.DOTALL,
    )
    if not compact_match:
        return html
    cleaned_toc = compact_match.group("prefix") + compact_match.group("items") + compact_match.group("suffix")
    return html[:nav_match.start()] + cleaned_toc + html[nav_match.end():]


def normalize_html_shell(html: str) -> str:
    html = html.replace('<html xmlns="http://www.w3.org/1999/xhtml">', "<html>", 1)
    html = re.sub(
        r"\s*\*\* See https://pandoc\.org/MANUAL\.html#variables-for-html for config info\.\n",
        "\n",
        html,
        count=1,
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
    if "</style>" in html:
        html = html.replace("</style>", DOCUMENT_CSS + "\n  </style>", 1)
    else:
        html = html.replace("</head>", f"<style>\n{DOCUMENT_CSS}\n</style>\n</head>", 1)
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
        "--toc",
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
