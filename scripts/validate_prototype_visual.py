#!/usr/bin/env python3
"""Capture and compare generated PM Copilot HTML prototypes.

The script intentionally has no hard dependency at import time. Install
or repair Playwright/browser dependencies with:

    python3 scripts/setup_visual_validation.py

When a system Chrome, Edge, or Chromium is available, the script can use it
instead of requiring Playwright's bundled Chromium download.

It writes screenshots plus a JSON report under
`outputs/<run-id>/visual-review/` by default. If a baseline directory is
provided, screenshots are compared at pixel level using a small stdlib PNG
decoder that supports the PNG format produced by Chromium screenshots.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path
from typing import Iterable


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SUPPORTED_PROTOTYPES = (
    "prototype-web.html",
    "prototype-h5.html",
    "prototype-app.html",
    "prototype-mini-program.html",
)
SYSTEM_BROWSER_CANDIDATES = (
    ("chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    ("msedge", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
    ("chromium", "/Applications/Chromium.app/Contents/MacOS/Chromium"),
    ("chrome", "google-chrome"),
    ("chrome", "google-chrome-stable"),
    ("msedge", "microsoft-edge"),
    ("msedge", "microsoft-edge-stable"),
    ("chromium", "chromium"),
    ("chromium", "chromium-browser"),
)


def fail(message: str, code: int = 1) -> None:
    print(f"FAIL: {message}")
    sys.exit(code)


def installed_browser_channel() -> str | None:
    for channel, candidate in SYSTEM_BROWSER_CANDIDATES:
        if Path(candidate).exists() or shutil.which(candidate):
            return channel
    for env_var in ("PLAYWRIGHT_CHROME_EXECUTABLE_PATH", "CHROME_EXECUTABLE_PATH"):
        value = os.environ.get(env_var)
        if value and Path(value).exists():
            return "chrome"
    return None


def run_setup_visual_validation(install_bundled_browser: bool = False) -> bool:
    setup_script = Path(__file__).with_name("setup_visual_validation.py")
    if not setup_script.is_file():
        return False
    command = [sys.executable, str(setup_script)]
    if install_bundled_browser:
        command.append("--install-bundled-browser")
    result = subprocess.run(command, check=False)
    importlib.invalidate_caches()
    return result.returncode == 0


def load_playwright(auto_setup: bool):
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ModuleNotFoundError:
        if auto_setup and run_setup_visual_validation():
            try:
                from playwright.sync_api import sync_playwright
                return sync_playwright
            except ModuleNotFoundError:
                pass
        fail(
            "Playwright is not installed. Run "
            "`python3 scripts/setup_visual_validation.py` or "
            "`python3 -m pip install --user playwright`.",
            code=2,
        )


def parse_viewport(value: str) -> tuple[str, int, int]:
    try:
        name, size = value.split("=", 1)
        width_s, height_s = size.lower().split("x", 1)
        width = int(width_s)
        height = int(height_s)
    except ValueError:
        fail(f"Invalid viewport '{value}', expected name=WIDTHxHEIGHT")
    if not name or width <= 0 or height <= 0:
        fail(f"Invalid viewport '{value}', width and height must be positive")
    return name, width, height


def find_prototypes(folder: Path, explicit: str | None) -> list[Path]:
    if explicit:
        candidate = folder / explicit
        if not candidate.is_file():
            fail(f"Prototype not found: {candidate}")
        return [candidate]
    prototypes = [
        folder / file_name
        for file_name in SUPPORTED_PROTOTYPES
        if (folder / file_name).is_file()
    ]
    if prototypes:
        return prototypes
    fail(f"No supported prototype found in {folder}")


def png_chunks(data: bytes) -> Iterable[tuple[bytes, bytes]]:
    if not data.startswith(PNG_SIGNATURE):
        fail("Screenshot is not a PNG file")
    offset = len(PNG_SIGNATURE)
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        offset += 4
        chunk_type = data[offset:offset + 4]
        offset += 4
        chunk = data[offset:offset + length]
        offset += length + 4
        yield chunk_type, chunk
        if chunk_type == b"IEND":
            break


def unfilter_scanline(filter_type: int, row: bytearray, prev: bytes, bpp: int) -> bytes:
    result = bytearray(row)
    for index in range(len(result)):
        left = result[index - bpp] if index >= bpp else 0
        up = prev[index] if prev else 0
        up_left = prev[index - bpp] if prev and index >= bpp else 0
        if filter_type == 0:
            value = result[index]
        elif filter_type == 1:
            value = result[index] + left
        elif filter_type == 2:
            value = result[index] + up
        elif filter_type == 3:
            value = result[index] + ((left + up) // 2)
        elif filter_type == 4:
            predictor = paeth(left, up, up_left)
            value = result[index] + predictor
        else:
            fail(f"Unsupported PNG filter type: {filter_type}")
        result[index] = value & 0xFF
    return bytes(result)


def paeth(left: int, up: int, up_left: int) -> int:
    estimate = left + up - up_left
    p_left = abs(estimate - left)
    p_up = abs(estimate - up)
    p_up_left = abs(estimate - up_left)
    if p_left <= p_up and p_left <= p_up_left:
        return left
    if p_up <= p_up_left:
        return up
    return up_left


def decode_png_rgba(path: Path) -> tuple[int, int, list[tuple[int, int, int, int]]]:
    data = path.read_bytes()
    width = height = bit_depth = color_type = interlace = None
    compressed = bytearray()
    for chunk_type, chunk in png_chunks(data):
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _compression, _filter, interlace = struct.unpack(
                ">IIBBBBB",
                chunk,
            )
        elif chunk_type == b"IDAT":
            compressed.extend(chunk)
    if width is None or height is None or bit_depth != 8 or interlace != 0:
        fail(f"Unsupported PNG format in {path}")
    channels_by_type = {0: 1, 2: 3, 4: 2, 6: 4}
    if color_type not in channels_by_type:
        fail(f"Unsupported PNG color type {color_type} in {path}")
    channels = channels_by_type[color_type]
    stride = width * channels
    raw = zlib.decompress(bytes(compressed))
    rows: list[bytes] = []
    offset = 0
    prev = b""
    for _row_index in range(height):
        filter_type = raw[offset]
        offset += 1
        row = bytearray(raw[offset:offset + stride])
        offset += stride
        decoded = unfilter_scanline(filter_type, row, prev, channels)
        rows.append(decoded)
        prev = decoded

    pixels: list[tuple[int, int, int, int]] = []
    for row in rows:
        for index in range(0, len(row), channels):
            if color_type == 0:
                gray = row[index]
                pixels.append((gray, gray, gray, 255))
            elif color_type == 2:
                pixels.append((row[index], row[index + 1], row[index + 2], 255))
            elif color_type == 4:
                gray = row[index]
                pixels.append((gray, gray, gray, row[index + 1]))
            else:
                pixels.append((row[index], row[index + 1], row[index + 2], row[index + 3]))
    return width, height, pixels


def screenshot_stats(path: Path) -> dict[str, float | int]:
    width, height, pixels = decode_png_rgba(path)
    non_blank = 0
    luma_total = 0
    for red, green, blue, alpha in pixels:
        luma_total += int((red * 0.2126) + (green * 0.7152) + (blue * 0.0722))
        if alpha > 0 and not (red >= 248 and green >= 248 and blue >= 248):
            non_blank += 1
    total = max(1, len(pixels))
    return {
        "width": width,
        "height": height,
        "non_blank_ratio": round(non_blank / total, 6),
        "mean_luma": round(luma_total / total, 3),
    }


def diff_png(candidate: Path, baseline: Path) -> dict[str, float | int | str]:
    c_width, c_height, c_pixels = decode_png_rgba(candidate)
    b_width, b_height, b_pixels = decode_png_rgba(baseline)
    if (c_width, c_height) != (b_width, b_height):
        return {
            "status": "failed",
            "reason": "dimension_mismatch",
            "candidate_width": c_width,
            "candidate_height": c_height,
            "baseline_width": b_width,
            "baseline_height": b_height,
            "diff_ratio": 1.0,
        }
    changed = 0
    total_delta = 0
    for candidate_pixel, baseline_pixel in zip(c_pixels, b_pixels):
        delta = sum(abs(candidate_pixel[i] - baseline_pixel[i]) for i in range(4))
        total_delta += delta
        if delta > 24:
            changed += 1
    total = max(1, len(c_pixels))
    return {
        "status": "compared",
        "changed_pixels": changed,
        "total_pixels": total,
        "diff_ratio": round(changed / total, 6),
        "mean_channel_delta": round(total_delta / (total * 4), 4),
    }


def capture_screenshots(
    prototype: Path,
    viewports: list[tuple[str, int, int]],
    output_dir: Path,
    wait_ms: int,
    browser_channel: str | None,
    auto_setup: bool,
) -> list[Path]:
    sync_playwright = load_playwright(auto_setup)

    output_dir.mkdir(parents=True, exist_ok=True)
    screenshots: list[Path] = []
    target = prototype.resolve().as_uri()
    with sync_playwright() as playwright:
        browser = launch_browser(playwright, browser_channel, auto_setup)
        for name, width, height in viewports:
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(target, wait_until="networkidle")
            page.wait_for_timeout(wait_ms)
            screenshot_path = output_dir / f"{name}.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
            screenshots.append(screenshot_path)
            page.close()
        browser.close()
    return screenshots


def launch_browser(playwright, browser_channel: str | None, auto_setup: bool):
    errors: list[str] = []

    def try_launch(channel: str | None, label: str):
        launch_options: dict[str, object] = {}
        if channel:
            launch_options["channel"] = channel
        try:
            return playwright.chromium.launch(**launch_options)
        except Exception as error:
            errors.append(f"{label}: {error}")
            return None

    attempts: list[tuple[str | None, str]] = [(browser_channel, browser_channel or "bundled/default")]
    if browser_channel:
        attempts.append((None, "bundled/default fallback"))

    for channel, label in attempts:
        browser = try_launch(channel, label)
        if browser:
            return browser

    if auto_setup:
        setup_ok = run_setup_visual_validation(install_bundled_browser=bool(browser_channel))
        if setup_ok:
            retry_attempts: list[tuple[str | None, str]] = [(None, "post-setup bundled/default")]
            if browser_channel:
                retry_attempts.append((browser_channel, f"post-setup {browser_channel}"))
            for channel, label in retry_attempts:
                browser = try_launch(channel, label)
                if browser:
                    return browser

    fail(
        "Browser launch failed. Run `python3 scripts/setup_visual_validation.py`, "
        "set `PLAYWRIGHT_BROWSER_CHANNEL=chrome` when using system Chrome, "
        "or record the exact environment limitation. Attempts: "
        + " | ".join(errors[-4:]),
        code=2,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_folder", type=Path)
    parser.add_argument("--prototype", default=None)
    parser.add_argument(
        "--viewport",
        action="append",
        default=None,
        help="Viewport in name=WIDTHxHEIGHT format. Can be repeated.",
    )
    parser.add_argument("--output-dir", default="visual-review")
    parser.add_argument("--baseline-dir", type=Path, default=None)
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--max-diff-ratio", type=float, default=0.01)
    parser.add_argument("--min-nonblank-ratio", type=float, default=0.01)
    parser.add_argument("--wait-ms", type=int, default=300)
    parser.add_argument(
        "--browser-channel",
        default=None,
        help="Use an installed browser channel such as chrome or msedge instead of Playwright's bundled Chromium. Defaults to PLAYWRIGHT_BROWSER_CHANNEL or an auto-detected system browser.",
    )
    parser.add_argument(
        "--no-auto-setup",
        action="store_true",
        help="Do not run setup_visual_validation.py automatically when Playwright/browser dependencies are missing.",
    )
    args = parser.parse_args()

    folder = args.output_folder
    if not folder.is_dir():
        fail(f"Output folder not found: {folder}")
    prototypes = find_prototypes(folder, args.prototype)
    viewport_values = args.viewport or ["desktop=1440x1000", "mobile=390x844"]
    viewports = [parse_viewport(value) for value in viewport_values]
    output_dir = folder / args.output_dir
    browser_channel = (
        args.browser_channel
        or os.environ.get("PLAYWRIGHT_BROWSER_CHANNEL")
        or installed_browser_channel()
    )

    report: dict[str, object] = {
        "output_dir": output_dir.as_posix(),
        "baseline_dir": args.baseline_dir.as_posix() if args.baseline_dir else None,
        "browser_channel": browser_channel,
        "max_diff_ratio": args.max_diff_ratio,
        "min_nonblank_ratio": args.min_nonblank_ratio,
    }
    multiple_prototypes = len(prototypes) > 1
    failures: list[str] = []
    prototype_reports: list[dict[str, object]] = []

    for prototype in prototypes:
        prototype_output_dir = output_dir / prototype.stem if multiple_prototypes else output_dir
        baseline_dir = None
        if args.baseline_dir:
            baseline_dir = args.baseline_dir / prototype.stem if multiple_prototypes else args.baseline_dir
        screenshots = capture_screenshots(
            prototype,
            viewports,
            prototype_output_dir,
            args.wait_ms,
            browser_channel,
            not args.no_auto_setup,
        )
        viewport_reports = []
        prototype_failures: list[str] = []
        for screenshot in screenshots:
            stats = screenshot_stats(screenshot)
            viewport_report: dict[str, object] = {
                "name": screenshot.stem,
                "screenshot": screenshot.relative_to(folder).as_posix(),
                "stats": stats,
            }
            if stats["non_blank_ratio"] < args.min_nonblank_ratio:
                prototype_failures.append(f"{screenshot.name} appears blank")

            if baseline_dir:
                baseline_dir.mkdir(parents=True, exist_ok=True)
                baseline = baseline_dir / screenshot.name
                if args.update_baseline or not baseline.exists():
                    shutil.copyfile(screenshot, baseline)
                    viewport_report["baseline"] = baseline.as_posix()
                    viewport_report["diff"] = {"status": "baseline_updated"}
                else:
                    diff = diff_png(screenshot, baseline)
                    viewport_report["baseline"] = baseline.as_posix()
                    viewport_report["diff"] = diff
                    if float(diff["diff_ratio"]) > args.max_diff_ratio:
                        prototype_failures.append(
                            f"{screenshot.name} diff ratio {diff['diff_ratio']} exceeds "
                            f"{args.max_diff_ratio}"
                        )
            viewport_reports.append(viewport_report)

        failures.extend(f"{prototype.name}: {failure}" for failure in prototype_failures)
        prototype_report = {
            "prototype": prototype.name,
            "output_dir": prototype_output_dir.relative_to(folder).as_posix(),
            "baseline_dir": baseline_dir.as_posix() if baseline_dir else None,
            "viewports": viewport_reports,
            "status": "failed" if prototype_failures else "passed",
            "failures": prototype_failures,
        }
        prototype_reports.append(prototype_report)

    report["prototypes"] = prototype_reports
    if len(prototypes) == 1:
        single_report = prototype_reports[0]
        report["prototype"] = single_report["prototype"]
        report["viewports"] = single_report["viewports"]
    report["status"] = "failed" if failures else "passed"
    report["failures"] = failures
    report_path = output_dir / "visual-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if failures:
        fail(f"Prototype visual validation failed; see {report_path}")
    print(f"PM Copilot prototype visual validation passed: {report_path}")


if __name__ == "__main__":
    main()
