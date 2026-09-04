#!/usr/bin/env python3
"""Freeze read-only implementation evidence from the invoking host repository."""

from __future__ import annotations

import argparse
import json
import os
import re
import select
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from inspect_host_frontend import build_report


MAX_CHANGED_FILES = 80
MAX_SNIPPET_CHARS = 4_000
_LOCAL_URL = re.compile(r"https?://(?:127\.0\.0\.1|localhost|0\.0\.0\.0):\d+(?:/[^\s'\"]*)?", re.I)


def _run(root: Path, *command: str) -> tuple[int, str]:
    result = subprocess.run(
        command, cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    return result.returncode, (result.stdout or result.stderr).strip()


def _git_lines(root: Path, *command: str) -> list[str]:
    code, output = _run(root, "git", *command)
    return output.splitlines() if code == 0 and output else []


def _changed_files(root: Path) -> list[str]:
    files = [
        *_git_lines(root, "diff", "--name-only", "HEAD"),
        *_git_lines(root, "diff", "--cached", "--name-only"),
        *_git_lines(root, "ls-files", "--others", "--exclude-standard"),
    ]
    return list(dict.fromkeys(path for path in files if path.strip()))[:MAX_CHANGED_FILES]


def _snippets(root: Path, paths: list[str]) -> list[dict[str, str]]:
    snippets: list[dict[str, str]] = []
    for relative in paths:
        path = root / relative
        if not path.is_file() or path.suffix.lower() not in {
            ".ts", ".tsx", ".js", ".jsx", ".vue", ".svelte", ".py", ".html", ".css", ".scss",
        }:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")[:MAX_SNIPPET_CHARS]
        except OSError:
            continue
        snippets.append({"path": relative, "excerpt": content})
    return snippets


def _candidate_url(output: str) -> str | None:
    match = _LOCAL_URL.search(output)
    if not match:
        return None
    return match.group(0).replace("0.0.0.0", "127.0.0.1")


def _capture_real_figure(root: Path, report: dict[str, Any], result_dir: Path) -> dict[str, Any]:
    """Attempt one bounded local capture and always return auditable facts."""
    command = str(report.get("render_entrypoint") or "").strip()
    platform = str(report.get("platform") or "")
    if not command.startswith("npm run ") or platform not in {"web", "unknown"}:
        return {"status": "not_attempted", "reason": "no supported local web preview command"}
    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(
            shlex.split(command), cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        output = ""
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            readable, _, _ = select.select([process.stdout] if process.stdout is not None else [], [], [], 0.2)
            if readable and process.stdout is not None:
                line = process.stdout.readline()
                if line:
                    output += line
                    url = _candidate_url(output)
                    if url:
                        asset_name = f"implemented-feature-real-{time.time_ns()}.png"
                        asset = result_dir / asset_name
                        capture = subprocess.run(
                            [sys.executable, str(Path(__file__).with_name("capture_frontend_figure.py")), url,
                             "--output", str(asset)],
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
                        )
                        return {
                            "status": "captured" if capture.returncode == 0 and asset.is_file() else "failed",
                            "url": url,
                            "path": f"tool-results/implemented-evidence/{asset_name}" if asset.is_file() else "",
                            "prd_asset_path": f"assets/{asset_name}" if asset.is_file() else "",
                            "capture_stdout": capture.stdout[-1000:], "capture_stderr": capture.stderr[-1000:],
                            "preview_output": output[-2000:],
                        }
            if process.poll() is not None:
                break
            time.sleep(0.2)
        return {"status": "failed", "reason": "preview did not expose a local URL", "preview_output": output[-2000:]}
    except OSError as error:
        return {"status": "failed", "reason": str(error)}
    finally:
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except OSError:
                    pass


def collect(root: Path, query: str, run_folder: Path) -> dict[str, Any]:
    """Collect a portable evidence packet and its run-local detailed report."""
    root = root.resolve()
    result_dir = run_folder / "tool-results" / "implemented-evidence"
    result_dir.mkdir(parents=True, exist_ok=True)
    frontend = build_report(root, limit=30, query=query)
    changed = _changed_files(root)
    branch_code, branch = _run(root, "git", "branch", "--show-current")
    branch = branch if branch_code == 0 and branch else "detached-or-non-git"
    capture = _capture_real_figure(root, frontend, result_dir)
    collection = {
        "host_project_root": str(root), "branch_name": branch,
        "diff_commands": ["git diff --name-only HEAD", "git diff --cached --name-only", "git ls-files --others --exclude-standard"],
        "changed_files": changed, "frontend_inventory": frontend,
        "changed_file_snippets": _snippets(root, changed), "real_frontend_capture": capture,
    }
    result_path = result_dir / "collection.json"
    result_path.write_text(json.dumps(collection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result_ref = "tool-results/implemented-evidence/collection.json"
    behavior = [{
        "evidence_id": f"implementation-{index}", "observed_behavior": f"Implemented surface candidate: {path}",
        "source_file": path, "result_ref": result_ref,
    } for index, path in enumerate(changed, 1)] or [{
        "evidence_id": "implementation-inventory", "observed_behavior": "No uncommitted file was found; inspect the recorded frontend inventory and selected branch.",
        "result_ref": result_ref,
    }]
    tests = [path for path in changed if re.search(r"(?:^|/)(?:test|tests|__tests__|spec)(?:/|\.)", path, re.I)]
    return {
        "branch_name": branch,
        "diff_commands": collection["diff_commands"],
        "changed_files": changed or ["No uncommitted paths; see collection report."],
        "behavior_evidence": behavior,
        "validation_evidence": [{"command": "changed test inventory", "status": "observed", "files": tests, "result_ref": result_ref}],
        "visual_runtime_capability": {
            "frontend_inventory": frontend,
            "real_frontend_capture": capture,
            "collection_result": {"result_ref": result_ref},
        },
        "screenshots_and_placeholders": [],
        "collection_provenance": {"mode": "automatic_host_repository_collection", "result_ref": result_ref},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", type=Path, default=Path.cwd())
    parser.add_argument("--request", default="")
    parser.add_argument("--run-folder", type=Path, required=True)
    args = parser.parse_args()
    if not args.host.is_dir():
        raise SystemExit(f"host repository not found: {args.host}")
    print(json.dumps(collect(args.host, args.request, args.run_folder), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
