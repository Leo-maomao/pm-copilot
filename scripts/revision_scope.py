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
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence
import unicodedata


REQUIREMENT_HEADING_RE = re.compile(
    r"(?m)^###\s+(?P<id>\d+\.\d+)\b(?P<title>.*?)\s*$"
)
REQUIREMENT_ROW_RE = re.compile(r"(?m)^\|\s*(?P<id>\d+\.\d+)\s*\|.*(?:\n|$)")
REQUIREMENT_ID_REFERENCE_RE = re.compile(r"(?<![\d.])(?P<id>\d+\.\d+)(?![\d.])")
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
DETAIL_MEDIA_PREFIX_RE = re.compile(r"\[\[\s*prd-detail-media\b", re.IGNORECASE)
DETAIL_MEDIA_SRC_RE = re.compile(
    r"\bsrc\s*=\s*[\"'](?P<value>[^\"']+)[\"']", re.IGNORECASE
)
DETAIL_MEDIA_ATTRIBUTE_RE = re.compile(
    r'\b(?P<name>src|alt|copy)\s*=\s*"(?P<value>[^"]*)"',
    re.IGNORECASE | re.DOTALL,
)
ASSET_REFERENCE_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])(?:\./)?assets/[\w .()\-\u3400-\u9fff]+?\.(?:png|jpe?g|webp)(?![A-Za-z0-9_.-])",
    re.IGNORECASE,
)
LINKED_COPY_RE = re.compile(r"多语言|文案|\bcopy\b|\bi18n\b|locali[sz]ation", re.IGNORECASE)
PURE_TEXT_FENCE_OPEN_RE = re.compile(
    r"^[ \t]*`{3,}(?:text|plain|txt)?[ \t]*(?:\r?\n)?$", re.IGNORECASE,
)
PURE_TEXT_FENCE_CLOSE_RE = re.compile(r"^[ \t]*`{3,}[ \t]*(?:\r?\n)?$")
FIXED_ORDER_RE = re.compile(r"固定顺序|按顺序|顺序为|顺序.*?(?:成功|失败)|\bfixed\s+order\b|\bin\s+(?:this|the)\s+order\b", re.IGNORECASE)
EXACT_IMAGE_SET_RE = re.compile(
    r"仅(?:保留|引用)?|只(?:保留|引用)?|只能|不(?:引用|生成).{0,24}(?:第?\s*(?:三|3)\s*(?:张)?(?:图|图示|图片)|third\s+(?:image|figure))|"
    r"\b(?:only|exactly|no\s+(?:third|additional)\s+(?:image|figure))\b",
    re.IGNORECASE,
)
EXTRACTION_NUMERIC_REQUIREMENT_RANGE_RE = re.compile(
    r"(?<![\d.])(\d+)\.(\d+)\s*(?:-|~|–|—|至|到|to|through|until)\s*(\d+)\.(\d+)(?![\d.])",
    re.IGNORECASE,
)
EXTRACTION_SOURCE_REQUIREMENT_ID_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])(?:\d+(?:\.\d+)+|[A-Za-z][A-Za-z0-9_]*-\d+)(?![A-Za-z0-9_.-])"
)

# Asset trees are delivery content, not a mirror of an author's filesystem.
# Finder/Explorer metadata is non-renderable in a PRD and unstable across
# copies, so it cannot participate in a revision's content baseline.
NON_CONTENT_ASSET_FILENAMES = frozenset({
    "thumbs.db",
    "ehthumbs.db",
    "desktop.ini",
    "icon\r",
})
VISUAL_COVERAGE_DECISIONS = frozenset({
    "real_figure",
    "required_placeholder",
    "not_required",
})
_VISUAL_COVERAGE_PRECEDENCE = {
    "not_required": 0,
    "real_figure": 1,
    "required_placeholder": 2,
}


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def is_content_asset_relative_path(value: Path | str) -> bool:
    """Return whether an assets/-relative path is deliverable PRD content.

    Hidden files and directories are deliberately excluded rather than merely
    ignoring one operating-system filename. They are not stable, addressable
    PRD media, and treating them as protected resources makes a copied stage
    disagree with its canonical source. Known non-hidden OS metadata files
    receive the same treatment.
    """
    path = Path(value)
    if path.is_absolute() or not path.parts:
        return False
    for part in path.parts:
        if part in {"", ".", ".."} or part.startswith("."):
            return False
    return path.name.casefold() not in NON_CONTENT_ASSET_FILENAMES


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
            "start": match.start(),
            "end": next_start,
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


def requirement_ids(text: str) -> list[str]:
    """Return stable requirement IDs from the list and detail sections in source order.

    Requirement-list rows and detail headings are both authoritative PRD
    structures.  Keeping their parser here prevents a controller from
    materializing trace coverage for one inventory while a validator checks a
    differently parsed inventory.  Version-history rows are intentionally
    removed first because semantic versions such as ``5.1`` are not PRD
    requirement IDs.
    """
    current = _without_version_history(text)
    matches = [
        (match.start(), match.group("id"))
        for expression in (REQUIREMENT_ROW_RE, REQUIREMENT_HEADING_RE)
        for match in expression.finditer(current)
    ]
    return list(dict.fromkeys(
        requirement_id
        for _, requirement_id in sorted(matches, key=lambda item: item[0])
    ))


def _section_bodies_for_titles(text: str, titles: Sequence[str]) -> list[str]:
    """Return H2+ section bodies whose normalized title matches ``titles``."""
    accepted = {_section_title(title) for title in titles if title.strip()}
    if not accepted:
        return []
    headings = list(SECTION_HEADING_RE.finditer(text))
    bodies: list[str] = []
    for index, heading in enumerate(headings):
        title = _section_title(heading.group("title"))
        without_chinese_number = re.sub(r"^[一二三四五六七八九十]+、\s*", "", title)
        if title not in accepted and without_chinese_number not in accepted:
            continue
        level = len(heading.group("hashes"))
        end = len(text)
        for following in headings[index + 1:]:
            if len(following.group("hashes")) <= level:
                end = following.start()
                break
        bodies.append(text[heading.end():end])
    return bodies


def _markdown_table_data_rows(text: str) -> list[str]:
    """Return Markdown table rows while excluding headers and separators."""
    lines = text.splitlines()
    table_rows = [
        index for index, line in enumerate(lines)
        if line.lstrip().startswith("|")
    ]

    def is_separator(line: str) -> bool:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)

    skipped: set[int] = set()
    for index in table_rows:
        if is_separator(lines[index]):
            skipped.add(index)
            previous = index - 1
            if previous in table_rows:
                skipped.add(previous)
    return [lines[index] for index in table_rows if index not in skipped]


def requirement_linked_rows(
    text: str, section_titles: Sequence[str],
) -> tuple[dict[str, list[str]], list[str]]:
    """Map optional-section table rows to explicit final PRD requirement IDs.

    A localization or tracking row can support more than one requirement, but
    it must name each target requirement ID in its own row.  Section headings
    and semantic text are deliberately not treated as a link: doing so would
    silently apply one optional section to every requirement.  Rows with no
    known final ID are returned separately so callers can fail closed.
    """
    known_id_order = requirement_ids(text)
    known_ids = set(known_id_order)
    linked: dict[str, list[str]] = {requirement_id: [] for requirement_id in known_id_order}
    unlinked: list[str] = []
    for body in _section_bodies_for_titles(text, section_titles):
        for row in _markdown_table_data_rows(body):
            candidates = list(dict.fromkeys(
                match.group("id") for match in REQUIREMENT_ID_REFERENCE_RE.finditer(row)
            ))
            references = [candidate for candidate in candidates if candidate in known_ids]
            if not references or len(references) != len(candidates):
                unlinked.append(row)
                continue
            for requirement_id in references:
                linked[requirement_id].append(row)
    return linked, unlinked


def aggregate_visual_evidence_by_requirement(
    visual_evidence: Sequence[object], requirement_id_values: Sequence[str],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Aggregate immutable visual evidence into one summary per requirement.

    A requirement can legitimately have several observable states, and each
    state can have its own screenshot or fallback.  The aggregate therefore
    preserves every evidence record and selects the conservative requirement
    decision: a remaining required placeholder takes precedence over a real
    figure, which takes precedence over a state that needs no figure.
    """
    requirement_order = list(dict.fromkeys(
        str(requirement_id).strip()
        for requirement_id in requirement_id_values
        if str(requirement_id).strip()
    ))
    known_ids = set(requirement_order)
    records: dict[str, list[Mapping[str, Any]]] = {
        requirement_id: [] for requirement_id in requirement_order
    }
    failures: list[str] = []
    for index, item in enumerate(visual_evidence, start=1):
        if not isinstance(item, Mapping):
            failures.append(f"visual evidence item {index} must be a mapping")
            continue
        requirement_id = str(item.get("target_ref", "")).strip()
        if not requirement_id:
            failures.append(f"visual evidence item {index} requires target_ref")
            continue
        if requirement_id not in known_ids:
            failures.append(
                f"visual evidence target_ref {requirement_id} is not a final PRD requirement"
            )
            continue
        decision = str(item.get("coverage_decision", "")).strip()
        if decision not in VISUAL_COVERAGE_DECISIONS:
            failures.append(
                f"visual evidence {requirement_id} has invalid coverage_decision"
            )
            continue
        if not str(item.get("rationale", "")).strip():
            failures.append(f"visual evidence {requirement_id} requires rationale")
            continue
        records[requirement_id].append(item)

    aggregate: dict[str, dict[str, Any]] = {}
    for requirement_id in requirement_order:
        items = records[requirement_id]
        if not items:
            continue
        decisions = [str(item["coverage_decision"]).strip() for item in items]
        rationales = list(dict.fromkeys(
            str(item["rationale"]).strip() for item in items
        ))
        aggregate[requirement_id] = {
            "decision": max(decisions, key=lambda value: _VISUAL_COVERAGE_PRECEDENCE[value]),
            "rationales": rationales,
            "records": items,
        }
    return aggregate, failures


def asset_digests(root: Path) -> dict[str, str]:
    """Hash deliverable local asset bytes with output-root-relative paths.

    A staged delivery must be self-contained.  ``Path.is_file()`` follows
    symbolic links, which used to let a link in ``assets/`` hash bytes outside
    the staging directory and then be silently dereferenced by a later copy.
    Reject links at inventory time instead: both the baseline and the staged
    validation paths call this function before a revision can be promoted.
    """
    assets = root / "assets"
    if assets.is_symlink():
        raise ValueError("PRD asset directory must not be a symbolic link: assets")
    if not assets.is_dir():
        return {}
    digests: dict[str, str] = {}
    for path in sorted(assets.rglob("*")):
        relative = path.relative_to(assets)
        if path.is_symlink():
            raise ValueError(
                "PRD asset tree must not contain a symbolic link: "
                f"assets/{relative.as_posix()}"
            )
        if path.is_file() and is_content_asset_relative_path(relative):
            digests[path.relative_to(root).as_posix()] = digest_bytes(path.read_bytes())
    return digests


def revision_scope_manifest_digest(manifest: Mapping[str, Any]) -> str:
    """Return the stable digest used to bind scope evidence to its manifest."""
    return hashlib.sha256(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def revision_artifact_set_snapshot(
    root: Path, *, allow_missing_artifacts: bool = False,
) -> dict[str, Any]:
    """Describe the Markdown, HTML, and asset bytes covered by a revision attestation.

    Controllers can request an incomplete snapshot while constructing a failed
    report; final validators use the default and require both derived files.
    """
    prd_path = root / "prd.md"
    html_path = root / "prd.html"
    if not allow_missing_artifacts and (not prd_path.is_file() or not html_path.is_file()):
        raise FileNotFoundError("in_place_revision final scope attestation requires prd.md and prd.html")
    snapshot: dict[str, Any] = {
        "prd_md_sha256": digest_bytes(prd_path.read_bytes()) if prd_path.is_file() else None,
        "prd_html_sha256": digest_bytes(html_path.read_bytes()) if html_path.is_file() else None,
        "assets": asset_digests(root),
    }
    snapshot["sha256"] = digest_bytes(
        json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    return snapshot


def normalize_extraction_selector(value: str) -> str:
    """Normalize a human source selector without treating punctuation as proof."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^\w\u3400-\u9fff]+", "", normalized)


def source_requirement_ids(source_text: str) -> list[str]:
    """Read stable IDs from source headings and requirement-list rows only."""
    candidates: list[str] = []
    for line in source_text.splitlines():
        if not re.match(r"\s*(?:#{1,6}\s+|\|)", line):
            continue
        candidates.extend(EXTRACTION_SOURCE_REQUIREMENT_ID_RE.findall(line))
    return list(dict.fromkeys(candidates))


def _source_headings_for_extraction(source_text: str) -> list[tuple[str, str]]:
    headings: list[tuple[str, str]] = []
    for raw_heading in re.findall(r"(?m)^#{1,6}\s+(.+?)\s*$", source_text):
        heading = raw_heading.strip()
        without_identifier = re.sub(
            r"^(?:(?:需求|requirement)\s*)?(?:\d+(?:\.\d+)+|[A-Za-z][A-Za-z0-9_-]*-\d+)[.、:：\-\s]*",
            "",
            heading,
            flags=re.IGNORECASE,
        ).strip()
        for candidate in (heading, without_identifier):
            normalized = normalize_extraction_selector(candidate)
            if normalized:
                headings.append((normalized, heading))
    return headings


def _source_text_spans_for_extraction(source_text: str) -> list[str]:
    spans: list[str] = []
    for line in source_text.splitlines():
        if re.match(r"\s*#{1,6}\s+", line):
            continue
        cleaned = re.sub(r"^\s*(?:[-*+]\s+|\|\s*)", "", line).strip(" |\t")
        for fragment in re.split(r"[。！？!?；;]+", cleaned):
            normalized = normalize_extraction_selector(fragment)
            if normalized:
                spans.append(normalized)
    return spans


def _is_substantive_extraction_selector(selector: str) -> bool:
    cjk_count = len(re.findall(r"[\u3400-\u9fff]", selector))
    latin_words = re.findall(r"[a-z0-9]+", selector, flags=re.IGNORECASE)
    return cjk_count >= 3 or len("".join(latin_words)) >= 8 or len(latin_words) >= 2


def resolve_extraction_scope(
    source_text: str, selected_scope: Sequence[str],
) -> tuple[list[dict[str, object]], str | None]:
    """Resolve each extraction selector against immutable source text.

    The result is intentionally deterministic so the controller and final
    trace validator can independently invoke the same selector policy against
    their own source snapshots.
    """
    source_ids = set(source_requirement_ids(source_text))
    headings = _source_headings_for_extraction(source_text)
    text_spans = _source_text_spans_for_extraction(source_text)
    resolutions: list[dict[str, object]] = []

    for raw_selector in selected_scope:
        selector = str(raw_selector).strip()
        normalized = normalize_extraction_selector(selector)
        if not normalized:
            return [], "contains an empty selector"

        ranges = list(EXTRACTION_NUMERIC_REQUIREMENT_RANGE_RE.finditer(selector))
        if ranges:
            for match in ranges:
                start_major, start_minor, end_major, end_minor = map(int, match.groups())
                if start_major != end_major or start_minor > end_minor:
                    return [], f"has an invalid requirement-ID range: {selector}"
                expected = [f"{start_major}.{minor}" for minor in range(start_minor, end_minor + 1)]
                missing = [item for item in expected if item not in source_ids]
                if missing:
                    return [], f"references IDs absent from the source snapshot: {', '.join(missing)}"
                resolutions.append({"selector": selector, "kind": "requirement_id_range", "matches": expected})
            continue

        selected_ids = list(dict.fromkeys(EXTRACTION_SOURCE_REQUIREMENT_ID_RE.findall(selector)))
        if selected_ids:
            unknown = [item for item in selected_ids if item not in source_ids]
            if unknown:
                return [], f"references IDs absent from the source snapshot: {', '.join(unknown)}"
            resolutions.append({"selector": selector, "kind": "requirement_id", "matches": selected_ids})
            continue

        matched_headings = {original for candidate, original in headings if candidate and candidate in normalized}
        if len(matched_headings) == 1:
            resolutions.append({"selector": selector, "kind": "heading", "matches": sorted(matched_headings)})
            continue
        if len(matched_headings) > 1:
            return [], f"matches multiple source headings: {selector}"

        if _is_substantive_extraction_selector(selector):
            matched_spans = [
                span for span in text_spans
                if normalized in span or (len(span) >= 8 and span in normalized)
            ]
            if len(matched_spans) == 1:
                resolutions.append({
                    "selector": selector,
                    "kind": "source_text",
                    "matches": sorted(set(matched_spans)),
                })
                continue
            if len(matched_spans) > 1:
                return [], f"matches multiple source text locations: {selector}"

        return [], f"cannot be uniquely resolved against the source snapshot: {selector}"
    return resolutions, None


def _extraction_source_aliases(
    sources: Mapping[str, str], source_aliases: Mapping[str, Sequence[str]] | None,
) -> tuple[dict[str, list[str]], str | None]:
    """Build a normalized, ambiguity-preserving source-name lookup.

    A source ID is the durable qualifier.  Display names are convenience
    aliases only: duplicate filenames deliberately remain ambiguous rather
    than silently choosing whichever source happened to be registered first.
    """
    aliases: dict[str, list[str]] = {}
    for raw_source_id, source_text in sources.items():
        source_id = str(raw_source_id).strip()
        if not source_id:
            return {}, "contains an empty source ID"
        if not isinstance(source_text, str):
            return {}, f"source {source_id} must contain text"
        names = [source_id]
        if source_aliases:
            configured = source_aliases.get(source_id)
            if configured is not None:
                names.extend(str(item).strip() for item in configured if str(item).strip())
        for name in names:
            normalized = normalize_extraction_selector(name)
            if normalized:
                aliases.setdefault(normalized, []).append(source_id)
    return aliases, None


def _split_multi_source_selector(
    selector: str, aliases: Mapping[str, Sequence[str]],
) -> tuple[str | None, str, str | None]:
    """Return an optional source ID and the source-local selector.

    Only a prefix that matches a known source ID or configured source alias is
    treated as a qualifier.  A normal heading such as ``5.1: Checkout`` keeps
    its ordinary single-source meaning instead of becoming an unknown source
    reference.
    """
    match = re.match(r"^\s*(?:\[(?P<bracket>[^\]]+)\]|(?P<plain>[^:：]+))\s*[:：]\s*(?P<body>.+?)\s*$", selector)
    if not match:
        return None, selector, None
    qualifier = (match.group("bracket") or match.group("plain") or "").strip()
    source_ids = list(aliases.get(normalize_extraction_selector(qualifier), []))
    if not source_ids:
        return None, selector, None
    if len(source_ids) != 1:
        return None, selector, f"uses an ambiguous source qualifier: {qualifier}"
    body = match.group("body").strip()
    if not body:
        return None, selector, f"has an empty selector after source qualifier: {qualifier}"
    return source_ids[0], body, None


def resolve_multi_source_extraction_scope(
    sources: Mapping[str, str], selected_scope: Sequence[str], *,
    source_aliases: Mapping[str, Sequence[str]] | None = None,
) -> tuple[list[dict[str, object]], str | None]:
    """Resolve source-qualified or globally unique extraction selectors.

    ``source_id: selector`` explicitly chooses a snapshot.  An unqualified
    selector is accepted only when exactly one immutable source snapshot can
    resolve it.  The returned records retain the resolved ``source_id`` and a
    source-local selector, which lets the controller persist independent
    per-source lineage and lets the validator re-check each snapshot without
    relying on a mutable external file path.
    """
    aliases, aliases_problem = _extraction_source_aliases(sources, source_aliases)
    if aliases_problem:
        return [], aliases_problem
    if not sources:
        return [], "has no source snapshots"

    resolutions: list[dict[str, object]] = []
    for raw_selector in selected_scope:
        selector = str(raw_selector).strip()
        if not selector:
            return [], "contains an empty selector"
        source_id, local_selector, qualifier_problem = _split_multi_source_selector(selector, aliases)
        if qualifier_problem:
            return [], qualifier_problem
        if source_id is not None:
            resolved, problem = resolve_extraction_scope(sources[source_id], [local_selector])
            if problem:
                return [], f"source {source_id} {problem}"
            resolutions.extend({"source_id": source_id, **item} for item in resolved)
            continue

        candidates: list[tuple[str, list[dict[str, object]]]] = []
        source_problems: list[tuple[str, str]] = []
        for candidate_id, source_text in sources.items():
            resolved, problem = resolve_extraction_scope(source_text, [selector])
            if problem:
                source_problems.append((candidate_id, problem))
            else:
                candidates.append((candidate_id, resolved))
        if len(candidates) == 1:
            candidate_id, resolved = candidates[0]
            resolutions.extend({"source_id": candidate_id, **item} for item in resolved)
            continue
        if len(candidates) > 1:
            candidate_ids = ", ".join(source_id for source_id, _ in candidates)
            return [], (
                f"matches more than one extraction source ({candidate_ids}): {selector}; "
                "qualify it as source-id: selector"
            )
        # All sources reject the selector.  Report the first deterministic
        # reason so users receive the same clarification prompt across runs.
        if source_problems:
            source_id, problem = source_problems[0]
            return [], f"source {source_id} {problem}"
        return [], f"cannot be uniquely resolved against any source snapshot: {selector}"
    return resolutions, None


def _deduplicate(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


_DELETION_INTENT_RE = re.compile(
    r"(?:删除|删掉|移除|去除|废弃|下线|delete|remove|drop)", re.IGNORECASE,
)
_NEGATED_DELETION_INTENT_RE = re.compile(
    r"(?:不|不要|无需|not\s+to|do\s+not|don't)\s*(?:删除|删掉|移除|去除|废弃|下线|delete|remove|drop)",
    re.IGNORECASE,
)


def _explicitly_deleted_requirement_ids(scope_text: str, selected: Sequence[str]) -> list[str]:
    """Return only selectors explicitly paired with a confirmed delete intent.

    A selected ID alone authorizes a revision, never a destructive removal.
    Keep the evidence local to one sentence and close to the delete verb so a
    sentence such as "delete 5.2; retain 5.3" cannot accidentally authorize
    both IDs. Ambiguous wording intentionally leaves the ID protected.
    """
    deleted: list[str] = []
    for sentence in re.split(r"[\r\n。！？!?；;,，]+", scope_text):
        if not _DELETION_INTENT_RE.search(sentence) or _NEGATED_DELETION_INTENT_RE.search(sentence):
            continue
        action_offsets = [match.start() for match in _DELETION_INTENT_RE.finditer(sentence)]
        for requirement_id in selected:
            id_match = re.search(
                rf"(?<![0-9.]){re.escape(requirement_id)}(?![0-9.])", sentence,
            )
            if id_match and any(abs(id_match.start() - offset) <= 40 for offset in action_offsets):
                deleted.append(requirement_id)
    return _deduplicate(deleted)


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
    deleted = _explicitly_deleted_requirement_ids(confirmed_scope_text, selected)
    evidence_refs = _asset_references(confirmed_scope_text)
    image_contracts: list[dict[str, Any]] = []
    active_selected = [item for item in selected if item not in deleted]
    if len(active_selected) == 1 and evidence_refs:
        image_contracts.append({
            "requirement_ids": active_selected,
            "required_image_refs": evidence_refs,
            "exact_count": bool(EXACT_IMAGE_SET_RE.search(confirmed_scope_text)),
            "fixed_order": bool(FIXED_ORDER_RE.search(confirmed_scope_text)),
            "source": "explicit local asset references in confirmed scope",
        })
    return {
        "schema_version": 1,
        "mode": "in_place_revision",
        "requirement_ids": selected,
        "deleted_requirement_ids": deleted,
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


def _table_cells(row: str) -> list[str]:
    """Return Markdown table cells without treating prose pipes as structure."""
    if not row.lstrip().startswith("|"):
        return []
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def _normalized_table_cells(row: str) -> tuple[str, ...]:
    """Return table cells normalized for identity checks without changing bytes."""
    return tuple(
        re.sub(r"\s+", " ", cell).strip().casefold()
        for cell in _table_cells(row)
    )


def _table_separator_row(row: str) -> bool:
    cells = _table_cells(row)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def _localization_table_blocks(text: str) -> list[dict[str, Any]]:
    """Locate actual localization tables, never generic requirement tables.

    Linked copy may only be revised inside a table whose header identifies it as
    copy/localization content.  Looking at arbitrary pipe rows made a selected
    requirement-list row look like a translation row when its title shared a
    word with the selected detail.
    """
    lines = text.splitlines(keepends=True)
    blocks: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        if not lines[index].lstrip().startswith("|"):
            index += 1
            continue
        start = index
        while index < len(lines) and lines[index].lstrip().startswith("|"):
            index += 1
        end = index
        if (
            end - start >= 3
            and _table_separator_row(lines[start + 1])
            and LINKED_COPY_RE.search(" ".join(_table_cells(lines[start])))
        ):
            blocks.append({
                "start": start,
                "end": end,
                "data_indexes": list(range(start + 2, end)),
            })
    return blocks


def _plain_copy_value(value: str) -> str:
    """Normalize a visible-copy cell using the PRD pure-text contract."""
    value = re.sub(r"<br\s*/?>", " ", value.strip(), flags=re.IGNORECASE)
    value = re.sub(r"^[-*]\s+", "", value)
    return value.strip("`\"'“”‘’ ")


def _localization_table_copy_values(
    lines: Sequence[str], block: Mapping[str, Any],
) -> list[str]:
    """Return the visible-copy column from a recognized localization table."""
    values: list[str] = []
    for index in block["data_indexes"]:
        cells = _table_cells(lines[int(index)])
        if not cells:
            return []
        value = _plain_copy_value(cells[0])
        if not value:
            return []
        values.append(value)
    return values


def _pure_text_checklist_before_table(
    lines: Sequence[str], table_start: int,
) -> dict[str, Any] | None:
    """Find the adjacent fenced copy checklist that a localization table owns.

    The output validator recognizes fenced ``text``/``plain``/``txt`` blocks
    (and an unlabeled fence) immediately before a copy checklist. Treating a
    nearby arbitrary code block as a derivative would let a scoped revision
    rewrite unrelated prose, so the association deliberately requires direct
    adjacency apart from blank lines.
    """
    close_index = table_start - 1
    while close_index >= 0 and not lines[close_index].strip():
        close_index -= 1
    if close_index < 0 or not PURE_TEXT_FENCE_CLOSE_RE.fullmatch(lines[close_index]):
        return None

    open_index = close_index - 1
    while open_index >= 0:
        line = lines[open_index]
        if PURE_TEXT_FENCE_OPEN_RE.fullmatch(line):
            values = [
                _plain_copy_value(item)
                for item in lines[open_index + 1:close_index]
                if _plain_copy_value(item)
            ]
            return {
                "open_index": open_index,
                "body_start": open_index + 1,
                "body_end": close_index,
                "close_index": close_index,
                "values": values,
            }
        # A preceding fence or heading means this closing fence is not a
        # directly owned checklist block.
        if PURE_TEXT_FENCE_CLOSE_RE.fullmatch(line) or SECTION_HEADING_RE.match(line.rstrip("\r\n")):
            return None
        open_index -= 1
    return None


def _remove_mirrored_localization_checklists(text: str) -> str:
    """Remove only fenced blocks that exactly mirror their adjacent table.

    This is used during scope comparison. A matching pure-text block is a
    redundant projection of the table, not independent document scope. Exact
    equality is required so a manual change to an unselected copy line remains
    visible to the revision-scope gate.
    """
    lines = text.splitlines(keepends=True)
    ranges: list[tuple[int, int]] = []
    for table in _localization_table_blocks(text):
        checklist = _pure_text_checklist_before_table(lines, int(table["start"]))
        if checklist is None:
            continue
        table_values = _localization_table_copy_values(lines, table)
        if table_values and checklist["values"] == table_values:
            ranges.append((int(checklist["open_index"]), int(checklist["close_index"]) + 1))
    for start, end in sorted(ranges, reverse=True):
        del lines[start:end]
    return "".join(lines)


def _ascii_copy_tokens(value: str) -> set[str]:
    """Extract stable ASCII copy identifiers such as ``Task ID`` / ``taskId``."""
    tokens: set[str] = set()
    for fragment in re.findall(r"[A-Za-z][A-Za-z0-9 _-]*", value):
        normalized = re.sub(r"[^a-z0-9]", "", fragment.casefold())
        if len(normalized) >= 4 and normalized not in {
            "copy", "error", "node", "status", "task", "title", "result",
        }:
            tokens.add(normalized)
    return tokens


def _chinese_copy_ngrams(value: str) -> set[str]:
    """Extract specific CJK copy fragments while excluding broad two-character words."""
    ngrams: set[str] = set()
    for run in re.findall(r"[\u3400-\u9fff]{3,}", value):
        ngrams.update(run[start:start + 3] for start in range(len(run) - 2))
    return ngrams


def _weakly_renamed_copy_key(key: str, candidate_keys: Iterable[str]) -> bool:
    """Recognize a short renamed label only when a candidate label contains it.

    This is deliberately weaker than a row ownership match and is used only to
    bridge the adjacent legacy row of an already anchored localization group.
    It covers changes such as ``失败`` -> ``执行失败`` without allowing arbitrary
    localization-table edits.
    """
    normalized = re.sub(r"\s+", "", key).strip()
    if not normalized:
        return False
    for candidate_key in candidate_keys:
        candidate = re.sub(r"\s+", "", candidate_key).strip()
        if not candidate:
            continue
        if normalized.isascii() and candidate.isascii():
            compact = re.sub(r"[^a-z0-9]", "", normalized.casefold())
            candidate_compact = re.sub(r"[^a-z0-9]", "", candidate.casefold())
            if len(compact) >= 4 and (compact in candidate_compact or candidate_compact in compact):
                return True
        elif re.fullmatch(r"[\u3400-\u9fff]{2,}", normalized) and normalized in candidate:
            return True
    return False


def _localization_row_match_score(baseline_row: str, candidate_row: str) -> int:
    """Score a deterministic row-level correspondence inside one copy table."""
    baseline_cells = _normalized_table_cells(baseline_row)
    candidate_cells = _normalized_table_cells(candidate_row)
    baseline_key = baseline_cells[0] if baseline_cells else ""
    candidate_key = candidate_cells[0] if candidate_cells else ""
    if not baseline_key or not candidate_key:
        return 0
    if baseline_cells == candidate_cells:
        return 200
    context_evidence = 0
    for baseline_cell, candidate_cell in zip(baseline_cells[1:], candidate_cells[1:]):
        if baseline_cell == candidate_cell:
            context_evidence += 12
        elif _ascii_copy_tokens(baseline_cell) & _ascii_copy_tokens(candidate_cell):
            context_evidence += 6
        elif _chinese_copy_ngrams(baseline_cell) & _chinese_copy_ngrams(candidate_cell):
            context_evidence += 4
    if baseline_key == candidate_key:
        # The visible copy can repeat. Matching usage/parameter cells make a
        # same-label row distinguishable without treating its position as an
        # identity signal.
        return 100 + min(context_evidence, 30)
    if baseline_cells[1:] and baseline_cells[1:] == candidate_cells[1:]:
        # A renamed label with an unchanged usage/parameter tuple is stronger
        # than a word-overlap guess, but remains weaker than the same label.
        return 90
    baseline_ascii = _ascii_copy_tokens(baseline_row)
    candidate_ascii = _ascii_copy_tokens(candidate_row)
    if baseline_ascii & candidate_ascii:
        return 80 + min(context_evidence, 15)
    baseline_chinese = _chinese_copy_ngrams(baseline_row)
    candidate_chinese = _chinese_copy_ngrams(candidate_row)
    if baseline_chinese & candidate_chinese:
        return 60 + min(context_evidence, 15)
    if _weakly_renamed_copy_key(baseline_key, [candidate_key]):
        return 20
    return 0


def _localization_heading_context(lines: Sequence[str], table_start: int) -> tuple[tuple[int, str], ...]:
    """Return the stable Markdown-heading ancestry for a localization table."""
    headings: list[tuple[int, str]] = []
    for line in lines[:table_start]:
        match = SECTION_HEADING_RE.match(line.rstrip("\r\n"))
        if not match:
            continue
        level = len(match.group("hashes"))
        title = _section_title(match.group("title"))
        while headings and headings[-1][0] >= level:
            headings.pop()
        headings.append((level, title))
    return tuple(headings)


def _localization_table_identity(
    block: Mapping[str, Any], lines: Sequence[str], copy_terms: set[str],
) -> dict[str, Any]:
    """Build non-positional evidence for matching a localization table.

    A complete candidate may remove an unrelated preceding table, so table
    ordinal is not an identity. The immutable header, heading ancestry, and
    unselected rows are safe evidence because none is authorized to change.
    """
    start = int(block["start"])
    stable_rows = frozenset(
        _normalized_table_cells(lines[index])
        for index in block["data_indexes"]
        if not _linked_copy_key(lines[index], copy_terms)
    )
    return {
        "header": _normalized_table_cells(lines[start]),
        "heading_context": _localization_heading_context(lines, start),
        "stable_rows": stable_rows,
    }


def _matching_baseline_localization_table(
    candidate_block: Mapping[str, Any],
    *,
    candidate_lines: Sequence[str],
    baseline_blocks: Sequence[Mapping[str, Any]],
    baseline_lines: Sequence[str],
    copy_terms: set[str],
) -> tuple[int | None, str | None]:
    """Return the only baseline table attributable to a candidate table.

    Prefer matching heading ancestry when it survives the candidate rewrite;
    otherwise require a uniquely strongest stable-row overlap. A table with no
    unique identity is unsafe to merge, even if it happens to be at a familiar
    ordinal position.
    """
    candidate_identity = _localization_table_identity(
        candidate_block, candidate_lines, copy_terms,
    )
    baseline_identities = [
        _localization_table_identity(block, baseline_lines, copy_terms)
        for block in baseline_blocks
    ]
    header_matches = [
        index
        for index, identity in enumerate(baseline_identities)
        if identity["header"] == candidate_identity["header"]
    ]
    if not header_matches:
        return None, "cannot safely merge linked localization rows without a matching baseline table identity"

    context_matches = [
        index
        for index in header_matches
        if candidate_identity["heading_context"]
        and baseline_identities[index]["heading_context"] == candidate_identity["heading_context"]
    ]
    eligible = context_matches or header_matches
    overlap_counts = {
        index: len(candidate_identity["stable_rows"] & baseline_identities[index]["stable_rows"])
        for index in eligible
    }
    best_overlap = max(overlap_counts.values(), default=0)
    if best_overlap:
        best_matches = [
            index for index in eligible
            if overlap_counts[index] == best_overlap
        ]
        if len(best_matches) == 1:
            return best_matches[0], None
        return None, "cannot safely merge linked localization rows because the matching baseline table is ambiguous"
    if len(eligible) == 1:
        return eligible[0], None
    return None, "cannot safely merge linked localization rows because the matching baseline table is ambiguous"


def _selected_copy_terms(candidate_sections: Mapping[str, Mapping[str, Any]]) -> set[str]:
    terms: set[str] = set()
    for section in candidate_sections.values():
        plain = re.sub(r"[`*_#|<>]", " ", str(section.get("content", "")))
        for item in re.findall(r"[\u3400-\u9fff]{2,}|[A-Za-z][A-Za-z0-9 _-]{2,}", plain):
            compact = re.sub(r"\s+", " ", item).strip()
            if len(compact) >= 2:
                terms.add(compact)
    return terms


def _linked_copy_key(value: str, copy_terms: set[str]) -> bool:
    """Match a localization row to selected content using stable cell evidence.

    A copy label is intentionally allowed to change.  Therefore the full row,
    including its usage location and parameter cell, participates in matching:
    ``任务编号：{taskId}`` remains attributable when the new label is ``Task ID``.
    Three-character CJK fragments and normalized non-generic ASCII identifiers
    avoid accepting a generic one-word overlap as scope authority.
    """
    normalized_value = re.sub(r"\s+", " ", value).strip()
    if not normalized_value:
        return False
    value_ascii = _ascii_copy_tokens(normalized_value)
    value_chinese = _chinese_copy_ngrams(normalized_value)
    for term in copy_terms:
        normalized_term = re.sub(r"\s+", " ", term).strip()
        if not normalized_term:
            continue
        term_ascii = _ascii_copy_tokens(normalized_term)
        term_chinese = _chinese_copy_ngrams(normalized_term)
        # Media attributes such as ``copy``, ``alt`` and ``png`` are not
        # localization ownership evidence. Only normalized, non-generic ASCII
        # identifiers or meaningful CJK fragments can match a table row.
        if not term_ascii and not term_chinese:
            continue
        if any(
            token in other or other in token
            for token in value_ascii
            for other in term_ascii
        ):
            return True
        if value_chinese & term_chinese:
            return True
    return False


def _remove_authorized_localization_rows(
    text: str, copy_terms: set[str], row_keys: set[str], *, mutate_keys: bool,
) -> str:
    if not copy_terms:
        return text
    lines = text.splitlines(keepends=True)
    removable: set[int] = set()
    for block in _localization_table_blocks(text):
        for index in block["data_indexes"]:
            line = lines[index]
            key = _row_key(line)
            if not key:
                continue
            linked = _linked_copy_key(line, copy_terms)
            renamed = not mutate_keys and _weakly_renamed_copy_key(key, row_keys)
            if key in row_keys or linked or renamed:
                removable.add(index)
                if mutate_keys:
                    row_keys.add(key)
    return "".join(line for index, line in enumerate(lines) if index not in removable)


def _synchronize_linked_localization_checklists(
    baseline_markdown: str, merged_markdown: str, copy_terms: set[str],
) -> tuple[str, list[str]]:
    """Project an authorized copy-table merge into its frozen text checklist.

    An in-place revision is rebuilt from the baseline. When a baseline fenced
    pure-text block exactly mirrors a localization table, the block is a second
    representation of the same copy checklist. Leaving it at baseline while
    bringing selected rows across creates an internally inconsistent PRD. The
    final table is safe authority here because ``_merge_linked_localization_rows``
    has already rejected or preserved every out-of-scope row.

    This never imports a candidate fenced block. It only updates a baseline
    mirror that the merge can map uniquely to its baseline table and that has
    otherwise stayed baseline-equivalent in the rebuilt document.
    """
    if not copy_terms:
        return merged_markdown, []
    baseline_lines = baseline_markdown.splitlines(keepends=True)
    merged_lines = merged_markdown.splitlines(keepends=True)
    baseline_blocks = _localization_table_blocks(baseline_markdown)
    merged_blocks = _localization_table_blocks(merged_markdown)
    replacements: list[tuple[int, int, list[str]]] = []
    claimed_baseline_tables: set[int] = set()

    for merged_block in merged_blocks:
        merged_indexes = list(merged_block["data_indexes"])
        if not any(_linked_copy_key(merged_lines[int(index)], copy_terms) for index in merged_indexes):
            continue
        checklist = _pure_text_checklist_before_table(merged_lines, int(merged_block["start"]))
        if checklist is None:
            continue
        baseline_index, table_failure = _matching_baseline_localization_table(
            merged_block,
            candidate_lines=merged_lines,
            baseline_blocks=baseline_blocks,
            baseline_lines=baseline_lines,
            copy_terms=copy_terms,
        )
        if table_failure or baseline_index is None or baseline_index in claimed_baseline_tables:
            continue
        claimed_baseline_tables.add(baseline_index)
        baseline_block = baseline_blocks[baseline_index]
        baseline_checklist = _pure_text_checklist_before_table(
            baseline_lines, int(baseline_block["start"]),
        )
        if baseline_checklist is None:
            continue
        baseline_values = _localization_table_copy_values(baseline_lines, baseline_block)
        merged_values = _localization_table_copy_values(merged_lines, merged_block)
        if (
            not baseline_values
            or not merged_values
            or baseline_checklist["values"] != baseline_values
            or checklist["values"] != baseline_checklist["values"]
            or merged_values == baseline_values
        ):
            continue

        newline = "\r\n" if any("\r\n" in line for line in merged_lines) else "\n"
        replacements.append((
            int(checklist["body_start"]),
            int(checklist["body_end"]),
            [f"{value}{newline}" for value in merged_values],
        ))

    for start, end, replacement in sorted(replacements, reverse=True):
        merged_lines[start:end] = replacement
    return "".join(merged_lines), []


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
    # A fenced checklist that exactly mirrors its adjacent localization table
    # is a table-derived representation. Normalize it before removing allowed
    # table rows so a controller-synchronized checklist is not misclassified
    # as an unrelated global rewrite. Non-mirrors remain visible and protected.
    result = _remove_mirrored_localization_checklists(text)
    result = _remove_selected_sections(result, selected_ids)
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


def build_revision_asset_attestation(
    manifest: Mapping[str, Any],
    *,
    candidate_markdown: str,
    candidate_assets: Mapping[str, str],
) -> dict[str, Any]:
    """Describe which selected-section assets exist in this staged workspace.

    Asset provenance is a controller concern: a PRD writer can choose an
    attested reference, but must not be asked to prove where its bytes came
    from.  The attestation deliberately distinguishes immutable baseline bytes
    from files copied from the confirmed input set.  It is generated from the
    actual staged directory, never from an Agent assertion.
    """
    selected = {
        str(item).strip()
        for item in manifest.get("requirement_ids", [])
        if str(item).strip()
    }
    baseline = manifest.get("baseline")
    baseline = baseline if isinstance(baseline, Mapping) else {}
    baseline_assets = baseline.get("assets")
    baseline_assets = {
        str(path): str(digest)
        for path, digest in baseline_assets.items()
    } if isinstance(baseline_assets, Mapping) else {}
    allowed_new = manifest.get("allowed_new_assets")
    allowed_new = {
        str(path): str(digest)
        for path, digest in allowed_new.items()
    } if isinstance(allowed_new, Mapping) else {}
    candidate = {str(path): str(digest) for path, digest in candidate_assets.items()}

    def source_for(path: str) -> tuple[str, str | None]:
        if path in baseline_assets:
            return "baseline", baseline_assets[path]
        if path in allowed_new:
            return "copied_input", allowed_new[path]
        return "unattested", None

    inventory: list[dict[str, Any]] = []
    for path in sorted(set(baseline_assets) | set(allowed_new)):
        origin, expected_digest = source_for(path)
        actual_digest = candidate.get(path)
        inventory.append({
            "path": path,
            "origin": origin,
            "sha256": actual_digest or "",
            "status": (
                "available" if actual_digest == expected_digest
                else "missing" if actual_digest is None
                else "digest_mismatch"
            ),
        })

    sections = requirement_sections(candidate_markdown)
    selected_assets: dict[str, list[dict[str, Any]]] = {}
    missing_required_assets: list[str] = []
    unattested_selected_assets: list[str] = []
    invalid_selected_references: list[str] = []
    for requirement_id in sorted(selected):
        entries: list[dict[str, Any]] = []
        for reference in sections.get(requirement_id, {}).get("image_refs", []):
            path = normalize_image_reference(str(reference))
            if not path.startswith("assets/"):
                invalid_selected_references.append(f"{requirement_id}:{path}")
                entries.append({
                    "path": path,
                    "origin": "invalid",
                    "sha256": "",
                    "status": "invalid_reference",
                })
                continue
            origin, expected_digest = source_for(path)
            actual_digest = candidate.get(path)
            status = (
                "available" if expected_digest is not None and actual_digest == expected_digest
                else "missing" if actual_digest is None
                else "unattested" if expected_digest is None
                else "digest_mismatch"
            )
            entries.append({
                "path": path,
                "origin": origin,
                "sha256": actual_digest or "",
                "status": status,
            })
            if status in {"missing", "digest_mismatch"}:
                missing_required_assets.append(path)
            elif status == "unattested":
                unattested_selected_assets.append(path)
        selected_assets[requirement_id] = entries

    for contract in manifest.get("image_contracts", []):
        if not isinstance(contract, Mapping):
            continue
        for reference in contract.get("required_image_refs", []):
            path = normalize_image_reference(str(reference))
            if path not in candidate:
                missing_required_assets.append(path)

    missing_required_assets = sorted(set(missing_required_assets))
    unattested_selected_assets = sorted(set(unattested_selected_assets))
    invalid_selected_references = sorted(set(invalid_selected_references))
    failures: list[str] = []
    if missing_required_assets:
        failures.append(
            "selected requirement asset is not present with attested bytes in the staged workspace: "
            + ", ".join(missing_required_assets)
        )
    if unattested_selected_assets:
        failures.append(
            "selected requirement references an asset outside the controller-owned inventory: "
            + ", ".join(unattested_selected_assets)
        )
    if invalid_selected_references:
        failures.append(
            "selected requirement image reference must stay under assets/: "
            + ", ".join(invalid_selected_references)
        )
    return {
        "schema_version": 1,
        "status": "passed" if not failures else "failed",
        "available_assets": [entry for entry in inventory if entry["status"] == "available"],
        "selected_requirement_assets": selected_assets,
        "missing_required_assets": missing_required_assets,
        "unattested_selected_assets": unattested_selected_assets,
        "invalid_selected_references": invalid_selected_references,
        "failures": failures,
    }


def _replace_requirement_rows(
    baseline_markdown: str, candidate_markdown: str, selected: set[str],
) -> str:
    """Carry selected list rows into an otherwise baseline-derived document."""
    candidate_rows = requirement_rows(candidate_markdown)
    result = baseline_markdown
    for requirement_id in sorted(selected, key=lambda item: (item.count("."), item), reverse=True):
        row = candidate_rows.get(requirement_id)
        if not row:
            continue
        pattern = re.compile(rf"(?m)^\|\s*{re.escape(requirement_id)}\s*\|.*(?:\n|$)")
        result, _ = pattern.subn(row, result, count=1)
    return result


def _remove_requirement_rows(markdown: str, requirement_ids: set[str]) -> str:
    """Remove only explicitly authorized requirement-list rows."""
    if not requirement_ids:
        return markdown
    pattern = "|".join(re.escape(item) for item in sorted(requirement_ids, key=len, reverse=True))
    return re.sub(rf"(?m)^\|\s*(?:{pattern})\s*\|.*(?:\n|$)", "", markdown)


def _detail_media_cell_analysis(value: str) -> tuple[bool, bool, str | None]:
    """Classify a table value that may contain a ``prd-detail-media`` marker.

    A normal ``需求详情`` value can mix a valid marker with its product prose.
    An auxiliary row is different: after removing one or more valid markers,
    it contains only whitespace and explicit ``<br>`` separators.  This small
    distinction lets the constrained merger fix a structural writer error
    without treating arbitrary prose as disposable layout.
    """
    if not DETAIL_MEDIA_PREFIX_RE.search(value):
        return False, False, None
    markers = list(DETAIL_MEDIA_RE.finditer(value))
    if not markers:
        return True, False, "contains an unterminated prd-detail-media marker"
    for marker in markers:
        attributes = marker.group("attributes").replace("“", '"').replace("”", '"')
        values = {
            match.group("name").casefold(): match.group("value").strip()
            for match in DETAIL_MEDIA_ATTRIBUTE_RE.finditer(attributes)
        }
        missing = [name for name in ("src", "alt", "copy") if not values.get(name)]
        if missing:
            return True, False, (
                "contains a prd-detail-media marker missing required attribute(s): "
                + ", ".join(missing)
            )
    remainder = DETAIL_MEDIA_RE.sub("", value)
    remainder = re.sub(r"<br\s*/?>", "", remainder, flags=re.IGNORECASE)
    return True, not remainder.strip(), None


def _replace_detail_media_value(row: str, value: str) -> str:
    """Replace a validated two-cell row while retaining its line terminator."""
    cells = _table_cells(row)
    assert len(cells) == 2
    if row.endswith("\r\n"):
        ending = "\r\n"
    elif row.endswith("\n"):
        ending = "\n"
    else:
        ending = ""
    return f"| {cells[0]} | {value} |{ending}"


def _normalize_detail_media_table(
    table: Sequence[str], requirement_id: str,
) -> tuple[list[str], list[str]]:
    """Move only unambiguous marker-only rows into one detail cell.

    The renderer intentionally expands source markers only from ``需求详情``.
    A selected-section artifact writer can nevertheless emit a legacy figure,
    screenshot, or duplicate detail row. Labels are not trusted as an
    identity: any two-cell row whose value is exclusively valid markers is an
    auxiliary media row. We transform it only when this table has exactly one
    substantive canonical detail value to receive it.
    """
    media_rows: list[tuple[int, str]] = []
    primary_detail_rows: list[int] = []
    failures: list[str] = []
    for row_index, row in enumerate(table):
        if _table_separator_row(row):
            continue
        cells = _table_cells(row)
        contains_marker = bool(DETAIL_MEDIA_PREFIX_RE.search(row))
        is_header = row_index == 0 and len(table) > 1 and _table_separator_row(table[1])
        if is_header:
            if contains_marker:
                failures.append(
                    f"cannot safely normalize media-only auxiliary row in selected requirement {requirement_id}: "
                    "a marker must not appear in the table header"
                )
            continue
        if len(cells) != 2:
            if contains_marker:
                failures.append(
                    f"cannot safely normalize media-only auxiliary row in selected requirement {requirement_id}: "
                    "a marker row must be a two-cell field/value row"
                )
            continue
        label = re.sub(r"\s+", "", cells[0])
        marker_in_value, media_only, marker_error = _detail_media_cell_analysis(cells[1])
        if contains_marker and not marker_in_value:
            failures.append(
                f"cannot safely normalize media-only auxiliary row in selected requirement {requirement_id}: "
                "the marker must be in the value cell"
            )
            continue
        if marker_error:
            failures.append(
                f"cannot safely normalize media-only auxiliary row in selected requirement {requirement_id}: "
                + marker_error
            )
            continue
        if marker_in_value and media_only:
            media_rows.append((row_index, cells[1].strip()))
            continue
        if label == "需求详情":
            # A canonical detail row can legally contain prose plus one or
            # more media markers. It is the only valid destination for an
            # auxiliary media-only row.
            detail_without_markers = DETAIL_MEDIA_RE.sub("", cells[1])
            detail_without_markers = re.sub(
                r"<br\s*/?>", "", detail_without_markers, flags=re.IGNORECASE,
            )
            if detail_without_markers.strip():
                primary_detail_rows.append(row_index)
        elif marker_in_value:
            failures.append(
                f"cannot safely normalize media-only auxiliary row in selected requirement {requirement_id}: "
                "a non-detail row mixes a media marker with substantive content"
            )

    if not media_rows:
        return list(table), failures
    if failures:
        return list(table), failures
    if not primary_detail_rows:
        return list(table), [
            f"cannot safely normalize media-only auxiliary row in selected requirement {requirement_id}: "
            "the table has no substantive 需求详情 cell"
        ]
    if len(primary_detail_rows) != 1:
        return list(table), [
            f"cannot safely normalize media-only auxiliary row in selected requirement {requirement_id}: "
            "the table has multiple substantive 需求详情 cells"
        ]

    target_index = primary_detail_rows[0]
    target_cells = _table_cells(table[target_index])
    before_target = [value for row_index, value in media_rows if row_index < target_index]
    after_target = [value for row_index, value in media_rows if row_index > target_index]
    # Keep the source sequence even when a writer placed a marker-only row
    # before a detail row that already contains media markers of its own.
    target_value = "<br>".join(before_target + [target_cells[1].rstrip()] + after_target)
    normalized = list(table)
    normalized[target_index] = _replace_detail_media_value(normalized[target_index], target_value)
    for row_index, _ in reversed(media_rows):
        del normalized[row_index]
    return normalized, []


def _normalize_selected_detail_media_rows(
    markdown: str, selected: set[str],
) -> tuple[str, list[str]]:
    """Normalize selected-only media-only table rows or fail closed.

    No table outside an explicitly selected requirement is inspected for a
    rewrite. If one selected table is structurally unsafe, return the original
    candidate unchanged so the caller can reject the entire constrained merge.
    """
    sections = requirement_sections(markdown)
    replacements: list[tuple[int, int, str]] = []
    failures: list[str] = []
    ordered_sections = sorted(
        (
            (requirement_id, section)
            for requirement_id, section in sections.items()
            if requirement_id in selected
        ),
        key=lambda item: int(item[1]["start"]),
    )
    for requirement_id, section in ordered_sections:
        lines = str(section["content"]).splitlines(keepends=True)
        changed = False
        index = 0
        while index < len(lines):
            if not lines[index].lstrip().startswith("|"):
                index += 1
                continue
            table_start = index
            while index < len(lines) and lines[index].lstrip().startswith("|"):
                index += 1
            table_end = index
            normalized_table, table_failures = _normalize_detail_media_table(
                lines[table_start:table_end], requirement_id,
            )
            failures.extend(table_failures)
            if table_failures:
                continue
            if normalized_table != lines[table_start:table_end]:
                lines[table_start:table_end] = normalized_table
                changed = True
                index = table_start + len(normalized_table)
        if changed:
            replacements.append((int(section["start"]), int(section["end"]), "".join(lines)))
    if failures:
        return markdown, failures
    for start, end, replacement in reversed(replacements):
        markdown = markdown[:start] + replacement + markdown[end:]
    return markdown, []


def _append_version_history_rows(baseline_markdown: str, rows: Sequence[str]) -> str:
    if not rows:
        return baseline_markdown
    section = _version_history_section(baseline_markdown)
    if section is None:
        return baseline_markdown
    body = str(section["body"])
    offset = 0
    insertion = None
    for line in body.splitlines(keepends=True):
        offset += len(line)
        if VERSION_RECORD_ROW_RE.match(line):
            insertion = offset
    if insertion is None:
        return baseline_markdown
    appended = "".join(row.rstrip("\r\n") + "\n" for row in rows)
    body = body[:insertion] + appended + body[insertion:]
    return (
        baseline_markdown[:int(section["body_start"])]
        + body
        + baseline_markdown[int(section["end"]):]
    )


def _merge_linked_localization_rows(
    baseline_markdown: str, candidate_markdown: str, copy_terms: set[str],
) -> tuple[str, list[str]]:
    """Carry selected-copy table segments while keeping all other rows intact.

    The source and candidate can use different visible labels for the same
    message.  We pair only recognized localization tables, then anchor a
    segment using the full row (usage location and parameter cells included).
    An adjacent short renamed label can join an already anchored segment, but
    an unanchored table change is retained from the baseline rather than being
    silently authorized.
    """
    if not copy_terms:
        return baseline_markdown, []
    baseline_lines = baseline_markdown.splitlines(keepends=True)
    candidate_lines = candidate_markdown.splitlines(keepends=True)
    baseline_blocks = _localization_table_blocks(baseline_markdown)
    candidate_blocks = _localization_table_blocks(candidate_markdown)
    failures: list[str] = []
    replacements: list[tuple[int, list[str]]] = []
    claimed_baseline_tables: set[int] = set()
    for candidate_block in candidate_blocks:
        candidate_indexes = [
            index for index in candidate_block["data_indexes"]
            if _linked_copy_key(candidate_lines[index], copy_terms)
        ]
        if not candidate_indexes:
            continue
        table_index, table_failure = _matching_baseline_localization_table(
            candidate_block,
            candidate_lines=candidate_lines,
            baseline_blocks=baseline_blocks,
            baseline_lines=baseline_lines,
            copy_terms=copy_terms,
        )
        if table_failure:
            failures.append(table_failure)
            continue
        assert table_index is not None
        if table_index in claimed_baseline_tables:
            failures.append(
                "cannot safely merge linked localization rows because multiple candidate tables map to one baseline table"
            )
            continue
        claimed_baseline_tables.add(table_index)
        baseline_block = baseline_blocks[table_index]
        baseline_indexes = [
            index for index in baseline_block["data_indexes"]
            if _linked_copy_key(baseline_lines[index], copy_terms)
        ]
        candidate_keys = [_row_key(candidate_lines[index]) for index in candidate_indexes]
        if baseline_indexes:
            first = min(baseline_indexes)
            last = max(baseline_indexes)
            # Visible labels such as "失败" may have been expanded to
            # "执行失败". Include only adjacent rows with that direct rename
            # evidence; no semantic guess permits distant table rows.
            for index in (first - 1, last + 1):
                if (
                    index in baseline_block["data_indexes"]
                    and _weakly_renamed_copy_key(_row_key(baseline_lines[index]), candidate_keys)
                ):
                    baseline_indexes.append(index)
        if not baseline_indexes:
            failures.append(
                "cannot safely merge linked localization rows without a baseline row anchor"
            )
            continue
        assignments: dict[int, list[str]] = {}
        last_assignment: int | None = None
        claimed_anchor_indexes: set[int] = set()
        for candidate_index in candidate_indexes:
            candidate_row = candidate_lines[candidate_index]
            scores = [
                (_localization_row_match_score(baseline_lines[index], candidate_row), index)
                for index in baseline_indexes
            ]
            available_scores = [
                item for item in scores
                if item[0] > 0 and item[1] not in claimed_anchor_indexes
            ]
            score = max((item[0] for item in available_scores), default=0)
            best_indexes = [
                index for item_score, index in available_scores
                if item_score == score
            ]
            if score and len(best_indexes) != 1:
                failures.append(
                    "cannot safely merge linked localization row because its baseline row anchor is ambiguous"
                )
                continue
            target_index = best_indexes[0] if best_indexes else -1
            if score == 0:
                # New copy can be inserted beside a preceding anchored row,
                # but never across an unmatched row belonging to another
                # requirement. Before the first anchor it belongs with the
                # first anchored row.
                target_index = last_assignment if last_assignment is not None else min(baseline_indexes)
            else:
                claimed_anchor_indexes.add(target_index)
            assignments.setdefault(target_index, []).append(candidate_row)
            last_assignment = target_index
        replacements.extend(sorted(assignments.items()))
    if failures:
        return baseline_markdown, failures
    if not replacements:
        return baseline_markdown, []
    replacements.sort(key=lambda item: item[0], reverse=True)
    for index, rows in replacements:
        baseline_lines[index:index + 1] = rows
    return "".join(baseline_lines), []


def constrain_revision_markdown(
    manifest: Mapping[str, Any],
    *,
    baseline_markdown: str,
    candidate_markdown: str,
) -> dict[str, Any]:
    """Rebuild a revision from the baseline plus only controller-authorized deltas.

    An Artifact Agent receives a complete staged PRD so it can understand local
    context, but it is not allowed to replace unrelated sections merely because
    it rewrote the whole file.  This constrained merge is deterministic: only
    selected detail sections/list rows, authorized linked-copy rows, and a
    valid append-only version history delta can cross from the candidate into
    the controller's baseline.  It is intentionally a safety recovery, not a
    replacement for the writer contract.
    """
    selected = {
        str(item).strip()
        for item in manifest.get("requirement_ids", [])
        if str(item).strip()
    }
    candidate_markdown, media_normalization_failures = _normalize_selected_detail_media_rows(
        candidate_markdown, selected,
    )
    if media_normalization_failures:
        return {
            "schema_version": 1,
            "status": "failed",
            "markdown": baseline_markdown,
            "failures": media_normalization_failures,
            "preserved": [],
        }
    baseline_sections = requirement_sections(baseline_markdown)
    candidate_sections = requirement_sections(candidate_markdown)
    deleted = {
        str(item).strip()
        for item in manifest.get("deleted_requirement_ids", [])
        if str(item).strip()
    }
    failures: list[str] = []
    unknown_deleted = deleted - selected
    if unknown_deleted:
        failures.append(
            "deletion contract names requirement IDs outside the confirmed revision scope: "
            + ", ".join(sorted(unknown_deleted))
        )
    for requirement_id in sorted(selected):
        if requirement_id not in baseline_sections:
            failures.append(f"selected requirement section {requirement_id} is absent from the baseline")
        elif requirement_id in deleted and requirement_id in candidate_sections:
            failures.append(f"explicitly deleted requirement section {requirement_id} is still present in the candidate")
        elif requirement_id not in deleted and requirement_id not in candidate_sections:
            failures.append(f"selected requirement section {requirement_id} is absent from the candidate")
    if failures:
        return {
            "schema_version": 1,
            "status": "failed",
            "markdown": baseline_markdown,
            "failures": failures,
            "preserved": [],
        }

    result = baseline_markdown
    # Replace slices from the end so offsets remain valid.
    for requirement_id, section in sorted(
        baseline_sections.items(), key=lambda item: int(item[1]["start"]), reverse=True,
    ):
        if requirement_id not in selected:
            continue
        if requirement_id in deleted:
            result = result[:int(section["start"])] + result[int(section["end"]):]
            continue
        candidate = candidate_sections[requirement_id]
        result = (
            result[:int(section["start"])]
            + str(candidate["content"])
            + result[int(section["end"]):]
        )
    result = _remove_requirement_rows(result, deleted)
    result = _replace_requirement_rows(result, candidate_markdown, selected - deleted)

    selected_sections = {
        requirement_id: candidate_sections[requirement_id]
        for requirement_id in selected - deleted
    }
    derivatives = manifest.get("allowed_derivatives")
    derivatives = derivatives if isinstance(derivatives, Mapping) else {}
    if derivatives.get("linked_localization_rows"):
        copy_terms = _selected_copy_terms(selected_sections)
        result, linked_failures = _merge_linked_localization_rows(
            result, candidate_markdown, copy_terms,
        )
        failures.extend(linked_failures)
        if not linked_failures:
            result, checklist_failures = _synchronize_linked_localization_checklists(
                baseline_markdown, result, copy_terms,
            )
            failures.extend(checklist_failures)
    if derivatives.get("append_only_version_history"):
        _, added_rows, history_failures = _version_history_append_only(
            baseline_markdown, candidate_markdown,
        )
        failures.extend(history_failures)
        if not history_failures:
            result = _append_version_history_rows(result, added_rows)
    return {
        "schema_version": 1,
        "status": "merged" if not failures else "failed",
        "markdown": result,
        "failures": failures,
        "preserved": [
            "unselected requirement sections and list rows",
            "unselected document metadata and prose",
            "unselected localization rows",
        ],
    }


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
    deleted = {
        str(item).strip()
        for item in manifest.get("deleted_requirement_ids", [])
        if str(item).strip()
    }
    if not selected:
        failures.append("in-place revision has no confirmed requirement selector")
    if deleted - selected:
        failures.append(
            "deletion contract names requirement IDs outside the confirmed revision scope: "
            + ", ".join(sorted(deleted - selected))
        )

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
    for requirement_id in sorted(selected):
        if requirement_id not in baseline_sections:
            failures.append(f"selected requirement section {requirement_id} is absent from the baseline")
        elif requirement_id in deleted:
            if requirement_id in candidate_sections:
                failures.append(f"explicitly deleted requirement section {requirement_id} is still present")
            if requirement_id in baseline_rows and requirement_id in candidate_rows:
                failures.append(f"explicitly deleted requirement-list row {requirement_id} is still present")
        elif requirement_id not in candidate_sections:
            failures.append(f"selected requirement section {requirement_id} was removed without explicit deletion authorization")
        elif requirement_id in baseline_rows and requirement_id not in candidate_rows:
            failures.append(f"selected requirement-list row {requirement_id} was removed without explicit deletion authorization")
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

    # Asset ownership follows the revision boundary.  A replaced screenshot
    # may be removed when it is only used by a selected requirement; assets
    # still referenced by an unselected requirement remain compare-and-swap
    # protected.  The previous implementation protected the entire asset tree,
    # making the ordinary "replace old figure with new figure" operation fail.
    protected_baseline_text = _outer_markdown(
        baseline_markdown, selected, allow_linked_copy=False,
        copy_terms=set(), row_keys=set(), discover_rows=False,
    )
    protected_asset_refs = set(markdown_image_refs(protected_baseline_text))
    for path, digest in baseline_assets.items():
        candidate_digest = candidate_assets.get(path)
        if candidate_digest is None:
            if path in protected_asset_refs:
                failures.append(f"protected asset changed or was removed: {path}")
            continue
        if candidate_digest != digest:
            failures.append(f"protected asset changed or was removed: {path}")
    for path, digest in candidate_assets.items():
        if path not in baseline_assets and allowed_new.get(path) != digest:
            failures.append(f"unconfirmed asset was added: {path}")

    asset_attestation = build_revision_asset_attestation(
        manifest,
        candidate_markdown=candidate_markdown,
        candidate_assets=candidate_assets,
    )
    failures.extend(asset_attestation["failures"])

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
        "asset_attestation": asset_attestation,
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
