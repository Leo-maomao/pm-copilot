"""Discover and rank user-provided model capabilities without vendor assumptions."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModelOption:
    model: str | None
    provider: str
    capabilities: frozenset[str]
    source: str
    quality_rank: int = 0


@dataclass(frozen=True)
class ModelSelection:
    option: ModelOption | None
    status: str
    reason: str
    requirement: str
    explicit_override: bool = False


def _normalise_option(value: Any, provider: str, source: str) -> ModelOption | None:
    if isinstance(value, str):
        return ModelOption(value.strip() or None, provider, frozenset({"standard"}), source)
    if not isinstance(value, dict):
        return None
    model = str(value.get("model", "")).strip() or None
    item_provider = str(value.get("provider", provider)).strip() or provider
    raw_capabilities = value.get("capabilities", ["standard"])
    if isinstance(raw_capabilities, str):
        raw_capabilities = [raw_capabilities]
    capabilities = frozenset(str(item).strip().lower() for item in raw_capabilities if str(item).strip())
    return ModelOption(
        model, item_provider, capabilities or frozenset({"standard"}), source,
        int(value.get("quality_rank", 0) or 0),
    )


def _env_options(provider: str) -> tuple[list[ModelOption], list[str]]:
    options: list[ModelOption] = []
    warnings: list[str] = []
    raw_catalog = os.environ.get("PM_COPILOT_MODEL_CATALOG", "").strip()
    if raw_catalog:
        try:
            parsed = json.loads(raw_catalog)
            values = parsed if isinstance(parsed, list) else parsed.get("models", [])
            if not isinstance(values, list):
                raise ValueError("models must be a list")
            options.extend(
                item for item in (_normalise_option(value, provider, "env:PM_COPILOT_MODEL_CATALOG") for value in values)
                if item is not None and item.provider == provider
            )
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            warnings.append(f"invalid PM_COPILOT_MODEL_CATALOG: {error}")
    raw_models = os.environ.get("PM_COPILOT_MODELS", "").strip()
    if raw_models:
        options.extend(
            item for item in (_normalise_option(value, provider, "env:PM_COPILOT_MODELS") for value in raw_models.split(","))
            if item is not None
        )
    return options, warnings


def _configured_model(provider: str, cwd: Path | None = None) -> ModelOption | None:
    if provider == "claude":
        # Claude CLI exposes its authenticated default at execution time rather
        # than through a local model-list command. It remains degraded until
        # the structured response proves the actual model identifier.
        return ModelOption(None, provider, frozenset({"configured_default"}), "provider-default")
    if provider != "codex":
        return None
    codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()
    config = codex_home / "config.toml"
    try:
        text = config.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r"(?m)^\s*model\s*=\s*[\"']([^\"']+)[\"']\s*$", text)
    if not match:
        return ModelOption(None, provider, frozenset({"configured_default"}), "provider-config")
    return ModelOption(match.group(1), provider, frozenset({"standard", "configured_default"}), "provider-config")


def _seawork_options() -> tuple[list[ModelOption], list[str]]:
    """Read locally available Seawork providers and models without inventing IDs."""
    executable = shutil.which("seawork")
    if executable is None:
        return [], ["seawork executable not found for runtime model discovery"]
    try:
        listed = subprocess.run(
            [executable, "provider", "ls", "--json"], text=True, capture_output=True, timeout=5, check=False,
        )
        providers = json.loads(listed.stdout) if listed.returncode == 0 else []
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        return [], [f"seawork provider discovery failed: {error}"]
    options: list[ModelOption] = []
    warnings: list[str] = []
    for provider in providers if isinstance(providers, list) else []:
        if not isinstance(provider, dict):
            continue
        provider_id = str(provider.get("provider", "")).strip()
        if not provider_id or str(provider.get("status", "")).lower() != "available":
            continue
        try:
            result = subprocess.run(
                [executable, "provider", "models", provider_id, "--json"], text=True, capture_output=True, timeout=5, check=False,
            )
            models = json.loads(result.stdout) if result.returncode == 0 else []
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
            warnings.append(f"seawork model discovery failed for {provider_id}: {error}")
            continue
        for item in models if isinstance(models, list) else []:
            if not isinstance(item, dict):
                continue
            model_id = str(item.get("id", "")).strip()
            if not model_id:
                continue
            thinking = item.get("thinkingOptionIds", [])
            if isinstance(thinking, str):
                thinking = [thinking]
            capabilities = {"standard"}
            if any(str(level).lower() in {"high", "xhigh", "max", "ultra"} for level in thinking):
                capabilities.add("judgment")
            options.append(ModelOption(
                f"{provider_id}/{model_id}", "seawork", frozenset(capabilities),
                "seawork-provider-discovery", len(thinking),
            ))
    return options, warnings


def discover_model_catalog(provider: str, cwd: Path | None = None, explicit_model: str | None = None) -> tuple[list[ModelOption], list[str]]:
    """Return only user-declared/configured models; never invent model IDs."""
    options, warnings = _env_options(provider)
    configured = _configured_model(provider, cwd)
    if configured is not None:
        options.append(configured)
    if provider == "seawork":
        discovered, discovered_warnings = _seawork_options()
        options.extend(discovered)
        warnings.extend(discovered_warnings)
    if explicit_model:
        explicit = _normalise_option(explicit_model, provider, "explicit-operator")
        if explicit is not None:
            options.insert(0, explicit)
    deduped: dict[tuple[str | None, str], ModelOption] = {}
    for option in options:
        deduped.setdefault((option.model, option.provider), option)
    return list(deduped.values()), warnings


def select_model(
    requirement: str, provider: str, options: list[ModelOption], explicit_model: str | None = None,
) -> ModelSelection:
    """Select by declared capability, with an explicit degraded/blocked result."""
    if explicit_model:
        match = next((item for item in options if item.model == explicit_model), None)
        if match is not None:
            return ModelSelection(match, "selected", "explicit operator model override", requirement, True)
        return ModelSelection(
            ModelOption(explicit_model, provider, frozenset(), "explicit-operator-unverified"),
            "unverified",
            "explicit model was supplied but no local capability manifest confirms it",
            requirement,
            True,
        )
    required = "judgment" if requirement in {"judgment", "repair"} else "standard"
    candidates = [item for item in options if item.provider == provider and item.model]
    capable = [item for item in candidates if required in item.capabilities]
    if capable:
        chosen = max(capable, key=lambda item: item.quality_rank)
        return ModelSelection(chosen, "selected", f"declared {required} capability", requirement)
    configured_default = next((item for item in options if "configured_default" in item.capabilities), None)
    if configured_default is not None:
        return ModelSelection(
            configured_default, "degraded",
            f"no declared {required} model; using the provider-configured default",
            requirement,
        )
    if candidates and required == "judgment":
        chosen = max(candidates, key=lambda item: item.quality_rank)
        return ModelSelection(
            chosen, "degraded",
            "no declared judgment model; using the highest-ranked available model",
            requirement,
        )
    return ModelSelection(None, "blocked", f"no available model declares the required {required} capability", requirement)


__all__ = ["ModelOption", "ModelSelection", "discover_model_catalog", "select_model"]
