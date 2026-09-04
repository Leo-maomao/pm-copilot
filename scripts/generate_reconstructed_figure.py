#!/usr/bin/env python3
"""Build and capture an isolated frontend figure for one PRD state.

The script deliberately writes only below ``--run-folder``.  It uses the
repository's browser capture path when available; a capture failure is a normal
result for the caller, which retains a controlled PRD placeholder instead of
pretending that an image was generated.
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-folder", type=Path, required=True)
    parser.add_argument("--asset-name", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--state", required=True)
    args = parser.parse_args()

    folder = args.run_folder.resolve()
    asset_name = Path(args.asset_name).name
    if asset_name != args.asset_name or Path(asset_name).suffix.lower() != ".png":
        raise SystemExit("--asset-name must be a PNG filename")
    reconstruction = folder / "reconstructions" / f"{Path(asset_name).stem}.html"
    reconstruction.parent.mkdir(parents=True, exist_ok=True)
    title = html.escape(args.title)
    state = html.escape(args.state)
    reconstruction.write_text(
        f"""<!doctype html><html lang=\"zh-CN\"><meta charset=\"utf-8\">
<title>{title}</title><style>
body{{margin:0;background:#f4f6f8;color:#172033;font:16px -apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif}}
main{{width:960px;max-width:calc(100vw - 48px);margin:40px auto;background:#fff;border:1px solid #d8dee8;padding:32px;box-sizing:border-box}}
header{{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #e5e9ef;padding-bottom:20px}}
h1{{font-size:24px;margin:0}} .tag{{color:#0b6b4f;background:#e6f5ed;padding:6px 10px}}
section{{margin-top:28px;border:1px solid #d8dee8;padding:24px}} h2{{font-size:18px;margin:0 0 18px}}
.row{{display:flex;gap:18px;align-items:center}} .icon{{width:44px;height:44px;background:#1f5b99}} .copy{{line-height:1.7}}
button{{margin-top:20px;background:#1f5b99;border:0;color:white;padding:10px 16px;font:inherit}}
</style><main><header><h1>{title}</h1><span class=\"tag\">还原图示</span></header>
<section><h2>{state}</h2><div class=\"row\"><div class=\"icon\"></div><div class=\"copy\">此页面根据已确认的功能逻辑还原，用于核对用户可见状态、入口和反馈。</div></div><button>确认</button></section></main></html>\n""",
        encoding="utf-8",
    )
    report = folder / "tool-results" / "reconstructed-figures" / f"{Path(asset_name).stem}.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    screenshot = folder / "reconstructions" / f"{Path(asset_name).stem}.png"
    command = [
        sys.executable, str(Path(__file__).with_name("capture_frontend_figure.py")),
        str(reconstruction), "--output", str(screenshot),
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    destination = folder / "assets" / asset_name
    payload = {
        "mode": "reconstructed_figure",
        "reconstruction_path": reconstruction.relative_to(folder).as_posix(),
        "capture_command": command,
        "capture_status": "passed" if result.returncode == 0 and screenshot.is_file() else "failed",
        "stdout": result.stdout[-2000:],
        "stderr": result.stderr[-2000:],
    }
    if payload["capture_status"] == "passed":
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(screenshot, destination)
        payload["asset_path"] = destination.relative_to(folder).as_posix()
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload["capture_status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
