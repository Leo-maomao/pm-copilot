#!/usr/bin/env python3
"""Render `prd.md` into a browser-readable `prd.html` with PM Copilot defaults."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


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
    }
    table {
      display: table;
      width: 100%;
      table-layout: fixed;
      border-collapse: collapse;
      border: 1px solid #e5e7eb;
      font-size: 13px;
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
    figure img {
      display: block;
      max-width: 100%;
      max-height: calc(100vh - 160px);
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      background: #fff;
      cursor: zoom-in;
      object-fit: contain;
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
<img alt="" />
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
    lightboxImage.removeAttribute('src');
    lightboxImage.setAttribute('alt', '');
  };

  Array.from(document.querySelectorAll('figure img')).forEach((image) => {
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


def inject_defaults(html: str, markdown: str) -> str:
    if "</style>" in html:
        html = html.replace("</style>", DOCUMENT_CSS + "\n  </style>", 1)
    else:
        html = html.replace("</head>", f"<style>\n{DOCUMENT_CSS}\n</style>\n</head>", 1)
    if "image-lightbox" not in html:
        lightbox_html = LIGHTBOX_HTML_TEMPLATE.replace("__CLOSE_LABEL__", infer_close_label(markdown))
        html = html.replace("</body>", lightbox_html + "\n</body>", 1)
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
    html_path.write_text(inject_defaults(html, markdown), encoding="utf-8")
    print(html_path)


if __name__ == "__main__":
    main()
