from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import (
    DisabledSummarizer,
    ManualSummarizer,
    OptionalAIAdapter,
    create_inbox_note,
    extract_source,
    generate_progress_report,
    initialize_vault,
    load_protected_patterns,
    review_note,
    validate_vault,
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
    review.add_argument("--mark", action="append", choices=("summary", "classification", "action", "links", "destination"), default=[])

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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
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
        output = create_inbox_note(
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
    errors = validate_vault(args.vault)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
