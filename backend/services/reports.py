"""Human-selected, preview-only progress report builder."""

from __future__ import annotations

from typing import Iterable

from backend.storage.sqlite import CaptureRecord


def build_report_preview(
    report_type: str,
    period: str,
    records: Iterable[CaptureRecord],
) -> str:
    heading = "Daily Progress Report" if report_type == "daily" else "Period / Project Progress Report"
    lines = ["# " + heading, "", "Period: " + period, "", "## Selected Records", ""]
    for record in records:
        lines.extend(
            [
                "### " + record.title,
                "",
                "- Capture ID: " + record.capture_id,
                "- Status: " + record.status,
                "- Project: " + (record.assigned_project or "Unassigned"),
                "- Processing: " + record.requested_processing,
                "",
                "#### Evidence",
                "",
                record.raw_content or record.source or "(reference only)",
                "",
            ]
        )
    lines.extend(
        [
            "## Human Review",
            "",
            "- [ ] Verify every selected record.",
            "- [ ] Edit the preview before any manual sharing.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"
