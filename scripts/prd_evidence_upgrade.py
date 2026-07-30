#!/usr/bin/env python3
"""Evidence-gated upgrades for historical PM Copilot PRDs.

The upgrader never invents product facts. It records source-backed candidates in
``tool-results/prd-evidence-ledger.json`` and writes only high-confidence
localization copy, tracking events, and same-run visual assets.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
MEDIA_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".mov", ".mp4", ".webm"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
RUNTIME_ASSET_NAMES = {"mermaid.min.js"}
ACTION_RE = re.compile(r"(点击|选择|提交|确认|保存|创建|启用|取消|删除|上传|下载|分享|重试|展开|收起|调整|管理|打开|关闭|恢复|设置|编辑|连接|添加|切换|刷新|发起)")
RESULT_RE = re.compile(r"(成功|完成|结果|失败|部分完成)")
VALUE_RE = re.compile(r"(浏览|瀑布流|阅读|时长|曝光|滚动|停留)")
SECTION_RE = re.compile(r"(?m)^##\s+([一二三四五六七])、([^\n]+)\s*$")
DETAIL_RE = re.compile(r"(?m)^###\s+(5\.\d+)\s+([^\n]+)\s*$")
FEATURE_TERMS = (
    ("登录", "login"), ("项目", "project"), ("画布", "canvas"), ("团队", "team"),
    ("模型", "model"), ("图像", "image"), ("图片", "image"), ("视频", "video"),
    ("节点", "node"), ("资产", "asset"), ("回收站", "trash"), ("菜单", "menu"),
    ("快捷键", "shortcut"), ("权限", "permission"), ("成员", "member"), ("续费", "renewal"),
    ("角色", "role"), ("连接", "connection"), ("连入", "connection"), ("首页", "home"),
    ("Flow Agent", "flow_agent"), ("助手", "assistant"), ("支付", "payment"), ("订单", "order"),
    ("多媒体", "multimedia"), ("文件", "file"), ("任务", "task"),
    ("Seedream", "seedream"), ("Seedance", "seedance"), ("微信", "wechat"),
)
FEATURE_QUALIFIERS = (
    ("批量", "bulk"), ("变更", "change"), ("预览", "preview"), ("恢复", "recovery"),
    ("状态", "status"), ("费用", "fee"), ("设置", "settings"), ("提醒", "reminder"),
    ("失败", "failure"), ("处理", "handling"), ("可用", "availability"), ("授权", "authorization"),
    ("撤销", "revocation"), ("拒绝", "rejection"), ("记录", "record"), ("浏览", "browse"),
    ("搜索", "search"), ("筛选", "filter"), ("整理", "organize"), ("复用", "reuse"),
    ("名称", "name"), ("输入", "input"), ("运行", "runtime"), ("素材", "media"),
    ("发现", "discovery"), ("引导", "guidance"), ("像素", "pixels"), ("分组", "group"),
    ("历史", "history"), ("不可用", "unavailable"), ("单图", "single"), ("购买", "purchase"),
    ("创作", "creation"), ("完成", "completion"), ("参考图", "reference"),
    ("登录方式", "mode"), ("二维码", "qrcode"), ("4K", "4k"),
)
ACTION_SUFFIXES = {
    "点击": ("click", "点击"), "选择": ("select", "选择"), "提交": ("submit", "提交"),
    "确认": ("confirm", "确认"), "保存": ("save", "保存"), "创建": ("create", "创建"),
    "启用": ("enable", "启用"), "取消": ("cancel", "取消"), "删除": ("delete", "删除"),
    "上传": ("upload", "上传"), "下载": ("download", "下载"), "分享": ("share", "分享"),
    "重试": ("retry", "重试"), "展开": ("expand", "展开"), "调整": ("adjust", "调整"),
    "管理": ("manage", "管理"), "打开": ("open", "打开"), "关闭": ("close", "关闭"),
    "恢复": ("restore", "恢复"), "设置": ("set", "设置"), "编辑": ("edit", "编辑"),
    "连接": ("connect", "连接"), "添加": ("add", "添加"), "收起": ("collapse", "收起"),
    "切换": ("switch", "切换"), "刷新": ("refresh", "刷新"), "发起": ("start", "发起"),
}


@dataclass
class Evidence:
    id: str
    kind: str
    source: str
    excerpt: str
    confidence: str
    sha256: str


@dataclass
class OutputReport:
    output: str
    status: str
    language: str = ""
    evidence_count: int = 0
    localization: str = "omitted"
    tracking: str = "omitted"
    figures: int = 0
    limitations: list[str] = field(default_factory=list)
    changed: bool = False
    rendered: bool = False
    validation: str = "not_run"
    error: str = ""


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def strip_markup(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "；", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value).strip(" -;；。")
    return value.replace("|", "／")


def output_language(folder: Path, prd: str) -> str:
    inferred = "zh" if any(item in prd for item in ("文档说明", "需求背景", "需求详情")) else "en"
    run_log = folder / "run-log.yaml"
    if run_log.is_file():
        match = re.search(r"(?m)^language:\s*[\"']?([^\s\"']+)", read(run_log))
        if match and not (inferred == "zh" and match.group(1).lower() != "zh"):
            return match.group(1).lower()
    return inferred


def add_evidence(records: list[Evidence], kind: str, source: Path, excerpt: str, confidence: str) -> str:
    identifier = f"E{len(records) + 1:03d}"
    records.append(Evidence(identifier, kind, str(source), excerpt[:500], confidence, digest(excerpt)))
    return identifier


def prototype_copy(folder: Path, language: str, records: list[Evidence]) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    for prototype in sorted(folder.glob("prototype-*.html")):
        text = read(prototype)
        text = re.sub(r"<(script|style)\b.*?</\1>", " ", text, flags=re.IGNORECASE | re.DOTALL)
        visible = [strip_markup(item) for item in re.findall(r">([^<>]{2,100})<", text)]
        for item in visible:
            if len(item) < 3 or item.lower() in {"notes", "back", "active"}:
                continue
            if language == "zh" and not re.search(r"[\u4e00-\u9fff]", item):
                continue
            evidence_id = add_evidence(records, "visible_copy", prototype, item, "high")
            candidates.append((item, evidence_id))
    return unique_pairs(candidates)[:12]


def quoted_copy(prd: str, language: str, source: Path, records: list[Evidence]) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    for value in re.findall(r"[“\"']([^”\"']{2,80})[”\"']", prd):
        value = strip_markup(value)
        if language == "zh" and not re.search(r"[\u4e00-\u9fff]", value):
            continue
        if value:
            candidates.append((value, add_evidence(records, "quoted_copy", source, value, "medium")))
    return unique_pairs(candidates)[:12]


def unique_pairs(values: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: set[str] = set()
    result: list[tuple[str, str]] = []
    for value, evidence_id in values:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            result.append((value, evidence_id))
    return result


def parse_table_field(section: str, field: str) -> str:
    match = re.search(rf"(?m)^\|\s*{re.escape(field)}\s*\|\s*(.*?)\s*\|\s*$", section)
    return strip_markup(match.group(1)) if match else ""


def requirement_details(prd: str, source: Path, records: list[Evidence]) -> list[dict[str, str]]:
    matches = list(DETAIL_RE.finditer(prd))
    details: list[dict[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(prd)
        body = prd[match.end() : end]
        title = strip_markup(match.group(2))
        entry = parse_table_field(body, "需求入口")
        description = parse_table_field(body, "需求详情")
        details.append({
            "number": match.group(1),
            "title": title,
            "entry": entry,
            "description": description,
            "evidence_id": add_evidence(records, "requirement_detail", source, f"{match.group(1)} {title}\n{body[:700]}", "high"),
            "body": body,
        })
    return details


def duplicate_requirement_numbers(prd: str, details: list[dict[str, str]]) -> list[str]:
    """Return duplicate user-visible requirement identifiers before an automatic upgrade mutates content."""
    duplicates: set[str] = set()
    list_match = re.search(r"(?ms)^##\s+四、需求清单\s*$\n(?P<body>.*?)(?=^##\s+|\Z)", prd)
    if list_match:
        list_numbers = re.findall(r"^\|\s*(\d+\.\d+)\s*\|", list_match.group("body"), re.MULTILINE)
        duplicates.update(number for number in list_numbers if list_numbers.count(number) > 1)
    detail_numbers = [detail["number"] for detail in details]
    duplicates.update(number for number in detail_numbers if detail_numbers.count(number) > 1)
    return sorted(duplicates)


def tracking_rows_from_csv(path: Path, records: list[Evidence]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            name = strip_markup(row.get("description") or row.get("名称") or row.get("event_name") or "")
            identifier = strip_markup(row.get("event_name") or row.get("标识") or "")
            trigger = strip_markup(row.get("trigger") or row.get("时机") or "")
            if not name or not identifier or not trigger:
                continue
            properties = strip_markup(row.get("required_properties") or row.get("附加参数") or row.get("参数") or "") or "/"
            evidence_id = add_evidence(records, "tracking_plan", path, json.dumps(row, ensure_ascii=False), "high")
            name = normalized_event_label(name)
            event_id = canonical_event_identifier(identifier, name, trigger)
            rows.append({"name": name, "id": event_id, "timing": compact_timing(trigger, event_id, name), "parameters": properties, "note": "来源于既有埋点方案。", "evidence_id": evidence_id})
    return rows


def semantic_feature(value: str, fallback: str = "") -> str:
    words: list[str] = []
    for term, word in FEATURE_TERMS:
        if term in value and word not in words:
            words.append(word)
    qualifiers = [word for term, word in FEATURE_QUALIFIERS if term in value and word not in words]
    fallback_words = [word for word in fallback.split("_") if word]
    if words:
        return "_".join((words + qualifiers)[:4])
    if fallback_words:
        return "_".join((fallback_words[:2] + qualifiers)[:4])
    return "_".join(qualifiers[:2]) or "journey"


def tracking_context_feature(event_names: Iterable[str]) -> str:
    combined = " ".join(event_names)
    words = [word for term, word in FEATURE_TERMS if term in combined]
    return "_".join(list(dict.fromkeys(words))[:2])


def action_for(value: str) -> tuple[str, str]:
    match = ACTION_RE.search(value)
    if match and match.group(1) in ACTION_SUFFIXES:
        return ACTION_SUFFIXES[match.group(1)]
    return "action", "操作"


def semantic_event_identifier(name: str, timing: str, default_action: str = "", fallback_feature: str = "") -> str:
    feature = semantic_feature(name, fallback_feature)
    if name.endswith(("结果展示", "结果可见")) or "结果" in timing or "成功" in timing or "失败" in timing:
        action = default_action or action_for(name)[0]
        suffix = f"{action}_result" if action != "action" else "result_display"
    elif "首屏" in timing or name.startswith(("访问", "查看", "进入")):
        suffix = "view"
    elif "浏览" in name or "时长" in name:
        suffix = "engagement"
    else:
        suffix = default_action or action_for(name)[0]
    return f"{feature}_{suffix}"


def normalized_event_label(value: str) -> str:
    value = value.strip()
    if value.startswith("访问"):
        value = "查看" + value[2:]
    if value.startswith("查看"):
        for action in ACTION_SUFFIXES:
            prefix = "查看" + action
            if value.startswith(prefix):
                value = "查看" + value[len(prefix):]
                break
    for action in ACTION_SUFFIXES:
        doubled = action + action
        if value.startswith(doubled):
            value = action + value[len(doubled):]
    if value.endswith("结果可见"):
        value = value[:-4] + "结果展示"
    return value


def canonical_event_identifier(identifier: str, event_name: str, timing: str, fallback_feature: str = "") -> str:
    identifier = normalize_tracking_identifier(identifier)
    action_id, _ = action_for(event_name)
    feature = semantic_feature(event_name)
    if identifier.startswith("prd_") or identifier.startswith("journey_") or identifier in {"event", "feature", "journey"}:
        return semantic_event_identifier(event_name, timing, action_id, fallback_feature)
    if identifier.endswith("_viewed"):
        return f"{feature}_view"
    if identifier.endswith("_created"):
        return f"{feature}_create_result"
    if "_action_result" in identifier:
        return f"{feature}_{action_id}_result"
    if identifier.endswith("_action"):
        return f"{feature}_{action_id}"
    return identifier


def compact_timing(value: str, identifier: str = "", event_name: str = "") -> str:
    if "首屏展示" in value:
        return "页面完成首屏展示时"
    if "离开" in value or "浏览达到" in value or "浏览时长" in value:
        return "用户离开页面或达到有效浏览阈值时"
    if "结果" in value or "成功" in value or "失败" in value:
        return "操作结果展示时"
    suffix = identifier.rsplit("_", 1)[-1]
    action = next((label for event_id, label in ACTION_SUFFIXES.values() if event_id == suffix), "")
    if action:
        target = normalized_event_label(event_name)
        if target.startswith(action):
            target = target[len(action):]
        return f"用户{action}{target}时"
    return value.strip() or "用户完成对应操作时"


def tracking_rows_from_details(details: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    context_feature = tracking_context_feature(detail["title"] for detail in details)
    for detail in details:
        number, title, entry, description = (detail[key] for key in ("number", "title", "entry", "description"))
        feature = semantic_feature(title, context_feature)
        if entry:
            rows.append({
                "name": f"查看{title}", "id": f"{feature}_view", "timing": "页面完成首屏展示时",
                "parameters": "/", "note": "/", "evidence_id": detail["evidence_id"],
            })
        action = ACTION_RE.search(description)
        if action:
            action_id, action_label = ACTION_SUFFIXES.get(action.group(1), ("action", action.group(1)))
            rows.append({
                "name": f"{action_label}{title}", "id": f"{feature}_{action_id}", "timing": f"用户{action_label}{title}时",
                "parameters": "/", "note": "/", "evidence_id": detail["evidence_id"],
            })
        if RESULT_RE.search(description):
            action_id, _ = action_for(description)
            rows.append({
                "name": f"{title}结果展示", "id": f"{feature}_{action_id}_result", "timing": "操作结果展示时",
                "parameters": "/", "note": "/", "evidence_id": detail["evidence_id"],
            })
        if VALUE_RE.search(description):
            rows.append({
                "name": f"{title}有效浏览", "id": f"{feature}_engagement", "timing": "用户离开页面或达到有效浏览阈值时",
                "parameters": "浏览时长、浏览深度", "note": "/", "evidence_id": detail["evidence_id"],
            })
    unique: dict[str, dict[str, str]] = {}
    for row in rows:
        unique.setdefault(row["id"], row)
    return list(unique.values())


def asset_tokens(value: str) -> set[str]:
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", " ", value.lower())
    tokens = set(re.findall(r"[a-z0-9]{2,}|[\u4e00-\u9fff]{2,}", normalized))
    for run in re.findall(r"[\u4e00-\u9fff]{3,}", normalized):
        tokens.update(run[index : index + 2] for index in range(len(run) - 1))
    return tokens


def real_assets(folder: Path, records: list[Evidence]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    assets = folder / "assets"
    if not assets.is_dir():
        return result
    for path in sorted(assets.rglob("*")):
        if not path.is_file() or path.name in RUNTIME_ASSET_NAMES or path.suffix.lower() not in MEDIA_SUFFIXES:
            continue
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        evidence_id = add_evidence(records, "same_run_visual_asset", path, path.name, "high")
        result.append({"path": f"./assets/{path.relative_to(assets).as_posix()}", "name": path.name, "tokens": " ".join(asset_tokens(path.stem)), "evidence_id": evidence_id})
    return result


def best_asset(detail: dict[str, str], assets: list[dict[str, str]], used: set[str]) -> dict[str, str] | None:
    keywords = asset_tokens(" ".join((detail["title"], detail["entry"], detail["description"])))
    ranked: list[tuple[int, dict[str, str]]] = []
    for asset in assets:
        if asset["path"] in used:
            continue
        score = len(keywords & set(asset["tokens"].split()))
        if score >= 2:
            ranked.append((score, asset))
    return max(ranked, key=lambda item: item[0])[1] if ranked else None


def remove_migrator_figure_rows(prd: str) -> str:
    """Remove only rows emitted by an earlier migrator before reinserting safely."""
    return re.sub(
        r"(?m)^\|\s*(?:图示|截图)\s*\|\s*!\[[^\]]*\]\([^\n]*\)<br><small>位置：[^\n]*</small>\s*\|\s*\n?",
        "",
        prd,
    )


def insert_figure_rows(prd: str, details: list[dict[str, str]], assets: list[dict[str, str]]) -> tuple[str, list[str]]:
    selected: list[str] = []
    used: set[str] = set()
    detail_by_number = {item["number"]: item for item in details}
    matches = list(DETAIL_RE.finditer(prd))
    if not matches:
        return prd, selected
    parts: list[str] = []
    cursor = 0
    for index, match in enumerate(matches):
        next_detail = matches[index + 1].start() if index + 1 < len(matches) else len(prd)
        next_section = re.search(r"(?m)^##\s+", prd[match.end() :])
        next_h2 = match.end() + next_section.start() if next_section else len(prd)
        end = min(next_detail, next_h2)
        section = prd[match.start() : end]
        detail = detail_by_number.get(match.group(1))
        if detail and "| 图示 |" not in section and "| 截图 |" not in section:
            asset = best_asset(detail, assets, used)
            table_match = re.search(
                r"(?m)(^\|\s*维度\s*\|\s*(?:内容|需求说明)\s*\|\s*\n(?:^\|[^\n]*(?:\n|$))*)",
                section,
            )
            if asset and table_match:
                caption = Path(asset["name"]).stem
                row = f"| 图示 | ![{Path(asset['name']).stem}]({asset['path']})<small>{caption}</small> |\n"
                table = table_match.group(1)
                if table.endswith("\n"):
                    replacement = table + row
                else:
                    replacement = table + "\n" + row
                section = section[:table_match.start()] + replacement + section[table_match.end():]
                used.add(asset["path"])
                selected.append(asset["evidence_id"])
        parts.append(prd[cursor : match.start()])
        parts.append(section)
        cursor = end
    parts.append(prd[cursor:])
    return "".join(parts), selected


def section_present(prd: str, title: str) -> bool:
    return bool(re.search(rf"(?m)^##\s+[六七]、{re.escape(title)}\s*$", prd))


def remove_unsupported_chinese_localization(prd: str, language: str) -> tuple[str, bool]:
    """Omit English-only legacy copy from a Chinese PRD without inventing translation."""
    if language != "zh":
        return prd, False
    heading = re.search(r"(?m)^##\s+六、多语言需求\s*$", prd)
    if not heading:
        return prd, False
    next_heading = re.search(r"(?m)^##\s+", prd[heading.end() :])
    end = heading.end() + next_heading.start() if next_heading else len(prd)
    section = prd[heading.end() : end]
    if re.search(r"[\u4e00-\u9fff]", section) or re.search(r"(?i)双语|bilingual", section):
        return prd, False
    return prd[: heading.start()].rstrip() + "\n\n" + prd[end:].lstrip(), True


def normalize_optional_section_order(prd: str) -> str:
    """Keep localization immediately before tracking regardless of a legacy tracking numeral."""
    localization_heading = re.search(r"(?m)^##\s+六、多语言需求\s*$", prd)
    tracking_heading = re.search(r"(?m)^##\s+(?:六|七)、埋点需求\s*$", prd)
    if not localization_heading or not tracking_heading or localization_heading.start() < tracking_heading.start():
        return prd
    next_heading = re.search(r"(?m)^##\s+", prd[localization_heading.end() :])
    localization_end = localization_heading.end() + next_heading.start() if next_heading else len(prd)
    localization = prd[localization_heading.start() : localization_end].strip()
    without_localization = prd[: localization_heading.start()].rstrip() + "\n\n" + prd[localization_end:].lstrip()
    tracking_heading = re.search(r"(?m)^##\s+(?:六|七)、埋点需求\s*$", without_localization)
    if not tracking_heading:
        return prd
    return (
        without_localization[: tracking_heading.start()].rstrip()
        + "\n\n"
        + localization
        + "\n\n"
        + without_localization[tracking_heading.start() :].lstrip()
    )


def normalize_tracking_identifier(value: str) -> str:
    """Convert an existing identifier to the PRD contract's stable form only."""
    value = value.strip().strip("`")
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value)
    value = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_").lower()
    if not value:
        return "event"
    if not value[0].isalpha() or not value[0].isascii():
        value = f"event_{value}"
    return value


def normalize_existing_tracking_rows(prd: str) -> str:
    """Migrate legacy tracking labels and generated IDs to the current PRD standard."""
    heading = re.search(r"(?m)^##\s+(?:六|七)、埋点需求\s*$", prd)
    if not heading:
        return prd
    next_heading = re.search(r"(?m)^##\s+", prd[heading.end() :])
    end = heading.end() + next_heading.start() if next_heading else len(prd)
    section = prd[heading.start() : end]
    event_names = [
        values[0]
        for line in section.splitlines()
        if line.strip().startswith("|")
        for values in [[item.strip() for item in line.strip().strip("|").split("|")]]
        if len(values) == 5 and values[0] not in {"事件", "名称", "---"}
    ]
    context_feature = tracking_context_feature(event_names)
    lines: list[str] = []
    used_identifiers: set[str] = set()
    for line in section.splitlines(keepends=True):
        values = [item.strip() for item in line.strip().strip("|").split("|")]
        if values == ["名称", "标识", "时机", "参数", "备注"]:
            suffix = "\n" if line.endswith("\n") else ""
            line = "| 事件 | 事件名称 | 上报时机 | 附加参数 | 备注 |" + suffix
        elif len(values) == 5 and values[0] not in {"事件", "名称", "---"}:
            name, identifier, timing, parameters, note = values
            name = normalized_event_label(name)
            normalized_identifier = canonical_event_identifier(identifier, name, timing, context_feature)
            generated_identifier = semantic_event_identifier(name, timing, action_for(name)[0], context_feature)
            if note in {"", "/"} and generated_identifier != "journey_action":
                normalized_identifier = generated_identifier
            if normalized_identifier in used_identifiers:
                feature = semantic_feature(name, context_feature)
                action = action_for(name)[0]
                normalized_identifier = f"{feature}_{action}"
                suffix = 2
                while normalized_identifier in used_identifiers:
                    normalized_identifier = f"{feature}_{action}_{suffix}"
                    suffix += 1
            used_identifiers.add(normalized_identifier)
            values[0] = name
            values[1] = normalized_identifier
            values[2] = compact_timing(timing, normalized_identifier, name)
            values[3] = parameters or "/"
            values[4] = "/" if not note or "拟议" in note else note
            suffix = "\n" if line.endswith("\n") else ""
            line = "| " + " | ".join(values) + " |" + suffix
        lines.append(line)
    canonical_heading = "七、埋点需求" if section_present(prd, "多语言需求") else "六、埋点需求"
    normalized_section = re.sub(
        r"(?m)^##\s+(?:六|七)、埋点需求\s*$",
        f"## {canonical_heading}",
        "".join(lines),
        count=1,
    )
    return prd[: heading.start()] + normalized_section + prd[end:]


def copy_usage(copy: str, details: list[dict[str, str]]) -> str:
    for detail in details:
        if copy in detail["body"]:
            return f"{detail['number']} {detail['title']}"
    return "相关需求"


def copy_parameters(copy: str) -> str:
    parameters = re.findall(r"\{([A-Za-z][A-Za-z0-9_]*)\}", copy)
    return "、".join(f"{{{item}}}" for item in parameters) or "/"


def normalize_localization_section(prd: str, details: list[dict[str, str]]) -> str:
    heading = re.search(r"(?m)^##\s+六、多语言需求\s*$", prd)
    if not heading:
        return prd
    next_heading = re.search(r"(?m)^##\s+", prd[heading.end() :])
    end = heading.end() + next_heading.start() if next_heading else len(prd)
    section = prd[heading.end() : end]
    blocks = re.findall(r"```(?:text|plain|txt)?\s*\n(.+?)\n```", section, re.DOTALL | re.IGNORECASE)
    copies = [line.strip() for block in blocks for line in block.splitlines() if line.strip()]
    if not copies:
        for line in section.splitlines():
            if not line.strip().startswith("|") or re.match(r"^\|\s*:?-{3,}", line):
                continue
            values = [value.strip() for value in line.strip().strip("|").split("|")]
            if values and values[0] not in {"文案", "---"}:
                copies.append(values[0])
    copies = list(dict.fromkeys(copies))
    if not copies:
        return prd
    canonical = "\n".join([
        "## 六、多语言需求", "", "```text", *copies, "```", "",
        "| 文案 | 使用位置 | 参数 |", "| --- | --- | --- |",
        *[f"| {copy} | {copy_usage(copy, details)} | {copy_parameters(copy)} |" for copy in copies],
    ])
    return prd[: heading.start()].rstrip() + "\n\n" + canonical + "\n\n" + prd[end:].lstrip()


def append_optional_sections(prd: str, copies: list[tuple[str, str]], tracking: list[dict[str, str]], language: str, details: list[dict[str, str]]) -> tuple[str, str, str]:
    prd, localization_removed = remove_unsupported_chinese_localization(prd, language)
    prd = normalize_optional_section_order(prd)
    localization = "already_present" if section_present(prd, "多语言需求") else "omitted"
    tracking_status = "already_present" if section_present(prd, "埋点需求") else "omitted"
    localization_block = ""
    tracking_block = ""
    if copies and localization == "omitted":
        copy_lines = [item[0] for item in copies]
        localization_block = "\n".join([
            "## 六、多语言需求", "", "```text", *copy_lines, "```", "",
            "| 文案 | 使用位置 | 参数 |", "| --- | --- | --- |",
            *[f"| {copy} | {copy_usage(copy, details)} | {copy_parameters(copy)} |" for copy in copy_lines],
        ])
        localization = "added"
    if tracking and tracking_status == "omitted":
        tracking_heading = "七、埋点需求" if localization != "omitted" or localization_block else "六、埋点需求"
        tracking_lines = [f"## {tracking_heading}", "", "| 事件 | 事件名称 | 上报时机 | 附加参数 | 备注 |", "| --- | --- | --- | --- | --- |"]
        tracking_lines.extend(
            f"| {row['name']} | {row['id']} | {row['timing']} | {row['parameters']} | {row['note']} |"
            for row in tracking
        )
        tracking_block = "\n".join(tracking_lines)
        tracking_status = "added"
    if localization_block:
        tracking_heading = re.search(r"(?m)^##\s+(?:六|七)、埋点需求\s*$", prd)
        if tracking_heading:
            prd = (
                prd[: tracking_heading.start()].rstrip()
                + "\n\n"
                + localization_block
                + "\n\n"
                + prd[tracking_heading.start() :].lstrip()
            )
        else:
            prd = prd.rstrip() + "\n\n" + localization_block + "\n"
    if tracking_block:
        prd = prd.rstrip() + "\n\n" + tracking_block + "\n"
    if localization_removed and localization == "omitted":
        localization = "removed_unsupported"
    prd = normalize_localization_section(prd, details)
    return normalize_existing_tracking_rows(prd), localization, tracking_status


def run_command(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def source_backed_preservation_gaps(folder: Path, prd: str) -> list[str]:
    """Return source-backed history that must be restored before automated mutation."""
    run_log_path = folder / "run-log.yaml"
    if not run_log_path.is_file():
        return []
    run_log = read(run_log_path)
    source_requirement_ids = set(re.findall(r"\bR\d+\b", run_log))
    detail_count = len(DETAIL_RE.findall(prd))
    gaps: list[str] = []
    if source_requirement_ids and detail_count < len(source_requirement_ids):
        gaps.append(
            "Source-backed requirement scope must be restored before automated upgrade "
            f"({detail_count} detail sections for {len(source_requirement_ids)} requirements)."
        )
    source_versions = [
        tuple(int(part) for part in value.split("."))
        for value in re.findall(r"(?i)(?:PRD\s+v|prd\.md[^\n]{0,100}?\bv)(\d+\.\d+)", run_log)
    ]
    document_versions = [
        tuple(int(part) for part in value.split("."))
        for value in re.findall(r"(?m)^\|\s*v(\d+\.\d+)\s*\|", prd)
    ]
    if source_versions and (not document_versions or max(document_versions) < max(source_versions)):
        gaps.append("Source-backed requirement-version history must be restored before automated upgrade.")
    return gaps


def upgrade_output(folder: Path, renderer_root: Path, apply: bool, validate: bool) -> OutputReport:
    prd_path = folder / "prd.md"
    report = OutputReport(output=str(folder), status="skipped")
    if not prd_path.is_file():
        report.limitations.append("No prd.md; content upgrade is not applicable.")
        return report
    prd = read(prd_path)
    report.language = output_language(folder, prd)
    preservation_gaps = source_backed_preservation_gaps(folder, prd)
    if preservation_gaps:
        report.status = "blocked"
        report.limitations.extend(preservation_gaps)
        if apply:
            tool_results = folder / "tool-results"
            tool_results.mkdir(exist_ok=True)
            payload = {
                "schema_version": "1.0",
                "output": str(folder),
                "language": report.language,
                "evidence": [],
                "selected_asset_evidence_ids": [],
                "localization_evidence_ids": [],
                "tracking_evidence_ids": [],
                "report": asdict(report),
            }
            (tool_results / "prd-evidence-ledger.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (tool_results / "prd-upgrade-report.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        return report
    records: list[Evidence] = []
    details = requirement_details(prd, prd_path, records)
    duplicate_numbers = duplicate_requirement_numbers(prd, details)
    if duplicate_numbers:
        report.status = "blocked"
        report.limitations.append(
            "Duplicate requirement number(s) must be resolved before automated upgrade: "
            + ", ".join(duplicate_numbers)
        )
        return report
    copies = prototype_copy(folder, report.language, records) + quoted_copy(prd, report.language, prd_path, records)
    copies = unique_pairs(copies)[:12]
    tracking_source = next(iter(sorted(folder.glob("tracking-plan.csv"))), None)
    tracking = tracking_rows_from_csv(tracking_source, records) if tracking_source else tracking_rows_from_details(details)
    assets = real_assets(folder, records)
    upgraded, selected_assets = insert_figure_rows(prd, details, assets)
    upgraded, report.localization, report.tracking = append_optional_sections(upgraded, copies, tracking, report.language, details)
    report.figures = len(selected_assets)
    report.evidence_count = len(records)
    if not copies:
        report.limitations.append("No source-backed user-visible copy was found; localization section was omitted.")
    if not tracking:
        report.limitations.append("No measurable user journey evidence was found; tracking section was omitted.")
    if assets and not selected_assets:
        report.limitations.append("Same-run visual assets were found but none met the semantic match threshold; no figure was inserted.")
    if not assets:
        report.limitations.append("No same-run real visual asset was found; no figure was inserted.")
    report.changed = upgraded != prd
    payload = {
        "schema_version": "1.0",
        "output": str(folder),
        "language": report.language,
        "evidence": [asdict(item) for item in records],
        "selected_asset_evidence_ids": selected_assets,
        "localization_evidence_ids": [item[1] for item in copies],
        "tracking_evidence_ids": [item["evidence_id"] for item in tracking],
        "report": asdict(report),
    }
    if not apply:
        report.status = "planned" if report.changed else "no_change"
        return report
    tool_results = folder / "tool-results"
    tool_results.mkdir(exist_ok=True)
    (tool_results / "prd-evidence-ledger.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if report.changed:
        temporary = prd_path.with_suffix(".md.tmp")
        temporary.write_text(upgraded, encoding="utf-8")
        temporary.replace(prd_path)
    rendered = run_command([sys.executable, str(renderer_root / "scripts" / "render_prd_html.py"), str(folder)], renderer_root)
    if rendered.returncode:
        report.status = "failed"
        report.error = rendered.stdout.strip()
    else:
        report.rendered = True
        report.status = "upgraded" if report.changed else "no_change"
    if validate and report.status != "failed":
        command = [
            sys.executable,
            str(renderer_root / "scripts" / "validate_outputs.py"),
            str(folder),
            "--historical-prd-upgrade",
        ]
        if report.language == "zh":
            command.extend(["--language", "zh"])
        validation = run_command(command, renderer_root)
        report.validation = "passed" if validation.returncode == 0 else "failed"
        if validation.returncode:
            report.limitations.append("Full output validation remains blocked by historical trace or artifact debt.")
    payload["report"] = asdict(report)
    (tool_results / "prd-upgrade-report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def discover_output_folders(roots: Iterable[Path]) -> list[Path]:
    discovered: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        direct = root / "outputs"
        if direct.is_dir():
            discovered.update(item for item in direct.iterdir() if item.is_dir())
        for output_root in root.rglob("outputs"):
            if output_root.is_dir() and output_root.parent.name == "pm-copilot":
                discovered.update(item for item in output_root.iterdir() if item.is_dir())
    return sorted(discovered)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roots", type=Path, nargs="+", default=[ROOT])
    parser.add_argument("--renderer-root", type=Path, default=ROOT)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--no-validate", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    reports = [upgrade_output(folder, args.renderer_root.resolve(), args.apply, not args.no_validate) for folder in discover_output_folders(args.roots)]
    payload = [asdict(report) for report in reports]
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for report in reports:
            print(f"{report.status}: {report.output}; localization={report.localization}; tracking={report.tracking}; figures={report.figures}")
    return 1 if any(report.status == "failed" for report in reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
