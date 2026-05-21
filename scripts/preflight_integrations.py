#!/usr/bin/env python3
"""Check PM Copilot external integration candidates without exposing secrets."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "tools" / "external-tool-catalog.json"
TIER_ORDER = {"core": 0, "recommended": 1, "optional": 2, "hold": 3}
BLOCKING_STATUSES = {"blocked", "unavailable", "setup_required"}


def load_catalog(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"Catalog not found: {path}") from None
    except json.JSONDecodeError as error:
        raise SystemExit(f"Catalog is not valid JSON: {path}: {error}") from None


def tier_included(tool_tier: str, requested: str) -> bool:
    if requested == "all":
        return True
    return TIER_ORDER.get(tool_tier, 99) <= TIER_ORDER[requested]


def check_url(url: str, timeout: float) -> dict[str, Any]:
    if not url:
        return {"checked": False, "status": "skipped", "evidence": "no source_url"}

    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "pm-copilot-preflight"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {
                "checked": True,
                "status": "available",
                "code": response.status,
                "evidence": f"HEAD {url} returned {response.status}",
            }
    except urllib.error.HTTPError as head_error:
        if 300 <= head_error.code < 400:
            return {
                "checked": True,
                "status": "available",
                "code": head_error.code,
                "evidence": f"HEAD {url} returned redirect {head_error.code}",
            }
        head_evidence = str(head_error)
    except Exception as head_error:
        head_evidence = str(head_error)

    request = urllib.request.Request(url, method="GET", headers={"User-Agent": "pm-copilot-preflight"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {
                "checked": True,
                "status": "available",
                "code": response.status,
                "evidence": f"GET {url} returned {response.status}; HEAD failed: {head_evidence}",
            }
    except urllib.error.HTTPError as get_error:
        if 300 <= get_error.code < 400:
            return {
                "checked": True,
                "status": "available",
                "code": get_error.code,
                "evidence": f"GET {url} returned redirect {get_error.code}; HEAD failed: {head_evidence}",
            }
        return {
            "checked": True,
            "status": "unavailable",
            "evidence": f"HEAD failed: {head_evidence}; GET failed: {get_error}",
        }
    except Exception as get_error:
        return {
            "checked": True,
            "status": "unavailable",
            "evidence": f"HEAD failed: {head_evidence}; GET failed: {get_error}",
        }


def evaluate_tool(tool: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    env_requirements = tool.get("credentials_required", [])
    missing_env = [name for name in env_requirements if not os.environ.get(name)]
    commands = tool.get("command_checks", [])
    missing_commands = [command for command in commands if shutil.which(command) is None]
    source_check = check_url(tool.get("source_url", ""), args.timeout) if args.check_remote else {
        "checked": False,
        "status": "skipped",
        "evidence": "remote source check not requested",
    }

    status = "available" if tool.get("default_enabled") else "candidate"
    limitations: list[str] = []
    if not tool.get("default_enabled"):
        limitations.append("not enabled by default")

    verification = tool.get("verification", {})
    candidate_status = verification.get("candidate_status", "candidate")
    if candidate_status in {"experimental_candidate", "community_candidate"}:
        status = "candidate"
        limitations.append(f"candidate_status={candidate_status}")

    if tool.get("tier") == "hold":
        status = "hold"
        limitations.append("catalog tier is hold")

    if missing_commands:
        status = "setup_required"
        limitations.append(f"missing commands: {', '.join(missing_commands)}")

    if missing_env:
        status = "setup_required"
        limitations.append(f"missing credentials: {', '.join(missing_env)}")

    if source_check["status"] == "unavailable":
        status = "unavailable"
        limitations.append(f"source unavailable: {source_check['evidence']}")

    return {
        "id": tool["id"],
        "name": tool["name"],
        "category": tool["category"],
        "tier": tool["tier"],
        "default_enabled": tool["default_enabled"],
        "status": status,
        "source_type": tool["source_type"],
        "source_url": tool["source_url"],
        "cost_risk": tool["cost_risk"],
        "credentials_required": env_requirements,
        "missing_credentials": missing_env,
        "command_checks": commands,
        "missing_commands": missing_commands,
        "permission_boundary": tool["permission_boundary"],
        "data_risk": tool["data_risk"],
        "fallback": tool["fallback"],
        "source_check": source_check,
        "limitations": limitations,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    catalog = load_catalog(args.catalog)
    selected_tools = [
        tool for tool in catalog.get("tools", [])
        if tier_included(tool.get("tier", "optional"), args.tier)
    ]
    results = [evaluate_tool(tool, args) for tool in selected_tools]

    summary: dict[str, int] = {}
    for result in results:
        summary[result["status"]] = summary.get(result["status"], 0) + 1

    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "catalog": str(args.catalog),
        "catalog_version": catalog.get("version"),
        "catalog_updated": catalog.get("updated"),
        "tier": args.tier,
        "remote_checked": args.check_remote,
        "tools": results,
        "summary": summary,
        "policy": catalog.get("policy", {}),
    }


def print_human(report: dict[str, Any]) -> None:
    print("PM Copilot external integration preflight")
    print(f"catalog: {report['catalog']}")
    print(f"tier: {report['tier']} remote_checked={report['remote_checked']}")
    for item in report["tools"]:
        missing = ""
        if item["missing_credentials"]:
            missing += f" missing_credentials={','.join(item['missing_credentials'])}"
        if item["missing_commands"]:
            missing += f" missing_commands={','.join(item['missing_commands'])}"
        print(
            f"- {item['id']}: {item['status']} "
            f"cost={item['cost_risk']} source={item['source_type']} "
            f"permission={item['permission_boundary']}{missing}"
        )
        if item["limitations"]:
            print(f"  limitations: {'; '.join(item['limitations'])}")
        print(f"  fallback: {item['fallback']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument(
        "--tier",
        choices=["core", "recommended", "optional", "all"],
        default="recommended",
        help="Include tools up to this tier. 'recommended' includes core and recommended.",
    )
    parser.add_argument("--check-remote", action="store_true", help="Probe source URLs with HEAD/GET.")
    parser.add_argument("--timeout", type=float, default=4.0)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--json", action="store_true", help="Print JSON only.")
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="Exit non-zero if any selected integration is unavailable or setup-required.",
    )
    args = parser.parse_args()

    report = build_report(args)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)

    if args.require_ready:
        failing = [item for item in report["tools"] if item["status"] in BLOCKING_STATUSES]
        if failing:
            for item in failing:
                print(f"FAIL: integration {item['id']} is {item['status']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
