from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from .core import (
    DisabledSummarizer,
    ManualSummarizer,
    OptionalAIAdapter,
    ProtectedPathError,
    UnsafePathError,
    VaultStructureError,
    capture_inbox_note,
    extract_source,
    generate_progress_report,
    initialize_vault,
    load_protected_patterns,
    review_note,
    validate_vault,
)
from .search import (
    DUPLICATE_STATUSES,
    SEARCH_SORTS,
    SOURCE_TYPES,
    InboxSearchQuery,
    format_search_diagnostics,
    format_search_json,
    format_search_text,
    parse_filter_date,
    search_inbox,
)


def _path(value: str) -> Path:
    return Path(value).expanduser()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bkc", description="Protected-path-aware Obsidian knowledge capture and reporting.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("--vault", required=True, type=_path)
    init.add_argument("--project-root", default="")

    capture = subparsers.add_parser("capture")
    capture.add_argument("--vault", required=True, type=_path)
    source = capture.add_mutually_exclusive_group(required=True)
    source.add_argument("--text")
    source.add_argument("--url")
    source.add_argument("--file")
    capture.add_argument("--title", default="")
    capture.add_argument("--external-file-link", default="")
    capture.add_argument("--fetch-url", action="store_true")
    capture.add_argument("--summarizer", choices=("manual", "disabled", "optional-ai-disabled"), default="disabled")
    capture.add_argument("--manual-summary", default="")
    capture.add_argument("--action-required", default="")
    capture.add_argument("--deadline", default="")
    capture.add_argument("--related-project", default="")
    capture.add_argument("--related-area", default="")

    review = subparsers.add_parser("review")
    review.add_argument("--vault", required=True, type=_path)
    review.add_argument("--note", required=True, type=_path)
    review.add_argument("--category", choices=("重要知識", "次要知識", "資源", "其他"), default="")
    review.add_argument("--action-required", default="")
    review.add_argument("--related-project", default="")
    review.add_argument("--related-area", default="")
    review.add_argument("--destination", default="")
    review.add_argument("--mark", action="append", choices=("summary", "classification", "action", "links", "destination", "duplicate"), default=[])

    report = subparsers.add_parser("report")
    report.add_argument("--vault", required=True, type=_path)
    report.add_argument("--type", required=True, choices=("daily", "weekly"))
    report.add_argument("--period", required=True)
    report.add_argument("--completed", action="append", type=_path, default=[])
    report.add_argument("--in-progress", action="append", type=_path, default=[])
    report.add_argument("--blocker", action="append", default=[])
    report.add_argument("--commitment", action="append", default=[])
    report.add_argument("--project-root", default="")

    validate = subparsers.add_parser("validate")
    validate.add_argument("--vault", required=True, type=_path)

    search = subparsers.add_parser("search")
    search.add_argument("--vault", required=True, type=_path)
    search.add_argument("--title", default="")
    search.add_argument("--query", default="")
    search.add_argument("--category", action="append", choices=("重要知識", "次要知識", "資源", "其他"), default=[])
    search.add_argument("--created-from", default="")
    search.add_argument("--created-to", default="")
    search.add_argument("--deadline-from", default="")
    search.add_argument("--deadline-to", default="")
    deadline_presence = search.add_mutually_exclusive_group()
    deadline_presence.add_argument("--has-deadline", action="store_true")
    deadline_presence.add_argument("--missing-deadline", action="store_true")
    search.add_argument("--related-project", default="")
    search.add_argument("--related-area", default="")
    search.add_argument("--source-type", action="append", choices=SOURCE_TYPES, default=[])
    search.add_argument("--file-type", action="append", default=[])
    search.add_argument("--processing-status", action="append", default=[])
    search.add_argument("--duplicate-status", action="append", choices=DUPLICATE_STATUSES, default=[])
    action_presence = search.add_mutually_exclusive_group()
    action_presence.add_argument("--has-action", action="store_true")
    action_presence.add_argument("--missing-action", action="store_true")
    search.add_argument("--sort", choices=SEARCH_SORTS, default="created-desc")
    search.add_argument("--limit", type=int, default=50)
    search.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def _run(args: argparse.Namespace) -> int:
    if args.command == "init":
        print(json.dumps(initialize_vault(args.vault, args.project_root), ensure_ascii=False, indent=2))
        return 0
    if args.command == "capture":
        source = extract_source(
            vault=args.vault,
            patterns=load_protected_patterns(args.vault),
            text=args.text or "",
            url=args.url or "",
            file_path=args.file or "",
            external_file_link=args.external_file_link,
            fetch_url=args.fetch_url,
        )
        summarizers = {"disabled": DisabledSummarizer(), "manual": ManualSummarizer(), "optional-ai-disabled": OptionalAIAdapter()}
        output, duplicate = capture_inbox_note(
            vault=args.vault,
            source=source,
            title=args.title,
            summarizer=summarizers[args.summarizer],
            manual_summary=args.manual_summary,
            action_required=args.action_required,
            deadline=args.deadline,
            related_project=args.related_project,
            related_area=args.related_area,
        )
        print(output)
        if duplicate.status == "exact_duplicate_suggested":
            print("WARNING: Exact duplicate suggested.", file=sys.stderr)
            print(f"Match type: {duplicate.match_type}", file=sys.stderr)
            print(f"Existing notes: {duplicate.match_count}", file=sys.stderr)
            if duplicate.matches:
                safe_matches = " ".join(", ".join(duplicate.matches).replace("\r", "\n").splitlines())
                print(f"Matches: {safe_matches}", file=sys.stderr)
        elif duplicate.status == "check_unavailable":
            print("WARNING: Duplicate check unavailable.", file=sys.stderr)
        for diagnostic in duplicate.diagnostics:
            print(f"WARNING: {diagnostic}", file=sys.stderr)
        return 0
    if args.command == "review":
        output = review_note(
            vault=args.vault,
            note_path=args.note,
            category=args.category,
            action_required=args.action_required,
            related_project=args.related_project,
            related_area=args.related_area,
            destination=args.destination,
            mark=args.mark,
        )
        print(output)
        return 0
    if args.command == "report":
        output = generate_progress_report(
            vault=args.vault,
            completed_paths=args.completed,
            in_progress_paths=args.in_progress,
            period_label=args.period,
            report_type=args.type,
            project_root=args.project_root,
            blockers=args.blocker,
            commitments=args.commitment,
        )
        print(output)
        return 0
    if args.command == "search":
        query = InboxSearchQuery(
            title=args.title,
            keyword=args.query,
            categories=tuple(args.category),
            created_from=parse_filter_date(args.created_from, "--created-from"),
            created_to=parse_filter_date(args.created_to, "--created-to"),
            deadline_from=parse_filter_date(args.deadline_from, "--deadline-from"),
            deadline_to=parse_filter_date(args.deadline_to, "--deadline-to"),
            related_project=args.related_project,
            related_area=args.related_area,
            source_types=tuple(args.source_type),
            file_types=tuple(args.file_type),
            processing_statuses=tuple(args.processing_status),
            duplicate_statuses=tuple(args.duplicate_status),
            has_deadline=args.has_deadline,
            missing_deadline=args.missing_deadline,
            has_action=args.has_action,
            missing_action=args.missing_action,
            sort=args.sort,
            limit=args.limit,
        )
        result = search_inbox(vault=args.vault, query=query)
        print(format_search_json(result) if args.format == "json" else format_search_text(result))
        for diagnostic in format_search_diagnostics(result):
            print(f"WARNING: {diagnostic}", file=sys.stderr)
        return 0
    errors = validate_vault(args.vault)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Validation passed.")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return _run(args)
    except (ProtectedPathError, UnsafePathError, VaultStructureError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
