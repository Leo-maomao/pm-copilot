#!/usr/bin/env python3
"""Recover a local Pandoc binary without requiring a package manager."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def local_pandoc_path() -> str:
    candidate = Path.home() / ".local" / "bin" / "pandoc"
    return str(candidate) if candidate.is_file() and candidate.stat().st_mode & 0o111 else ""


def find_pandoc() -> str:
    return shutil.which("pandoc") or local_pandoc_path()


def install_official_binary() -> tuple[bool, str]:
    """Use pypandoc only as a downloader for the official Pandoc macOS binary."""
    try:
        import pypandoc
    except ImportError:
        return False, "Official binary downloader is unavailable"
    target = Path.home() / ".local" / "bin"
    try:
        target.mkdir(parents=True, exist_ok=True)
        pypandoc.download_pandoc(targetfolder=str(target), version="latest", delete_installer=True)
    except Exception as error:
        return False, f"Official Pandoc binary download failed: {error}"
    pandoc = find_pandoc()
    return (True, f"pandoc={pandoc}") if pandoc else (False, "Official binary download completed without a usable pandoc")


def report(status: str, evidence: str, attempted: bool) -> int:
    print(json.dumps({"status": status, "evidence": evidence, "attempted": attempted}, ensure_ascii=False))
    return 0 if status in {"available", "installed"} else 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true", help="Recover Pandoc from the official binary, then Homebrew if available.")
    args = parser.parse_args()

    pandoc = find_pandoc()
    if pandoc:
        raise SystemExit(report("available", f"pandoc={pandoc}", False))
    if not args.install:
        raise SystemExit(report("setup_required", "pandoc is not on PATH", False))

    installed, evidence = install_official_binary()
    if installed:
        raise SystemExit(report("installed", evidence, True))

    brew = shutil.which("brew")
    if not brew:
        raise SystemExit(report("not_available", f"{evidence}; Homebrew is not installed; use the built-in local renderer", True))
    result = subprocess.run([brew, "install", "pandoc"], text=True, capture_output=True, check=False)
    if result.returncode != 0:
        evidence = (result.stderr or result.stdout or "brew install pandoc failed").strip()
        raise SystemExit(report("failed", evidence, True))
    pandoc = find_pandoc()
    if not pandoc:
        raise SystemExit(report("failed", "Homebrew completed but pandoc is not on PATH", True))
    raise SystemExit(report("installed", f"pandoc={pandoc}", True))


if __name__ == "__main__":
    main()
