#!/usr/bin/env python3
"""Check repository-only travel setup evidence without Vault or network access."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

try:
    from tools.validate_private_config_example import (
        PrivateConfigValidationError,
        validate_private_config,
    )
except ModuleNotFoundError:  # Direct ``python3 tools/...`` execution.
    from validate_private_config_example import (  # type: ignore[no-redef]
        PrivateConfigValidationError,
        validate_private_config,
    )


REQUIRED_FILES = (
    "config/private-values.example.json",
    "docs/SHORTCUT_BUILD_SHEET_KNOWLEDGE_CAPTURE.md",
    "docs/SHORTCUT_BUILD_SHEET_PROJECT_UPDATE.md",
    "docs/SHORTCUT_BUILD_SHEET_VOICE_CAPTURE.md",
    "docs/P1_4_SIMPLIFIED_MOBILE_PRODUCT_DECISION.md",
    "docs/SHORTCUT_BUILD_SHEET_VOICE_FLASH_V2.md",
    "docs/SHORTCUT_BUILD_SHEET_CONTENT_CAPTURE_V2.md",
    "docs/P1_4_OFFLINE_BEHAVIOR.md",
    "docs/PENDING_ENRICHMENT_CONTRACT_V1.md",
    "docs/P1_4_TWO_SHORTCUT_DEVICE_ACCEPTANCE.md",
    "docs/VOICE_CAPTURE_CONTRACT_V1.md",
    "docs/VOICE_CAPTURE_DEVICE_ACCEPTANCE.md",
    "docs/PRIVATE_VALUES_SETUP.md",
    "docs/TRAVEL_E2E_ACCEPTANCE.md",
    "docs/MAKE_GEMINI_TRAVEL_SETUP_CHECKLIST.md",
    "docs/MAKE_GEMINI_FIELD_MAPPING_WORKSHEET.md",
    "docs/SHORTCUT_AI_PREVIEW_FORMAT.md",
    "docs/ACTIVE_PROJECTS_MOBILE_SETUP.md",
    "docs/CURRENT_DOCS_MAP.md",
    "docs/MANUAL_ONLY_WORK_MATRIX.md",
    "docs/TRAVEL_QUICK_START.md",
    "schemas/mobile-insight-request-v3.schema.json",
    "schemas/mobile-insight-response-v3.schema.json",
    "schemas/voice-capture-request-v1.schema.json",
    "schemas/voice-capture-response-v1.schema.json",
    "tools/mobile_capture_reference.py",
    "tools/mobile_enrichment_simulator.py",
    "tools/mobile_progress_report.py",
    "tools/project_dashboard_reference.py",
    "tools/voice_capture_reference.py",
    "tools/voice_capture_simulator.py",
    "tools/two_entry_capture_reference.py",
    "templates/universal-voice-capture-v1.md",
    "prompts/gemini-voice-structured-capture-v1.md",
    "samples/travel_ai_requests/summary.json",
    "samples/travel_ai_requests/recommendation.json",
    "samples/travel_ai_requests/short_article.json",
    "samples/travel_ai_requests/project_knowledge.json",
    "samples/travel_ai_requests/task.json",
    "samples/travel_ai_requests/decision.json",
    "samples/travel_ai_requests/learning_note.json",
    "samples/travel_ai_responses/summary.json",
    "samples/travel_ai_responses/recommendation.json",
    "samples/travel_ai_responses/short_article.json",
    "samples/travel_ai_responses/project_knowledge.json",
    "samples/travel_ai_responses/task.json",
    "samples/travel_ai_responses/decision.json",
    "samples/travel_ai_responses/learning_note.json",
    "samples/travel_ai_responses/ai_unavailable.json",
    "samples/travel_ai_responses/timeout.json",
    "samples/travel_ai_responses/invalid_json_reference.md",
    "samples/travel_ai_responses/schema_mismatch.json",
    "samples/travel_project_updates/morning-update.md",
    "samples/travel_project_updates/afternoon-update.md",
    "samples/travel_project_updates/evening-update.md",
    "samples/travel_reports/daily-report.md",
    "samples/travel_reports/weekly-report.md",
)
REFERENCE_TOOLS = (
    "tools/mobile_capture_reference.py",
    "tools/mobile_enrichment_simulator.py",
    "tools/mobile_progress_report.py",
    "tools/project_dashboard_reference.py",
    "tools/voice_capture_reference.py",
    "tools/voice_capture_simulator.py",
    "tools/two_entry_capture_reference.py",
)
MANUAL_ONLY_PENDING = (
    "Voice Flash Shortcut",
    "Content Capture Shortcut",
    "Remotely Save",
    "Make/Gemini",
    "P1.4 device acceptance",
)
REAL_MAKE_WEBHOOK = re.compile(
    r"https://hook\.[A-Za-z0-9.-]*make\.com/[A-Za-z0-9_-]{12,}"
)
REAL_VAULT_PATH = re.compile(
    r"/(?:Users|home)/[^/\s]+/(?:[^\s`'\"]+/){0,8}"
    r"(?:Business[_ -]?Knowledge|Matt[_ -]?Space|\.obsidian)(?:/[^\s`'\"]*)?",
    re.IGNORECASE,
)
PROTECTED_REPOSITORY_PARTS = frozenset(
    {
        ".obsidian",
        "private",
        "credentials",
        "25_self_management",
    }
)


@dataclass(frozen=True)
class ReadinessResult:
    passed: bool
    failures: tuple[str, ...]
    manual_only_pending: tuple[str, ...] = MANUAL_ONLY_PENDING


def _repository_files(root: Path) -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=str(root),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        return []
    return [Path(value) for value in completed.stdout.decode("utf-8").split("\0") if value]


def _load_json(path: Path, failures: list[str]) -> Optional[object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        failures.append(f"Invalid JSON: {path.name}: {exc}")
        return None


def is_repository_path_excluded(relative: Path) -> bool:
    """Return True before metadata access for protected repository paths."""

    lowered_parts = {part.lower() for part in relative.parts}
    return bool(
        lowered_parts & PROTECTED_REPOSITORY_PARTS
        or any(part.lower().startswith(".env") for part in relative.parts)
    )


def _check_import(path: Path, failures: list[str]) -> None:
    module_name = f"travel_readiness_{path.stem}"
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError("module specification unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as exc:  # Import failures need a bounded repository diagnostic.
        failures.append(f"Reference tool import failed: {path.name}: {exc}")


def _check_privacy(root: Path, files: Iterable[Path], failures: list[str]) -> None:
    for relative in files:
        if is_repository_path_excluded(relative):
            continue
        path = root / relative
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if REAL_MAKE_WEBHOOK.search(text):
            failures.append(f"Possible real webhook URL in repository file: {relative}")
        if REAL_VAULT_PATH.search(text):
            failures.append(f"Possible real Vault path in repository file: {relative}")


def check_repository(
    root: Path,
    *,
    tracked_files: Optional[Sequence[Path]] = None,
) -> ReadinessResult:
    """Return repository readiness; never inspect a Vault or call the network."""

    root = root.resolve()
    failures: list[str] = []
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            failures.append(f"Missing required repository file: {relative}")

    for path in sorted((root / "schemas").glob("*.json")) if (root / "schemas").is_dir() else ():
        _load_json(path, failures)
    for path in sorted((root / "samples").rglob("*.json")) if (root / "samples").is_dir() else ():
        _load_json(path, failures)

    fixture_paths = sorted((root / "tests" / "fixtures" / "travel_ai").glob("*.json"))
    if len(fixture_paths) != 12:
        failures.append("Travel AI fixture pack must contain 12 JSON files")
    voice_fixture_paths = sorted(
        (root / "tests" / "fixtures" / "voice_capture").glob("*.json")
    )
    if len(voice_fixture_paths) != 14:
        failures.append("Voice capture fixture pack must contain 14 JSON files")
    if not list((root / "tests").glob("test*.py")):
        failures.append("No unit tests are available")

    for relative in REFERENCE_TOOLS:
        path = root / relative
        if path.is_file():
            _check_import(path, failures)

    config_path = root / "config" / "private-values.example.json"
    if config_path.is_file():
        payload = _load_json(config_path, failures)
        if payload is not None:
            try:
                validate_private_config(payload)  # type: ignore[arg-type]
            except (PrivateConfigValidationError, TypeError) as exc:
                failures.append(f"Private config placeholder check failed: {exc}")

    files = list(tracked_files) if tracked_files is not None else _repository_files(root)
    if tracked_files is None and not files:
        failures.append("Unable to enumerate repository files with git")
    _check_privacy(root, files, failures)
    return ReadinessResult(passed=not failures, failures=tuple(failures))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repository root; defaults to this script's repository",
    )
    args = parser.parse_args(argv)
    result = check_repository(args.repo)
    print(f"Repository readiness: {'PASS' if result.passed else 'FAIL'}")
    for failure in result.failures:
        print(f"- {failure}")
    print("Manual-only pending:")
    for item in result.manual_only_pending:
        print(f"- {item}")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
