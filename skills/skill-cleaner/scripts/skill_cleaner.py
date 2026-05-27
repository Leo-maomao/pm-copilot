#!/usr/bin/env python3
"""Read-only skill layer auditor for PM Copilot and Codex-style skills."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


DEFAULT_CONTEXT_TOKENS = 272_000
DEFAULT_MODEL = "gpt-5.5"


@dataclass
class Skill:
    name: str
    description: str
    path: Path
    root: Path
    source_kind: str
    body: str

    @property
    def rendered_line(self) -> str:
        if self.description:
            return f"- {self.name}: {self.description} (file: {self.path})"
        return f"- {self.name} (file: {self.path})"

    @property
    def min_line(self) -> str:
        return f"- {self.name} (file: {self.path})"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", default=[], help="Additional skill root to scan.")
    parser.add_argument("--months", type=int, default=3, help="Recent Codex log window for usage evidence.")
    parser.add_argument("--no-logs", action="store_true", help="Skip Codex log scanning.")
    parser.add_argument("--max-log-mb", type=int, default=300, help="Maximum recent log MB to scan.")
    parser.add_argument("--context-tokens", type=int, default=0, help="Override model context window.")
    parser.add_argument("--budget-percent", type=float, default=2.0, help="Skill-list budget as percent of context.")
    parser.add_argument("--chars-per-token", type=float, default=4.0, help="Token estimate divisor.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model name to look up in models_cache.json.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown.")
    return parser.parse_args()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def expand_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def default_roots(root: Path) -> list[Path]:
    candidates = [
        root / "skills",
        Path("~/.codex/skills").expanduser(),
        Path("~/.codex/plugins/cache").expanduser(),
        Path("~/.agents/skills").expanduser(),
    ]
    return [candidate.resolve() for candidate in candidates if candidate.exists()]


def unique_roots(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    roots: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen or not resolved.exists():
            continue
        seen.add(resolved)
        roots.append(resolved)
    return roots


def source_kind(path: Path, root: Path, project_root: Path) -> str:
    path_text = str(path)
    root_text = str(root)
    if root == project_root / "skills" or path.is_relative_to(project_root / "skills"):
        return "repo"
    if "/.codex/plugins/cache/" in path_text:
        return "plugin"
    if root_text.endswith("/.codex/skills") or "/.codex/skills/" in path_text:
        return "codex"
    if root_text.endswith("/.agents/skills") or "/.agents/skills/" in path_text:
        return "agents"
    return "extra"


def find_skill_files(roots: list[Path]) -> list[tuple[Path, Path]]:
    discovered: list[tuple[Path, Path]] = []
    seen_files: set[Path] = set()
    for root in roots:
        for skill_file in root.rglob("SKILL.md"):
            try:
                resolved = skill_file.resolve()
            except OSError:
                continue
            if resolved in seen_files:
                continue
            seen_files.add(resolved)
            discovered.append((resolved, root))
    return sorted(discovered, key=lambda item: str(item[0]))


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def sanitize_inline(value: str) -> str:
    return re.sub(r"\s+", " ", strip_quotes(value)).strip()


def parse_frontmatter(text: str, fallback_name: str) -> tuple[str, str]:
    if not text.startswith("---"):
        return fallback_name, ""

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return fallback_name, ""

    frontmatter: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        frontmatter.append(line)
    else:
        return fallback_name, ""

    data: dict[str, str] = {}
    for line in frontmatter:
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match:
            data[match.group(1)] = sanitize_inline(match.group(2))

    name = data.get("name") or fallback_name
    description = data.get("description", "")
    return sanitize_inline(name), sanitize_inline(description)


def read_skills(roots: list[Path], project_root: Path) -> list[Skill]:
    skills: list[Skill] = []
    for path, root in find_skill_files(roots):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="replace")
        name, description = parse_frontmatter(text, path.parent.name)
        skills.append(
            Skill(
                name=name,
                description=description,
                path=path,
                root=root,
                source_kind=source_kind(path, root, project_root),
                body=text,
            )
        )
    return sorted(skills, key=lambda skill: (skill.source_kind, skill.name, str(skill.path)))


def token_cost(text: str, chars_per_token: float) -> int:
    return math.ceil(len(text.encode("utf-8")) / chars_per_token)


def find_context_tokens(model: str, override: int) -> tuple[int, str]:
    if override > 0:
        return override, "--context-tokens"

    cache_path = Path("~/.codex/models_cache.json").expanduser()
    if not cache_path.exists():
        return DEFAULT_CONTEXT_TOKENS, "fallback"

    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return DEFAULT_CONTEXT_TOKENS, "fallback"

    value = find_context_window(data, model)
    if value:
        return value, str(cache_path)
    return DEFAULT_CONTEXT_TOKENS, "fallback"


def find_context_window(data: Any, model: str) -> int | None:
    if isinstance(data, dict):
        if data.get("id") == model and isinstance(data.get("context_window"), int):
            return int(data["context_window"])
        if data.get("slug") == model and isinstance(data.get("context_window"), int):
            return int(data["context_window"])
        if model in data:
            nested = data[model]
            if isinstance(nested, dict) and isinstance(nested.get("context_window"), int):
                return int(nested["context_window"])
        for value in data.values():
            found = find_context_window(value, model)
            if found:
                return found
    elif isinstance(data, list):
        for value in data:
            found = find_context_window(value, model)
            if found:
                return found
    return None


def root_summary(skills: list[Skill]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter(str(skill.root) for skill in skills)
    return [{"root": root, "skills": count} for root, count in sorted(counts.items())]


def similarity(left: str, right: str) -> float:
    if left == right:
        return 1.0
    return SequenceMatcher(a=left, b=right).ratio()


def keep_priority(skill: Skill) -> tuple[int, str]:
    rank = {
        "repo": 0,
        "codex": 1,
        "plugin": 2,
        "agents": 3,
        "extra": 4,
    }.get(skill.source_kind, 9)
    return rank, str(skill.path)


def duplicate_report(skills: list[Skill]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    by_name: defaultdict[str, list[Skill]] = defaultdict(list)
    for skill in skills:
        by_name[skill.name].append(skill)

    name_groups: list[dict[str, Any]] = []
    delete_suggestions: list[dict[str, Any]] = []
    for name, group in sorted(by_name.items()):
        if len(group) < 2:
            continue
        keep = sorted(group, key=keep_priority)[0]
        entries = []
        for skill in sorted(group, key=keep_priority):
            entries.append(
                {
                    "source": skill.source_kind,
                    "path": str(skill.path),
                    "body_similarity": round(similarity(skill.body, keep.body) * 100, 1),
                    "description_similarity": round(similarity(skill.description, keep.description) * 100, 1),
                }
            )
        name_groups.append({"name": name, "keep": str(keep.path), "entries": entries})

        delete = [
            entry
            for entry in entries
            if entry["path"] != str(keep.path)
            and entry["body_similarity"] >= 98
            and entry["description_similarity"] >= 98
        ]
        if delete:
            delete_suggestions.append({"name": name, "keep": str(keep.path), "delete": delete})

    by_hash: defaultdict[str, list[Skill]] = defaultdict(list)
    for skill in skills:
        digest = hashlib.sha256(normalize_body(skill.body).encode("utf-8")).hexdigest()
        by_hash[digest].append(skill)

    hash_groups = []
    for group in by_hash.values():
        if len(group) < 2:
            continue
        hash_groups.append(
            {
                "names": [skill.name for skill in group],
                "paths": [str(skill.path) for skill in sorted(group, key=keep_priority)],
            }
        )
    return name_groups, delete_suggestions, hash_groups


def normalize_body(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def description_candidates(skills: list[Skill]) -> list[dict[str, Any]]:
    candidates = []
    for skill in skills:
        if len(skill.description) < 140:
            continue
        candidates.append(
            {
                "name": skill.name,
                "path": str(skill.path),
                "description_chars": len(skill.description),
                "rendered_line_chars": len(skill.rendered_line),
                "current": skill.description,
                "recommendation": "Consider <=140 chars while preserving trigger nouns and artifact names.",
            }
        )
    return sorted(candidates, key=lambda item: item["description_chars"], reverse=True)


def collect_log_files(months: int) -> list[Path]:
    codex_home = Path("~/.codex").expanduser()
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(months, 0) * 31)
    candidates: list[Path] = []

    history = codex_home / "history.jsonl"
    if history.exists():
        candidates.append(history)

    sessions = codex_home / "sessions"
    if sessions.exists():
        candidates.extend(sessions.rglob("*.jsonl"))

    recent: list[Path] = []
    for path in candidates:
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        except OSError:
            continue
        if months <= 0 or mtime >= cutoff:
            recent.append(path)
    return sorted(recent, key=lambda path: path.stat().st_mtime if path.exists() else 0, reverse=True)


def scan_usage(skills: list[Skill], months: int, max_log_mb: int) -> tuple[dict[str, dict[str, int]], int, int]:
    usage = {
        str(skill.path): {
            "dollar_mentions": 0,
            "path_reads": 0,
            "skill_path_text": 0,
        }
        for skill in skills
    }
    max_bytes = max_log_mb * 1024 * 1024
    scanned_files = 0
    scanned_bytes = 0

    for path in collect_log_files(months):
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if scanned_bytes + size > max_bytes and scanned_files > 0:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        scanned_files += 1
        scanned_bytes += size

        for skill in skills:
            record = usage[str(skill.path)]
            escaped_name = re.escape(skill.name)
            record["dollar_mentions"] += len(re.findall(rf"\${escaped_name}\b", text))
            record["path_reads"] += text.count(str(skill.path))
            record["skill_path_text"] += text.count(f"skills/{skill.name}/SKILL.md")

    return usage, scanned_files, scanned_bytes


def unused_candidates(skills: list[Skill], usage: dict[str, dict[str, int]] | None) -> list[dict[str, Any]]:
    if usage is None:
        return []
    candidates = []
    for skill in skills:
        record = usage[str(skill.path)]
        evidence = sum(record.values())
        if evidence > 0:
            continue
        if skill.source_kind in {"plugin", "codex"}:
            continue
        candidates.append(
            {
                "name": skill.name,
                "source": skill.source_kind,
                "path": str(skill.path),
                **record,
            }
        )
    return candidates


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    project_root = repo_root()
    roots = unique_roots(default_roots(project_root) + [expand_path(root) for root in args.root])
    skills = read_skills(roots, project_root)
    context_tokens, context_source = find_context_tokens(args.model, args.context_tokens)
    budget_tokens = math.floor(context_tokens * args.budget_percent / 100)
    full_tokens = sum(token_cost(skill.rendered_line, args.chars_per_token) for skill in skills)
    min_tokens = sum(token_cost(skill.min_line, args.chars_per_token) for skill in skills)
    name_groups, delete_suggestions, hash_groups = duplicate_report(skills)

    usage = None
    log_files_scanned = 0
    log_bytes_scanned = 0
    if not args.no_logs:
        usage, log_files_scanned, log_bytes_scanned = scan_usage(skills, args.months, args.max_log_mb)

    return {
        "generated": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "months": args.months,
        "skills_discovered": len(skills),
        "description_chars": sum(len(skill.description) for skill in skills),
        "rendered_line_chars": sum(len(skill.rendered_line) for skill in skills),
        "log_files_scanned": log_files_scanned,
        "log_bytes_scanned": log_bytes_scanned,
        "budget": {
            "model": args.model,
            "context_tokens": context_tokens,
            "context_source": context_source,
            "budget_percent": args.budget_percent,
            "budget_tokens": budget_tokens,
            "chars_per_token": args.chars_per_token,
            "full_tokens": full_tokens,
            "minimum_no_description_tokens": min_tokens,
            "used_of_budget_percent": round((full_tokens / budget_tokens * 100), 1) if budget_tokens else 0,
            "used_of_context_percent": round((full_tokens / context_tokens * 100), 2) if context_tokens else 0,
            "remaining_budget_tokens": budget_tokens - full_tokens,
            "over_budget": full_tokens > budget_tokens,
        },
        "description_candidates": description_candidates(skills),
        "duplicates_by_name": name_groups,
        "duplicate_delete_suggestions": delete_suggestions,
        "duplicates_by_body_hash": hash_groups,
        "unused_candidates": unused_candidates(skills, usage),
        "root_summary": root_summary(skills),
        "skills": [
            {
                "name": skill.name,
                "description": skill.description,
                "path": str(skill.path),
                "root": str(skill.root),
                "source": skill.source_kind,
            }
            for skill in skills
        ],
        "logs_skipped": args.no_logs,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Skill Cleaner Report",
        "",
        f"generated: {report['generated']}",
        f"months: {report['months']}",
        f"skills: {report['skills_discovered']} discovered",
        f"description_chars: {report['description_chars']}",
        f"rendered_line_chars: {report['rendered_line_chars']}",
        f"log_files_scanned: {report['log_files_scanned']}",
        "",
        "## Skill Budget",
        "",
    ]

    budget = report["budget"]
    lines.extend(
        [
            f"model: {budget['model']}",
            f"context_tokens: {budget['context_tokens']:,}",
            f"context_source: {budget['context_source']}",
            f"{budget['budget_percent']}%_budget_tokens: {budget['budget_tokens']:,}",
            f"estimated_full_tokens: {budget['full_tokens']:,}",
            f"minimum_no_description_tokens: {budget['minimum_no_description_tokens']:,}",
            f"used_of_budget: {budget['used_of_budget_percent']}%",
            f"used_of_context: {budget['used_of_context_percent']}%",
            f"remaining_budget_tokens: {budget['remaining_budget_tokens']:,}",
            f"over_budget: {str(budget['over_budget']).lower()}",
            "",
            "## Description Candidates",
            "",
        ]
    )

    if report["description_candidates"]:
        for item in report["description_candidates"]:
            lines.extend(
                [
                    f"- {item['name']}",
                    f"  path: {item['path']}",
                    f"  chars: description={item['description_chars']}, rendered_line={item['rendered_line_chars']}",
                    f"  recommendation: {item['recommendation']}",
                ]
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Duplicates By Name", ""])
    if report["duplicates_by_name"]:
        for group in report["duplicates_by_name"]:
            lines.append(f"- {group['name']}")
            lines.append(f"  keep-default: {group['keep']}")
            for entry in group["entries"]:
                lines.append(
                    f"  - {entry['source']}: {entry['path']} "
                    f"(body={entry['body_similarity']}%, description={entry['description_similarity']}%)"
                )
    else:
        lines.append("- none")

    lines.extend(["", "## Duplicate Delete Suggestions", ""])
    if report["duplicate_delete_suggestions"]:
        for group in report["duplicate_delete_suggestions"]:
            lines.append(f"- {group['name']}")
            lines.append(f"  keep: {group['keep']}")
            for entry in group["delete"]:
                lines.append(
                    f"  delete: {entry['source']}: {entry['path']} "
                    f"(body={entry['body_similarity']}%, description={entry['description_similarity']}%)"
                )
    else:
        lines.append("- none")

    lines.extend(["", "## Duplicates By Body Hash", ""])
    if report["duplicates_by_body_hash"]:
        for group in report["duplicates_by_body_hash"]:
            lines.append(f"- {', '.join(group['names'])}")
            for path in group["paths"]:
                lines.append(f"  - {path}")
    else:
        lines.append("- none")

    lines.extend(["", "## Unused Candidates", ""])
    if report["logs_skipped"]:
        lines.append("- not evaluated (--no-logs)")
    elif report["unused_candidates"]:
        for item in report["unused_candidates"]:
            lines.append(
                f"- {item['name']}: {item['source']}; usage=${item['dollar_mentions']}, "
                f"reads={item['path_reads']}, text={item['skill_path_text']}; {item['path']}"
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Root Summary", ""])
    if report["root_summary"]:
        for item in report["root_summary"]:
            lines.append(f"- {item['root']}: {item['skills']} skills")
    else:
        lines.append("- none")

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    report = build_report(args)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
