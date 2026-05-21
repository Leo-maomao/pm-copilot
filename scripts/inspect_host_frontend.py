#!/usr/bin/env python3
"""Inspect a host repository for frontend source-rendered prototype inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


IGNORED_DIRS = {
    ".git",
    ".next",
    ".nuxt",
    ".output",
    ".turbo",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "outputs",
    "target",
}

ENTRY_NAMES = {
    "package.json",
    "vite.config.ts",
    "vite.config.js",
    "next.config.js",
    "next.config.mjs",
    "nuxt.config.ts",
    "app.json",
    "app.config.ts",
    "app.config.js",
    "project.config.json",
    "pages.json",
    "manifest.json",
    "pubspec.yaml",
    "Podfile",
}

ROUTE_PARTS = {
    "app",
    "pages",
    "routes",
    "screens",
    "views",
    "features",
    "subpackages",
}

COMPONENT_PARTS = {
    "components",
    "widgets",
    "ui",
    "design-system",
    "design_system",
}

STYLE_SUFFIXES = {
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".wxss",
    ".acss",
    ".ttss",
}

SOURCE_SUFFIXES = {
    ".tsx",
    ".ts",
    ".jsx",
    ".js",
    ".vue",
    ".svelte",
    ".wxml",
    ".axml",
    ".ttml",
    ".dart",
    ".kt",
    ".swift",
    ".xml",
}

ASSET_SUFFIXES = {
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".ttf",
    ".otf",
    ".woff",
    ".woff2",
}


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def should_skip(path: Path) -> bool:
    return any(part in IGNORED_DIRS for part in path.parts)


def limited_append(items: list[str], value: str, limit: int) -> None:
    if len(items) >= limit or value in items:
        return
    items.append(value)


def read_package_json(root: Path) -> dict[str, Any]:
    package_path = root / "package.json"
    if not package_path.is_file():
        return {}
    try:
        return json.loads(package_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def dependency_names(package: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for field in ("dependencies", "devDependencies", "peerDependencies"):
        value = package.get(field)
        if isinstance(value, dict):
            names.update(value.keys())
    return names


def script_command(package: dict[str, Any]) -> str:
    scripts = package.get("scripts") if isinstance(package, dict) else {}
    if not isinstance(scripts, dict):
        return ""
    for name in ("dev", "start", "storybook", "preview", "serve", "h5:dev", "weapp:dev"):
        command = scripts.get(name)
        if isinstance(command, str) and command.strip():
            return f"npm run {name}"
    return ""


def detect_platform(root: Path, package: dict[str, Any]) -> tuple[str, list[str]]:
    deps = dependency_names(package)
    candidates: list[str] = []
    if {"@tarojs/taro", "@tarojs/cli"} & deps or (root / "config/index.ts").is_file():
        candidates.append("taro")
    if (root / "pages.json").is_file() and (root / "manifest.json").is_file():
        candidates.append("uni_app")
    if (root / "project.config.json").is_file() or (root / "miniprogram").is_dir():
        candidates.append("mini_program")
    if "react-native" in deps or (root / "android").is_dir() or (root / "ios").is_dir():
        candidates.append("react_native")
    if (root / "pubspec.yaml").is_file() or (root / "lib/main.dart").is_file():
        candidates.append("flutter")
    if (root / "android").is_dir() or (root / "ios").is_dir():
        candidates.append("native_app")
    if deps or any((root / name).exists() for name in ("src", "app", "pages")):
        if {"next", "nuxt", "vite", "react", "vue", "svelte", "@angular/core"} & deps:
            candidates.append("web")
        elif not candidates:
            candidates.append("web")
    if not candidates:
        candidates.append("unknown")
    return candidates[0], candidates


def classify_files(root: Path, limit: int) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {
        "entry_files": [],
        "route_or_screen_files": [],
        "component_files": [],
        "style_files": [],
        "icon_asset_sources": [],
        "data_or_mock_sources": [],
    }
    for path in sorted(root.rglob("*")):
        if not path.is_file() or should_skip(path.relative_to(root)):
            continue
        relative = rel(path, root)
        parts = {part.lower() for part in path.relative_to(root).parts}
        lower_name = path.name.lower()
        suffix = path.suffix.lower()
        if path.name in ENTRY_NAMES or lower_name in ENTRY_NAMES:
            limited_append(result["entry_files"], relative, limit)
        if suffix in SOURCE_SUFFIXES and parts & ROUTE_PARTS:
            limited_append(result["route_or_screen_files"], relative, limit)
        if suffix in SOURCE_SUFFIXES and parts & COMPONENT_PARTS:
            limited_append(result["component_files"], relative, limit)
        if suffix in STYLE_SUFFIXES or lower_name in {"tailwind.config.js", "tailwind.config.ts"}:
            limited_append(result["style_files"], relative, limit)
        if suffix in ASSET_SUFFIXES or "icons" in parts or "icon" in lower_name:
            limited_append(result["icon_asset_sources"], relative, limit)
        if (
            "mock" in parts
            or "mocks" in parts
            or "fixtures" in parts
            or "data" in parts
            or lower_name.endswith(".mock.ts")
            or lower_name.endswith(".mock.js")
        ):
            limited_append(result["data_or_mock_sources"], relative, limit)
    return result


def preview_surface(root: Path, files: dict[str, list[str]]) -> str:
    for candidate in files["route_or_screen_files"]:
        return candidate
    for candidate in files["component_files"]:
        return candidate
    for fallback in ("src/App.tsx", "src/App.vue", "app/page.tsx", "pages/index/index.wxml", "lib/main.dart"):
        if (root / fallback).exists():
            return fallback
    return ""


def build_report(root: Path, limit: int) -> dict[str, Any]:
    package = read_package_json(root)
    platform, platform_candidates = detect_platform(root, package)
    files = classify_files(root, limit)
    command = script_command(package)
    if not command and platform == "flutter":
        command = "flutter run"
    elif not command and platform in {"react_native", "native_app"}:
        command = "npm run start or platform simulator command"
    elif not command and platform in {"mini_program", "taro", "uni_app"}:
        command = "platform devtools or framework dev command required"

    missing = [key for key in ("entry_files", "route_or_screen_files", "component_files", "style_files") if not files[key]]
    render_available = bool(command and preview_surface(root, files))
    report: dict[str, Any] = {
        "host_project_root": str(root),
        "platform": platform,
        "platform_candidates": platform_candidates,
        **files,
        "render_entrypoint": command,
        "preview_surface": preview_surface(root, files),
        "source_rendering_decision": "used" if render_available else "blocked",
        "source_rendering_limitation": "" if render_available else "missing render command or preview surface",
        "missing_required_inventory": missing,
        "recommended_artifact_mode": recommended_mode(platform, render_available),
    }
    return report


def recommended_mode(platform: str, render_available: bool) -> str:
    if not render_available:
        return "self_contained_html_from_host_code"
    if platform in {"mini_program", "taro", "uni_app"}:
        return "mini_program_preview"
    if platform in {"react_native", "flutter", "native_app"}:
        return "app_preview_screen"
    return "source_delta_patch"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=Path, default=Path.cwd(), help="Host repository root to inspect")
    parser.add_argument("--limit", type=int, default=30, help="Maximum files to list per inventory field")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    host = args.host.resolve()
    if not host.is_dir():
        raise SystemExit(f"Host repository not found: {host}")
    report = build_report(host, args.limit)
    print(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))


if __name__ == "__main__":
    main()
