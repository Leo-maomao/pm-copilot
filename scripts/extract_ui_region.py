#!/usr/bin/env python3
"""Extract a rendered UI region into a standalone PM Copilot HTML handoff."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import validate_prototype_visual as visual  # noqa: E402


STYLE_PROPERTIES = (
    "align-items",
    "background",
    "background-color",
    "border",
    "border-radius",
    "box-shadow",
    "box-sizing",
    "color",
    "display",
    "flex",
    "flex-direction",
    "flex-wrap",
    "font-family",
    "font-size",
    "font-weight",
    "gap",
    "grid-template-columns",
    "height",
    "justify-content",
    "letter-spacing",
    "line-height",
    "margin",
    "max-height",
    "max-width",
    "min-height",
    "min-width",
    "opacity",
    "overflow",
    "padding",
    "position",
    "text-align",
    "text-decoration",
    "text-overflow",
    "transform",
    "vertical-align",
    "white-space",
    "width",
)


ANNOTATION_CSS = """
:root {
  --annotation-red: #ff3b30;
  --annotation-size: 22px;
}
.pm-source-extract-shell {
  min-height: 100vh;
  margin: 0;
  overflow-x: hidden;
  background: #f5f6f8;
  color: #1f2937;
}
.pm-source-extract-region {
  position: relative;
  width: 100%;
  max-width: 100vw;
  overflow-x: auto;
}
.pm-source-extract-region [data-source-extract="true"] {
  max-width: calc(100vw - 32px) !important;
}
.pm-source-extract-region [data-source-extract="true"] * {
  max-width: 100% !important;
}
.annotation-marker,
.annotation-number {
  width: var(--annotation-size);
  height: var(--annotation-size);
  border-radius: 999px;
  border: 0;
  background: var(--annotation-red);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  line-height: var(--annotation-size);
  text-align: center;
  box-sizing: border-box;
}
.annotation-marker {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 40;
  cursor: pointer;
}
.annotation-dialog {
  position: absolute;
  top: 38px;
  right: 10px;
  z-index: 50;
  display: none;
  width: min(320px, calc(100vw - 32px));
  padding: 12px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 12px 36px rgba(15, 23, 42, 0.18);
  font: 14px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.annotation-dialog.is-open {
  display: block;
}
.annotation-dialog-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-weight: 700;
}
.annotation-toggle {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 80;
  padding: 8px 12px;
  border: 0;
  border-radius: 999px;
  background: #111827;
  color: #fff;
  font: 13px/20px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  cursor: grab;
}
.annotation-toggle.is-hidden {
  display: none;
}
.annotation-list {
  position: fixed;
  top: 0;
  right: 0;
  z-index: 90;
  display: none;
  width: min(360px, 100vw);
  height: 100vh;
  padding: 18px;
  overflow: auto;
  background: #fff;
  box-shadow: -18px 0 44px rgba(15, 23, 42, 0.18);
  font: 14px/1.5 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.annotation-list.is-open {
  display: block;
}
.annotation-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.annotation-close {
  border: 0;
  background: transparent;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
}
.annotation-item {
  display: grid;
  grid-template-columns: var(--annotation-size) 1fr;
  gap: 10px;
  margin: 0 0 14px;
}
@media (max-width: 600px) {
  .pm-source-extract-region [data-source-extract="true"] {
    width: auto !important;
    margin-left: 16px !important;
    margin-right: 16px !important;
    box-sizing: border-box !important;
  }
}
"""


ANNOTATION_JS = """
(() => {
  const marker = document.querySelector('.annotation-marker');
  const dialog = document.querySelector('.annotation-dialog');
  const toggle = document.querySelector('.annotation-toggle');
  const panel = document.querySelector('.annotation-list');
  const close = document.querySelector('.annotation-close');
  if (marker && dialog) {
    marker.addEventListener('click', () => {
      dialog.classList.toggle('is-open');
    });
  }
  if (toggle && panel) {
    toggle.addEventListener('click', () => {
      toggle.classList.add('is-hidden');
      panel.classList.add('is-open');
    });
  }
  if (close && panel && toggle) {
    close.addEventListener('click', () => {
      panel.classList.remove('is-open');
      toggle.classList.remove('is-hidden');
    });
  }
})();
"""


def safe_json_for_script(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2).replace("</", "<\\/")


def fail(message: str, code: int = 1) -> None:
    print(f"FAIL: {message}")
    sys.exit(code)


def target_to_url(target: str) -> str:
    if target.startswith(("http://", "https://", "file://")):
        return target
    path = Path(target).expanduser().resolve()
    if not path.exists():
        fail(f"Target is neither a URL nor an existing file: {target}")
    return path.as_uri()


def output_name_for_platform(platform: str) -> str:
    names = {
        "web": "prototype-web.html",
        "h5": "prototype-h5.html",
        "app": "prototype-app.html",
        "mini-program": "prototype-mini-program.html",
    }
    if platform not in names:
        fail("--platform must be one of web, h5, app, mini-program")
    return names[platform]


def read_mock_data(path: Path | None) -> Any:
    if not path:
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"Mock data JSON is invalid: {path}: {error}")
    except OSError as error:
        fail(f"Cannot read mock data file: {path}: {error}")
    return {}


def read_optional_text(path: Path | None, label: str) -> str:
    if not path:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        fail(f"Cannot read {label}: {path}: {error}")
    return ""


def extract_region(
    page,
    selector: str,
    style_properties: tuple[str, ...],
) -> dict[str, Any]:
    return page.evaluate(
        """({ selector, styleProperties }) => {
            const root = document.querySelector(selector);
            if (!root) {
                throw new Error(`Selector not found: ${selector}`);
            }
            const makeScopedClass = (index) => `pm-extract-${index}`;
            const clone = root.cloneNode(true);
            const originalNodes = [root, ...root.querySelectorAll('*')];
            const cloneNodes = [clone, ...clone.querySelectorAll('*')];
            const styles = [];
            const placeholderAsset = (node, source) => {
                const rect = node.getBoundingClientRect();
                const width = Math.max(1, Math.round(rect.width || node.naturalWidth || 160));
                const height = Math.max(1, Math.round(rect.height || node.naturalHeight || 90));
                const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><rect width="100%" height="100%" fill="#eef2f7"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#64748b" font-family="Arial, sans-serif" font-size="12">asset</text></svg>`;
                return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
            };
            originalNodes.forEach((node, index) => {
                const className = makeScopedClass(index);
                cloneNodes[index].classList.add(className);
                const computed = window.getComputedStyle(node);
                const declarations = [];
                styleProperties.forEach((property) => {
                    const value = computed.getPropertyValue(property);
                    if (value) {
                        declarations.push(`${property}: ${value};`);
                    }
                });
                styles.push(`.${className}{${declarations.join('')}}`);
                const cloneNode = cloneNodes[index];
                const currentSource = node.currentSrc || node.src || node.getAttribute?.('src') || '';
                if (/^https?:\\/\\//i.test(currentSource)) {
                    cloneNode.setAttribute('data-external-asset-source', currentSource);
                    cloneNode.removeAttribute('srcset');
                    if (cloneNode.tagName && cloneNode.tagName.toLowerCase() === 'img') {
                        cloneNode.setAttribute('src', placeholderAsset(node, currentSource));
                    } else {
                        cloneNode.removeAttribute('src');
                    }
                }
                const href = node.href?.baseVal || node.getAttribute?.('href') || '';
                if (/^https?:\\/\\//i.test(href) && cloneNode.tagName && cloneNode.tagName.toLowerCase() !== 'a') {
                    cloneNode.setAttribute('data-external-asset-source', href);
                    cloneNode.removeAttribute('href');
                }
            });
            const rect = root.getBoundingClientRect();
            const assetUrls = Array.from(root.querySelectorAll('img, source, video, use'))
                .map((node) => node.currentSrc || node.src || node.href?.baseVal || node.getAttribute('href') || '')
                .filter(Boolean);
            return {
                html: clone.outerHTML,
                textLength: (root.innerText || '').trim().length,
                rect: {
                    x: Math.round(rect.x),
                    y: Math.round(rect.y),
                    width: Math.round(rect.width),
                    height: Math.round(rect.height),
                },
                styles: styles.join('\\n'),
                assetUrls: Array.from(new Set(assetUrls)),
                title: document.title || '',
            };
        }""",
        {"selector": selector, "styleProperties": list(style_properties)},
    )


def run_interaction_actions(page, actions: list[str]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for raw_action in actions:
        action = raw_action.strip()
        if not action:
            continue
        if "=" not in action:
            results.append({"action": action, "status": "failed", "error": "expected action=selector or wait=ms"})
            continue
        kind, payload = action.split("=", 1)
        kind = kind.strip().lower()
        payload = payload.strip()
        try:
            if kind == "wait":
                page.wait_for_timeout(int(payload))
            elif kind == "click":
                page.locator(payload).first.click()
            elif kind == "hover":
                page.locator(payload).first.hover()
            elif kind in {"fill", "press", "select"}:
                if "::" not in payload:
                    raise ValueError(f"{kind} action requires selector::value")
                selector, value = payload.split("::", 1)
                locator = page.locator(selector.strip()).first
                if kind == "fill":
                    locator.fill(value)
                elif kind == "press":
                    locator.press(value)
                else:
                    locator.select_option(value)
            else:
                raise ValueError(f"unsupported action type: {kind}")
            results.append({"action": action, "status": "passed"})
        except Exception as error:  # noqa: BLE001 - report browser action failures verbatim.
            results.append({"action": action, "status": "failed", "error": str(error)})
    return results


def capture_region_screenshot(page, selector: str, screenshot_path: Path) -> str:
    element = page.locator(selector).first
    if element.count() == 0:
        raise RuntimeError(f"Selector not found: {selector}")
    element.screenshot(path=str(screenshot_path))
    return screenshot_path.as_posix()


def compare_regions(
    browser,
    *,
    source_url: str,
    source_selector: str,
    extracted_url: str,
    extracted_selector: str,
    actions: list[str],
    viewport_name: str,
    width: int,
    height: int,
    wait_until: str,
    wait_ms: int,
    nav_timeout_ms: int,
    visual_dir: Path,
    run_folder: Path,
    max_diff_ratio: float,
    label: str,
) -> dict[str, Any]:
    source_page = browser.new_page(viewport={"width": width, "height": height})
    extracted_page = browser.new_page(viewport={"width": width, "height": height})
    try:
        source_page.goto(source_url, wait_until=wait_until, timeout=nav_timeout_ms)
        extracted_page.goto(extracted_url, wait_until="load", timeout=nav_timeout_ms)
        source_page.wait_for_timeout(wait_ms)
        extracted_page.wait_for_timeout(wait_ms)
        source_actions = run_interaction_actions(source_page, actions)
        extracted_actions = run_interaction_actions(extracted_page, actions)
        source_failed = [item for item in source_actions if item.get("status") == "failed"]
        extracted_failed = [item for item in extracted_actions if item.get("status") == "failed"]
        source_screenshot = visual_dir / f"{viewport_name}-{label}-source-region.png"
        extracted_screenshot = visual_dir / f"{viewport_name}-{label}-extracted-region.png"
        if source_failed or extracted_failed:
            return {
                "status": "failed",
                "label": label,
                "actions": actions,
                "source_actions": source_actions,
                "extracted_actions": extracted_actions,
                "source_region_screenshot": "",
                "extracted_region_screenshot": "",
                "region_diff": {"status": "not_available"},
                "failures": [
                    *[f"source action failed: {item.get('action')} {item.get('error', '')}" for item in source_failed],
                    *[
                        f"extracted action failed: {item.get('action')} {item.get('error', '')}"
                        for item in extracted_failed
                    ],
                ],
            }
        capture_region_screenshot(source_page, source_selector, source_screenshot)
        capture_region_screenshot(extracted_page, extracted_selector, extracted_screenshot)
        region_diff = visual.diff_png(extracted_screenshot, source_screenshot)
        failures: list[str] = []
        if region_diff.get("status") == "failed":
            failures.append(str(region_diff.get("reason") or "region screenshot comparison failed"))
        elif float(region_diff.get("diff_ratio") or 0) > max_diff_ratio:
            failures.append(f"region diff ratio {region_diff.get('diff_ratio')} exceeds {max_diff_ratio}")
        return {
            "status": "failed" if failures else "passed",
            "label": label,
            "actions": actions,
            "source_actions": source_actions,
            "extracted_actions": extracted_actions,
            "source_region_screenshot": visual.path_for_report(source_screenshot, run_folder),
            "extracted_region_screenshot": visual.path_for_report(extracted_screenshot, run_folder),
            "region_diff": region_diff,
            "failures": failures,
        }
    finally:
        source_page.close()
        extracted_page.close()


def build_html(
    extracted: dict[str, Any],
    target_url: str,
    selector: str,
    source_screenshot: str,
    note: str,
    generated_at: str,
    mock_data: Any,
    mock_runtime_js: str,
    dependency_notes: list[str],
) -> str:
    escaped_note = html.escape(note)
    escaped_target = html.escape(target_url)
    escaped_selector = html.escape(selector)
    escaped_screenshot = html.escape(source_screenshot)
    title = html.escape(str(extracted.get("title") or "Source Extracted UI"))
    region_html = str(extracted["html"]).replace(
        ">",
        ' data-source-extract="true" data-source-target="'
        + escaped_target
        + '" data-source-selector="'
        + escaped_selector
        + '">',
        1,
    )
    metadata = {
        "artifact_mode": "source_extract_html",
        "source_target": target_url,
        "selector": selector,
        "source_region_screenshot": source_screenshot,
        "generated_at": generated_at,
        "dependency_simulation": {
            "mock_data_embedded": bool(mock_data),
            "mock_runtime_embedded": bool(mock_runtime_js.strip()),
            "dependency_notes": dependency_notes,
        },
        "limitations": [
            "Extracted computed styles cover common CSS properties, not every pseudo-state or host runtime behavior.",
            "Portal, canvas, video, shadow DOM, remote font, and cross-origin asset behavior may require manual follow-up.",
        ],
    }
    mock_runtime_block = (
        f"\n  <script id=\"pm-mock-runtime\">\n{mock_runtime_js}\n  </script>"
        if mock_runtime_js.strip()
        else ""
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="pm-copilot-artifact" content="source_extract_html">
  <meta name="delivery-boundary" content="source_extract_html_review_artifact">
  <title>{title}</title>
  <!-- source-extract-summary: target={escaped_target}; selector={escaped_selector}; screenshot={escaped_screenshot} -->
  <style>
    {extracted["styles"]}
    {ANNOTATION_CSS}
  </style>
</head>
<body class="pm-source-extract-shell">
  <main class="pm-source-extract-region" data-style-source="source_extract_html" data-delivery-boundary="source_extract_html_review_artifact">
    {region_html}
    <button class="annotation-marker" data-annotation-id="1" data-annotation-placement="top-right" aria-label="注释 1">1</button>
    <section class="annotation-dialog" data-annotation-id="1" aria-label="注释 1">
      <div class="annotation-dialog-header"><span class="annotation-number">1</span><span>提取说明</span></div>
      <div>{escaped_note}</div>
    </section>
  </main>
  <button class="annotation-toggle" data-draggable="true" type="button">注释</button>
  <aside class="annotation-list" aria-label="注释列表">
    <div class="annotation-list-header">
      <strong>注释</strong>
      <button class="annotation-close" type="button" aria-label="关闭">×</button>
    </div>
    <div class="annotation-item" data-annotation-id="1">
      <span class="annotation-number">1</span>
      <div>
        <strong>来源区域</strong>
        <p>{escaped_note}</p>
      </div>
    </div>
  </aside>
  <script type="application/json" id="source-extract-metadata">
{safe_json_for_script(metadata)}
  </script>
  <script type="application/json" id="pm-mock-data">
{safe_json_for_script(mock_data)}
  </script>
  <script>
    window.__PM_SOURCE_EXTRACT__ = JSON.parse(document.getElementById('source-extract-metadata').textContent || '{{}}');
    window.__PM_MOCK_DATA__ = JSON.parse(document.getElementById('pm-mock-data').textContent || '{{}}');
  </script>
  <script>{ANNOTATION_JS}</script>
  {mock_runtime_block}
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, help="Source preview URL, file:// URL, or local HTML file path.")
    parser.add_argument("--selector", required=True, help="CSS selector for the source UI region to extract.")
    parser.add_argument("--output", type=Path, default=None, help="Output HTML path.")
    parser.add_argument("--run-folder", type=Path, default=None, help="PM Copilot output folder.")
    parser.add_argument("--platform", choices=["web", "h5", "app", "mini-program"], default="web")
    parser.add_argument("--viewport", default="desktop=1440x1000", help="Viewport in name=WIDTHxHEIGHT format.")
    parser.add_argument("--wait-ms", type=int, default=500)
    parser.add_argument(
        "--wait-until",
        choices=["commit", "domcontentloaded", "load", "networkidle"],
        default="domcontentloaded",
    )
    parser.add_argument("--nav-timeout-ms", type=int, default=15000)
    parser.add_argument("--browser-channel", default=None)
    parser.add_argument("--no-auto-setup", action="store_true")
    parser.add_argument(
        "--max-diff-ratio",
        type=float,
        default=0.03,
        help="Maximum pixel diff ratio allowed between the source region screenshot and extracted HTML region screenshot.",
    )
    parser.add_argument(
        "--skip-region-diff",
        action="store_true",
        help="Write the extracted HTML without comparing the extracted region screenshot to the source region screenshot.",
    )
    parser.add_argument(
        "--interaction",
        action="append",
        default=[],
        help=(
            "Interaction action to replay against source and extracted HTML before diffing. "
            "Supported: click=<selector>, hover=<selector>, fill=<selector>::<value>, "
            "press=<selector>::<key>, select=<selector>::<value>, wait=<ms>. Can be repeated."
        ),
    )
    parser.add_argument(
        "--interaction-max-diff-ratio",
        type=float,
        default=None,
        help="Maximum diff ratio for interaction replay screenshots. Defaults to --max-diff-ratio.",
    )
    parser.add_argument(
        "--compare-only",
        action="store_true",
        help="Do not rewrite --output; only compare the source preview with an existing extracted HTML file.",
    )
    parser.add_argument(
        "--annotation-note",
        default="该 HTML 从源项目预览中的指定区域提取，标注层用于说明产品逻辑、交互、数据和研发注意事项。",
    )
    parser.add_argument(
        "--mock-data",
        type=Path,
        default=None,
        help="JSON file to embed as window.__PM_MOCK_DATA__ for dependency-free product-state simulation.",
    )
    parser.add_argument(
        "--mock-runtime-js",
        type=Path,
        default=None,
        help="JavaScript file to embed after extraction for mock interactions, API/store simulation, and closed-loop states.",
    )
    parser.add_argument(
        "--dependency-note",
        action="append",
        default=[],
        help="Dependency simulated by mock data/runtime, such as API, permission, store, async job, or upload service. Can be repeated.",
    )
    args = parser.parse_args()

    run_folder = args.run_folder.resolve() if args.run_folder else Path.cwd()
    output = args.output.resolve() if args.output else run_folder / output_name_for_platform(args.platform)
    visual_dir = run_folder / "visual-review" / "source-extract"
    visual_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_folder / "visual-review" / "source-extract-report.json"
    viewport_name, width, height = visual.parse_viewport(args.viewport)
    target_url = target_to_url(args.target)
    browser_channel = args.browser_channel or os.environ.get("PLAYWRIGHT_BROWSER_CHANNEL")
    sync_playwright = visual.load_playwright(not args.no_auto_setup)
    mock_data = read_mock_data(args.mock_data)
    mock_runtime_js = read_optional_text(args.mock_runtime_js, "mock runtime JS")

    generated_at = dt.datetime.now(dt.timezone.utc).isoformat()
    source_screenshot = visual_dir / f"{viewport_name}-region.png"
    extracted: dict[str, Any] = {
        "textLength": 0,
        "rect": {},
        "assetUrls": [],
    }
    if args.compare_only:
        if not output.is_file():
            fail(f"--compare-only requires an existing output file: {output}")
        with sync_playwright() as playwright:
            browser = visual.launch_browser(playwright, browser_channel, not args.no_auto_setup)
            page = browser.new_page(viewport={"width": width, "height": height})
            try:
                page.goto(target_url, wait_until=args.wait_until, timeout=args.nav_timeout_ms)
                page.wait_for_timeout(args.wait_ms)
                capture_region_screenshot(page, args.selector, source_screenshot)
            finally:
                page.close()
                browser.close()
    else:
        with sync_playwright() as playwright:
            browser = visual.launch_browser(playwright, browser_channel, not args.no_auto_setup)
            page = browser.new_page(viewport={"width": width, "height": height})
            try:
                page.goto(target_url, wait_until=args.wait_until, timeout=args.nav_timeout_ms)
                page.wait_for_timeout(args.wait_ms)
                element = page.locator(args.selector).first
                if element.count() == 0:
                    fail(f"Selector not found: {args.selector}")
                element.screenshot(path=str(source_screenshot))
                extracted = extract_region(page, args.selector, STYLE_PROPERTIES)
            finally:
                page.close()
                browser.close()

        if int(extracted.get("textLength") or 0) < 1:
            fail("Extracted region has no visible text; use a more specific selector or inspect the source preview")

        output.parent.mkdir(parents=True, exist_ok=True)
        html_text = build_html(
            extracted,
            target_url,
            args.selector,
            visual.path_for_report(source_screenshot, run_folder),
            args.annotation_note,
            generated_at,
            mock_data,
            mock_runtime_js,
            args.dependency_note,
        )
        output.write_text(html_text, encoding="utf-8")

    extracted_screenshot: Path | None = None
    region_diff: dict[str, Any] | None = None
    diff_failures: list[str] = []
    initial_diff_report: dict[str, Any] | None = None
    if not args.skip_region_diff:
        with sync_playwright() as playwright:
            browser = visual.launch_browser(playwright, browser_channel, not args.no_auto_setup)
            page = browser.new_page(viewport={"width": width, "height": height})
            try:
                page.goto(output.as_uri(), wait_until="load", timeout=args.nav_timeout_ms)
                page.wait_for_timeout(args.wait_ms)
                extracted_element = page.locator('[data-source-extract="true"]').first
                if extracted_element.count() == 0:
                    diff_failures.append("extracted HTML missing [data-source-extract='true'] region")
                else:
                    extracted_screenshot = visual_dir / f"{viewport_name}-extracted-region.png"
                    extracted_element.screenshot(path=str(extracted_screenshot))
                    region_diff = visual.diff_png(extracted_screenshot, source_screenshot)
                    initial_diff_report = {
                        "status": "failed" if region_diff.get("status") == "failed" else "passed",
                        "label": "initial",
                        "actions": [],
                        "source_region_screenshot": visual.path_for_report(source_screenshot, run_folder),
                        "extracted_region_screenshot": visual.path_for_report(extracted_screenshot, run_folder),
                        "region_diff": region_diff,
                        "failures": [],
                    }
                    if region_diff.get("status") == "failed":
                        failure = str(region_diff.get("reason") or "region screenshot comparison failed")
                        diff_failures.append(failure)
                        initial_diff_report["status"] = "failed"
                        initial_diff_report["failures"].append(failure)
                    elif float(region_diff.get("diff_ratio") or 0) > args.max_diff_ratio:
                        failure = f"region diff ratio {region_diff.get('diff_ratio')} exceeds {args.max_diff_ratio}"
                        diff_failures.append(failure)
                        initial_diff_report["status"] = "failed"
                        initial_diff_report["failures"].append(failure)
            finally:
                page.close()
                browser.close()

    interaction_checks: list[dict[str, Any]] = []
    if args.interaction:
        interaction_max_diff = args.interaction_max_diff_ratio
        if interaction_max_diff is None:
            interaction_max_diff = args.max_diff_ratio
        with sync_playwright() as playwright:
            browser = visual.launch_browser(playwright, browser_channel, not args.no_auto_setup)
            try:
                interaction_report = compare_regions(
                    browser,
                    source_url=target_url,
                    source_selector=args.selector,
                    extracted_url=output.as_uri(),
                    extracted_selector='[data-source-extract="true"]',
                    actions=args.interaction,
                    viewport_name=viewport_name,
                    width=width,
                    height=height,
                    wait_until=args.wait_until,
                    wait_ms=args.wait_ms,
                    nav_timeout_ms=args.nav_timeout_ms,
                    visual_dir=visual_dir,
                    run_folder=run_folder,
                    max_diff_ratio=interaction_max_diff,
                    label="interaction",
                )
                interaction_checks.append(interaction_report)
                diff_failures.extend(interaction_report.get("failures", []))
            finally:
                browser.close()
    else:
        interaction_checks.append({
            "status": "not_requested",
            "label": "interaction",
            "actions": [],
            "note": "No interaction replay actions were supplied; the extracted HTML is validated as a captured state only.",
        })

    report = {
        "status": "failed" if diff_failures else "passed",
        "artifact_mode": "source_extract_html",
        "source_target": args.target,
        "target_url": target_url,
        "selector": args.selector,
        "viewport": {"name": viewport_name, "width": width, "height": height},
        "output": visual.path_for_report(output, run_folder),
        "source_region_screenshot": visual.path_for_report(source_screenshot, run_folder),
        "extracted_region_screenshot": visual.path_for_report(extracted_screenshot, run_folder)
        if extracted_screenshot
        else "",
        "region_diff": region_diff or {
            "status": "skipped" if args.skip_region_diff else "not_available",
        },
        "region_comparison": initial_diff_report or {
            "status": "skipped" if args.skip_region_diff else "not_available",
        },
        "max_diff_ratio": args.max_diff_ratio,
        "interaction_scope": "interaction_replay" if args.interaction else "static_snapshot_only",
        "interaction_checks": interaction_checks,
        "failures": diff_failures,
        "rect": extracted.get("rect", {}),
        "text_length": extracted.get("textLength"),
        "style_capture_method": "computed_style_subset_inline",
        "asset_handling": {
            "found_asset_urls": extracted.get("assetUrls", []),
            "policy": "source URLs are preserved in extracted markup; embed or localize assets manually if stable offline review is required",
        },
        "dependency_simulation": {
            "mock_data_path": str(args.mock_data) if args.mock_data else "",
            "mock_data_embedded": bool(mock_data),
            "mock_runtime_js_path": str(args.mock_runtime_js) if args.mock_runtime_js else "",
            "mock_runtime_embedded": bool(mock_runtime_js.strip()),
            "dependency_notes": args.dependency_note,
            "policy": (
                "Use mock data and mock runtime for API/store/permission/asynchronous dependencies "
                "so the standalone HTML demonstrates product intent and closed-loop behavior for engineering handoff."
            ),
        },
        "annotation_layer": "single initial marker plus right-side annotation panel; add more markers manually for product logic",
        "limitations": [
            "Computed style extraction captures a common property subset only.",
            "Pseudo-elements, pseudo-states, portal content, canvas/video, shadow DOM, and cross-origin assets may need manual refinement.",
        ],
        "generated_at": generated_at,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PM Copilot source UI region extracted: {output}")
    print(f"Source extract report: {report_path}")
    if diff_failures:
        fail("Source extracted HTML does not match the source region closely enough; see source-extract-report.json")


if __name__ == "__main__":
    main()
