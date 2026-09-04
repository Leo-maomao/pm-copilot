#!/usr/bin/env python3
"""Controller-owned scope contracts for in-place PRD revisions.

The controller keeps global document integrity checks intact, but a revision's
product constraints apply to its selected requirement sections.  This module
turns that boundary into structured evidence so a reviewer cannot reinterpret
"two images in 5.1" as "two images in the entire document".
"""

from __future__ import annotations

import hashlib
from html.parser import HTMLParser
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence


REQUIREMENT_HEADING_RE = re.compile(
    r"(?m)^###\s+(?P<id>\d+\.\d+)\b(?P<title>.*?)\s*$"
)
REQUIREMENT_ROW_RE = re.compile(r"(?m)^\|\s*(?P<id>\d+\.\d+)\s*\|.*(?:\n|$)")
SECTION_HEADING_RE = re.compile(
    r"(?m)^(?P<hashes>#{2,6})[ \t]+(?P<title>.*?)[ \t]*$"
)
SECTION_NUMBER_PREFIX_RE = re.compile(r"^\s*\d+(?:\.\d+)*[.、]?\s*")
VERSION_HISTORY_TITLES = {
    "版本记录",
    "版本历史",
    "version history",
    "version record",
    "version log",
    "revision history",
    "revision log",
    "change history",
    "change log",
}
VERSION_RECORD_ROW_RE = re.compile(
    r"^[ \t]*\|[ \t]*(?:v(?:ersion)?[ \t]*\d+(?:\.\d+)*|\d+\.\d+(?:\.\d+)*)[ \t]*\|",
    re.IGNORECASE,
)
VERSION_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
HTML_IMAGE_RE = re.compile(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", re.IGNORECASE)
DETAIL_MEDIA_RE = re.compile(
    r"\[\[prd-detail-media\s+(?P<attributes>.*?)\]\]", re.IGNORECASE | re.DOTALL
)
DETAIL_MEDIA_SRC_RE = re.compile(
    r"\bsrc\s*=\s*[\"'](?P<value>[^\"']+)[\"']", re.IGNORECASE
)
ASSET_REFERENCE_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])(?:\./)?assets/[\w .()\-\u3400-\u9fff]+?\.(?:png|jpe?g|webp)(?![A-Za-z0-9_.-])",
    re.IGNORECASE,
)
LINKED_COPY_RE = re.compile(r"多语言|文案|\bcopy\b|\bi18n\b|locali[sz]ation", re.IGNORECASE)
FIXED_ORDER_RE = re.compile(r"固定顺序|按顺序|顺序为|顺序.*?(?:成功|失败)|\bfixed\s+order\b|\bin\s+(?:this|the)\s+order\b", re.IGNORECASE)
EXACT_IMAGE_SET_RE = re.compile(
    r"仅(?:保留|引用)?|只(?:保留|引用)?|只能|不(?:引用|生成).{0,24}(?:第?\s*(?:三|3)\s*(?:张)?(?:图|图示|图片)|third\s+(?:image|figure))|"
    r"\b(?:only|exactly|no\s+(?:third|additional)\s+(?:image|figure))\b",
    re.IGNORECASE,
)


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def normalize_image_reference(value: str) -> str:
    """Normalize local paths without converting a relative reference to an absolute one."""
    clean = value.strip().split("#", 1)[0].split("?", 1)[0].replace("\\", "/")
    return clean[2:] if clean.startswith("./") else clean


def markdown_image_refs(text: str) -> list[str]:
    refs: list[str] = []
    refs.extend(match.group(1) for match in MARKDOWN_IMAGE_RE.finditer(text))
    refs.extend(match.group(1) for match in HTML_IMAGE_RE.finditer(text))
    for match in DETAIL_MEDIA_RE.finditer(text):
        source = DETAIL_MEDIA_SRC_RE.search(match.group("attributes"))
        if source:
            refs.append(source.group("value"))
    return [normalize_image_reference(reference) for reference in refs if reference.strip()]


def _section_title(value: str) -> str:
    """Normalize a Markdown heading without changing its source bytes."""
    return SECTION_NUMBER_PREFIX_RE.sub("", value).strip().casefold()


def _version_history_section(text: str) -> dict[str, Any] | None:
    """Locate one recognized version-history section in an existing PRD."""
    headings = list(SECTION_HEADING_RE.finditer(text))
    for index, match in enumerate(headings):
        if _section_title(match.group("title")) not in VERSION_HISTORY_TITLES:
            continue
        level = len(match.group("hashes"))
        end = len(text)
        for following in headings[index + 1:]:
            if len(following.group("hashes")) <= level:
                end = following.start()
                break
        return {
            "start": match.start(),
            "body_start": match.end(),
            "end": end,
            "heading": text[match.start():match.end()],
            "body": text[match.end():end],
        }
    return None


def _without_version_history(text: str) -> str:
    """Remove the recognized history block before requirement-row discovery."""
    section = _version_history_section(text)
    if section is None:
        return text
    return text[:int(section["start"])] + text[int(section["end"]):]


def requirement_sections(text: str) -> dict[str, dict[str, Any]]:
    """Return Markdown requirement-detail slices keyed by their stable IDs."""
    matches = list(REQUIREMENT_HEADING_RE.finditer(text))
    sections: dict[str, dict[str, Any]] = {}
    for index, match in enumerate(matches):
        next_start = len(text)
        for following in matches[index + 1:]:
            next_start = following.start()
            break
        # A following H1/H2 ends the current requirement section too.
        boundary = re.search(r"(?m)^#{1,2}\s+", text[match.end():next_start])
        if boundary:
            next_start = match.end() + boundary.start()
        content = text[match.start():next_start]
        requirement_id = match.group("id")
        sections[requirement_id] = {
            "id": requirement_id,
            "title": match.group("title").strip(),
            "content": content,
            "sha256": digest_bytes(content.encode("utf-8")),
            "image_refs": markdown_image_refs(content),
        }
    return sections


def requirement_rows(text: str) -> dict[str, str]:
    """Return requirement-list rows so selected rows can change independently."""
    rows: dict[str, str] = {}
    for match in REQUIREMENT_ROW_RE.finditer(_without_version_history(text)):
        rows[match.group("id")] = match.group(0)
    return rows


def asset_digests(root: Path) -> dict[str, str]:
    """Hash local asset bytes with output-root-relative paths."""
    assets = root / "assets"
    if not assets.is_dir():
        return {}
    return {
        path.relative_to(root).as_posix(): digest_bytes(path.read_bytes())
        for path in sorted(assets.rglob("*"))
        if path.is_file()
    }


def _deduplicate(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def _asset_references(text: str) -> list[str]:
    return _deduplicate(normalize_image_reference(match.group(0)) for match in ASSET_REFERENCE_RE.finditer(text))


def build_revision_scope_manifest(
    *,
    baseline_markdown: str,
    baseline_assets: Mapping[str, str],
    requirement_ids: Sequence[str],
    confirmed_scope_text: str,
    authority: str,
    selectors: Sequence[str] = (),
    allowed_new_assets: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Create the durable controller-owned contract for one in-place revision.

    Explicit image rules are intentionally inferred only where the confirmation
    names local assets. For a single selected requirement, those named assets
    belong to that requirement; multiple selected IDs with one unpartitioned
    image list remain a human/reviewer concern instead of being guessed.
    """
    selected = _deduplicate(str(item).strip() for item in requirement_ids)
    baseline_sections = requirement_sections(baseline_markdown)
    evidence_refs = _asset_references(confirmed_scope_text)
    image_contracts: list[dict[str, Any]] = []
    if len(selected) == 1 and evidence_refs:
        image_contracts.append({
            "requirement_ids": selected,
            "required_image_refs": evidence_refs,
            "exact_count": bool(EXACT_IMAGE_SET_RE.search(confirmed_scope_text)),
            "fixed_order": bool(FIXED_ORDER_RE.search(confirmed_scope_text)),
            "source": "explicit local asset references in confirmed scope",
        })
    return {
        "schema_version": 1,
        "mode": "in_place_revision",
        "requirement_ids": selected,
        "selectors": _deduplicate(str(item).strip() for item in selectors),
        "authority": authority,
        "baseline": {
            "prd_sha256": digest_bytes(baseline_markdown.encode("utf-8")),
            "requirement_sections": {
                requirement_id: {
                    "sha256": str(section["sha256"]),
                    "image_refs": list(section["image_refs"]),
                }
                for requirement_id, section in baseline_sections.items()
            },
            "assets": dict(sorted(baseline_assets.items())),
        },
        "image_contracts": image_contracts,
        "allowed_derivatives": {
            "linked_localization_rows": bool(LINKED_COPY_RE.search(confirmed_scope_text)),
            # The PRD contract requires a material revision to retain an
            # append-only history record. The validator below still freezes
            # existing records and all other document metadata.
            "append_only_version_history": _version_history_section(baseline_markdown) is not None,
            "rendered_html": True,
        },
        "allowed_new_assets": dict(sorted((allowed_new_assets or {}).items())),
    }


def _remove_selected_sections(text: str, selected_ids: set[str]) -> str:
    sections = requirement_sections(text)
    removed = [str(section["content"]) for requirement_id, section in sections.items() if requirement_id in selected_ids]
    for content in removed:
        text = text.replace(content, "", 1)
    return text


def _row_key(row: str) -> str:
    cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
    return re.sub(r"\s+", " ", cells[0]) if cells else ""


def _selected_copy_terms(candidate_sections: Mapping[str, Mapping[str, Any]]) -> set[str]:
    terms: set[str] = set()
    for section in candidate_sections.values():
        plain = re.sub(r"[`*_#|<>]", " ", str(section.get("content", "")))
        for item in re.findall(r"[\u3400-\u9fff]{2,}|[A-Za-z][A-Za-z0-9 _-]{2,}", plain):
            compact = re.sub(r"\s+", " ", item).strip()
            if len(compact) >= 2:
                terms.add(compact)
    return terms


def _linked_copy_key(key: str, copy_terms: set[str]) -> bool:
    """Match a localization key to selected requirement copy without broad words.

    Exact/subsequence matches handle labels such as ``Task ID``. For Chinese
    copy, a three-character shared run allows a renamed label such as
    ``旧执行结果`` to be replaced by the selected ``节点执行结果`` while avoiding
    a generic one-word overlap like ``节点``.
    """
    normalized_key = re.sub(r"\s+", " ", key).strip()
    if not normalized_key:
        return False
    for term in copy_terms:
        normalized_term = re.sub(r"\s+", " ", term).strip()
        if normalized_key in normalized_term or normalized_term in normalized_key:
            return True
        key_runs = re.findall(r"[\u3400-\u9fff]{3,}", normalized_key)
        term_runs = re.findall(r"[\u3400-\u9fff]{3,}", normalized_term)
        for key_run in key_runs:
            for term_run in term_runs:
                for start in range(len(key_run) - 2):
                    if key_run[start:start + 3] in term_run:
                        return True
    return False


def _remove_authorized_localization_rows(
    text: str, copy_terms: set[str], row_keys: set[str], *, mutate_keys: bool,
) -> str:
    if not copy_terms:
        return text
    lines: list[str] = []
    for line in text.splitlines(keepends=True):
        if not line.lstrip().startswith("|"):
            lines.append(line)
            continue
        key = _row_key(line)
        if key and (key in row_keys or _linked_copy_key(key, copy_terms)):
            row_keys.add(key)
            continue
        lines.append(line)
    return "".join(lines)


def _version_history_append_only(
    baseline_markdown: str, candidate_markdown: str,
) -> tuple[str, list[str], list[str]]:
    """Allow only contiguous record rows appended to an existing history table.

    Version history is a document-level administrative derivative of a material
    selected-requirement change.  It cannot authorize edits to past records,
    document information, or any other unselected content.  Product semantics
    of an added summary remain subject to the PRD contract and stage review.
    """
    baseline = _version_history_section(baseline_markdown)
    candidate = _version_history_section(candidate_markdown)
    if baseline is None:
        return candidate_markdown, [], []
    if candidate is None:
        return candidate_markdown, [], ["protected version history section was removed"]
    if baseline["heading"] != candidate["heading"]:
        return candidate_markdown, [], ["protected version history heading changed"]

    baseline_lines = str(baseline["body"]).splitlines(keepends=True)
    candidate_lines = str(candidate["body"]).splitlines(keepends=True)
    baseline_rows = [line for line in baseline_lines if VERSION_RECORD_ROW_RE.match(line)]
    candidate_rows = [line for line in candidate_lines if VERSION_RECORD_ROW_RE.match(line)]
    if candidate_rows[:len(baseline_rows)] != baseline_rows:
        return candidate_markdown, [], ["protected version history rows changed or were reordered"]
    added_rows = candidate_rows[len(baseline_rows):]
    if not added_rows:
        return candidate_markdown, [], []
    if not baseline_rows:
        return candidate_markdown, [], [
            "version history append requires a preserved baseline version record"
        ]

    candidate_indexes = [
        index for index, line in enumerate(candidate_lines) if VERSION_RECORD_ROW_RE.match(line)
    ]
    added_indexes = candidate_indexes[len(baseline_rows):]
    last_baseline_index = candidate_indexes[len(baseline_rows) - 1]
    expected_indexes = list(range(last_baseline_index + 1, last_baseline_index + 1 + len(added_rows)))
    if added_indexes != expected_indexes:
        return candidate_markdown, [], [
            "version history entries must be appended immediately after preserved history rows"
        ]

    added_index_set = set(added_indexes)
    normalized_body = "".join(
        line for index, line in enumerate(candidate_lines) if index not in added_index_set
    )
    normalized_section = str(candidate["heading"]) + normalized_body
    baseline_section = str(baseline["heading"]) + str(baseline["body"])
    if normalized_section != baseline_section:
        return candidate_markdown, [], [
            "version history changes must preserve the existing section and append complete records only"
        ]
    normalized_candidate = (
        candidate_markdown[:int(candidate["body_start"])]
        + normalized_body
        + candidate_markdown[int(candidate["end"]):]
    )
    return normalized_candidate, [row.rstrip("\r\n") for row in added_rows], []


def _version_history_record_failures(rows: Sequence[str]) -> list[str]:
    """Check that a newly appended history row has the canonical record cells."""
    failures: list[str] = []
    for row in rows:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if len(cells) < 4 or not all(cells[:4]):
            failures.append(
                "appended version history record requires version, date, material change summary, and owner"
            )
            continue
        if not VERSION_DATE_RE.fullmatch(cells[1]):
            failures.append("appended version history record date must use YYYY-MM-DD")
    return failures


def _section_without_media(value: str) -> str:
    """Remove media-only markup to distinguish a product change from a layout update."""
    value = DETAIL_MEDIA_RE.sub("", value)
    value = MARKDOWN_IMAGE_RE.sub("", value)
    value = HTML_IMAGE_RE.sub("", value)
    value = re.sub(r"(?m)[ \t]+$", "", value)
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def _has_material_selected_change(
    selected: set[str],
    baseline_sections: Mapping[str, Mapping[str, Any]],
    candidate_sections: Mapping[str, Mapping[str, Any]],
    baseline_rows: Mapping[str, str],
    candidate_rows: Mapping[str, str],
    *,
    baseline_markdown: str,
    candidate_markdown: str,
    copy_terms: set[str],
) -> bool:
    """Return whether a selected behavior, list entry, or linked copy changed.

    Pure screenshot/media substitutions are intentionally not material product
    changes. They remain allowed inside the selected section, but cannot gain a
    document-level version history entry.
    """
    for requirement_id in selected:
        baseline_section = baseline_sections.get(requirement_id)
        candidate_section = candidate_sections.get(requirement_id)
        if baseline_section is None or candidate_section is None:
            return True
        if _section_without_media(str(baseline_section.get("content", ""))) != _section_without_media(
            str(candidate_section.get("content", ""))
        ):
            return True
        if baseline_rows.get(requirement_id) != candidate_rows.get(requirement_id):
            return True
    if not copy_terms:
        return False
    baseline_without_linked_copy = _outer_markdown(
        baseline_markdown, selected, allow_linked_copy=False,
        copy_terms=copy_terms, row_keys=set(), discover_rows=False,
    )
    candidate_without_linked_copy = _outer_markdown(
        candidate_markdown, selected, allow_linked_copy=False,
        copy_terms=copy_terms, row_keys=set(), discover_rows=False,
    )
    return baseline_without_linked_copy != candidate_without_linked_copy


def _outer_markdown(
    text: str,
    selected_ids: set[str],
    *,
    allow_linked_copy: bool,
    copy_terms: set[str],
    row_keys: set[str],
    discover_rows: bool,
) -> str:
    result = _remove_selected_sections(text, selected_ids)
    if selected_ids:
        pattern = "|".join(re.escape(item) for item in sorted(selected_ids, key=len, reverse=True))
        result = re.sub(rf"(?m)^\|\s*(?:{pattern})\s*\|.*(?:\n|$)", "", result)
    if allow_linked_copy:
        result = _remove_authorized_localization_rows(
            result, copy_terms, row_keys, mutate_keys=discover_rows,
        )
    return result


def _contains_ordered(items: Sequence[str], expected: Sequence[str]) -> bool:
    position = 0
    for item in items:
        if position < len(expected) and item == expected[position]:
            position += 1
    return position == len(expected)


def validate_revision_scope(
    manifest: Mapping[str, Any],
    *,
    baseline_markdown: str,
    candidate_markdown: str,
    baseline_assets: Mapping[str, str],
    candidate_assets: Mapping[str, str],
) -> dict[str, Any]:
    """Validate selected semantics while freezing unselected PRD content/assets."""
    selected = {str(item).strip() for item in manifest.get("requirement_ids", []) if str(item).strip()}
    baseline_sections = requirement_sections(baseline_markdown)
    candidate_sections = requirement_sections(candidate_markdown)
    failures: list[str] = []
    checks: list[str] = []
    if not selected:
        failures.append("in-place revision has no confirmed requirement selector")

    for requirement_id, baseline_section in baseline_sections.items():
        if requirement_id in selected:
            continue
        candidate_section = candidate_sections.get(requirement_id)
        if candidate_section is None:
            failures.append(f"protected requirement section {requirement_id} was removed")
        elif candidate_section.get("sha256") != baseline_section.get("sha256"):
            failures.append(f"protected requirement section {requirement_id} changed")
    for requirement_id in candidate_sections:
        if requirement_id not in baseline_sections and requirement_id not in selected:
            failures.append(f"unconfirmed requirement section {requirement_id} was added")

    baseline_rows = requirement_rows(baseline_markdown)
    candidate_rows = requirement_rows(candidate_markdown)
    for requirement_id, baseline_row in baseline_rows.items():
        if requirement_id in selected:
            continue
        if candidate_rows.get(requirement_id) != baseline_row:
            failures.append(f"protected requirement-list row {requirement_id} changed")
    for requirement_id in candidate_rows:
        if requirement_id not in baseline_rows and requirement_id not in selected:
            failures.append(f"unconfirmed requirement-list row {requirement_id} was added")

    allow_linked_copy = bool(
        isinstance(manifest.get("allowed_derivatives"), Mapping)
        and manifest["allowed_derivatives"].get("linked_localization_rows")
    )
    selected_sections = {
        requirement_id: section
        for requirement_id, section in candidate_sections.items()
        if requirement_id in selected
    }
    copy_terms = _selected_copy_terms(selected_sections)
    allow_version_history = bool(
        isinstance(manifest.get("allowed_derivatives"), Mapping)
        and manifest["allowed_derivatives"].get("append_only_version_history")
    )
    normalized_candidate_markdown = candidate_markdown
    added_version_history_rows: list[str] = []
    if allow_version_history:
        normalized_candidate_markdown, added_version_history_rows, history_failures = _version_history_append_only(
            baseline_markdown, candidate_markdown,
        )
        failures.extend(history_failures)
        selected_changed = _has_material_selected_change(
            selected,
            baseline_sections,
            candidate_sections,
            baseline_rows,
            candidate_rows,
            baseline_markdown=baseline_markdown,
            candidate_markdown=normalized_candidate_markdown,
            copy_terms=copy_terms,
        )
        if added_version_history_rows:
            failures.extend(_version_history_record_failures(added_version_history_rows))
            if not selected_changed:
                failures.append(
                    "version history append is not allowed for a layout or media-only selected change"
                )
        elif selected_changed:
            failures.append(
                "material selected requirement change requires an appended version history record"
            )
    linked_copy_keys: set[str] = set()
    candidate_outer = _outer_markdown(
        normalized_candidate_markdown, selected, allow_linked_copy=allow_linked_copy,
        copy_terms=copy_terms, row_keys=linked_copy_keys, discover_rows=True,
    )
    baseline_outer = _outer_markdown(
        baseline_markdown, selected, allow_linked_copy=allow_linked_copy,
        copy_terms=copy_terms, row_keys=linked_copy_keys, discover_rows=False,
    )
    if candidate_outer != baseline_outer:
        failures.append("PRD content outside the confirmed revision scope changed")

    for contract in manifest.get("image_contracts", []):
        if not isinstance(contract, Mapping):
            continue
        ids = [str(item).strip() for item in contract.get("requirement_ids", []) if str(item).strip()]
        actual = [
            reference
            for requirement_id in ids
            for reference in list(candidate_sections.get(requirement_id, {}).get("image_refs", []))
        ]
        expected = [normalize_image_reference(str(item)) for item in contract.get("required_image_refs", [])]
        if any(reference not in actual for reference in expected):
            failures.append("selected requirement images are missing an explicitly confirmed local asset")
        if contract.get("exact_count") and actual != expected:
            failures.append("selected requirement image set does not match its explicit exact-count contract")
        elif contract.get("fixed_order") and not _contains_ordered(actual, expected):
            failures.append("selected requirement images do not preserve the confirmed order")

    allowed_new = {str(path): str(digest) for path, digest in dict(manifest.get("allowed_new_assets", {})).items()}
    for path, digest in baseline_assets.items():
        if candidate_assets.get(path) != digest:
            failures.append(f"protected asset changed or was removed: {path}")
    for path, digest in candidate_assets.items():
        if path not in baseline_assets and allowed_new.get(path) != digest:
            failures.append(f"unconfirmed asset was added: {path}")

    if not failures:
        checks.extend([
            "unselected requirement sections and list rows match the baseline",
            "unselected assets match the baseline",
        ])
        if allow_linked_copy:
            checks.append("only selected-section-linked localization rows may differ")
        if added_version_history_rows:
            checks.append("version history preserves prior records and appends material revision evidence")
        if manifest.get("image_contracts"):
            checks.append("selected requirement image constraints match the confirmed scope")
    return {
        "schema_version": 1,
        "status": "passed" if not failures else "failed",
        "requirement_ids": sorted(selected),
        "selected_requirement_images": {
            requirement_id: list(section.get("image_refs", []))
            for requirement_id, section in selected_sections.items()
        },
        "allowed_linked_copy_rows": sorted(linked_copy_keys),
        "allowed_version_history_rows": added_version_history_rows,
        "checks": checks,
        "failures": failures,
    }


class _ScopedHTMLImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.current_requirement_id: str | None = None
        self._heading_tag: str | None = None
        self._heading_text: list[str] = []
        self.images: dict[str, list[str]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h1", "h2", "h3"}:
            self._heading_tag = tag
            self._heading_text = []
            if tag in {"h1", "h2"}:
                self.current_requirement_id = None
        elif tag == "img" and self.current_requirement_id:
            source = dict(attrs).get("src")
            if source:
                self.images.setdefault(self.current_requirement_id, []).append(normalize_image_reference(source))

    def handle_data(self, data: str) -> None:
        if self._heading_tag:
            self._heading_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != self._heading_tag:
            return
        if tag == "h3":
            match = re.match(r"\s*(\d+\.\d+)\b", "".join(self._heading_text))
            self.current_requirement_id = match.group(1) if match else None
        self._heading_tag = None
        self._heading_text = []


def html_requirement_image_refs(html: str) -> dict[str, list[str]]:
    parser = _ScopedHTMLImageParser()
    parser.feed(html)
    parser.close()
    return parser.images


def validate_rendered_html_scope(
    scope_report: Mapping[str, Any], html: str,
) -> list[str]:
    """Ensure rendered section images retain the source Markdown's local ordering."""
    html_images = html_requirement_image_refs(html)
    failures: list[str] = []
    selected_images = scope_report.get("selected_requirement_images", {})
    if not isinstance(selected_images, Mapping):
        return ["revision scope report has malformed selected requirement images"]
    for requirement_id, markdown_refs in selected_images.items():
        expected = [normalize_image_reference(str(item)) for item in markdown_refs]
        actual = html_images.get(str(requirement_id), [])
        if actual != expected:
            failures.append(
                f"rendered HTML images for requirement {requirement_id} do not match staged Markdown order"
            )
    return failures
