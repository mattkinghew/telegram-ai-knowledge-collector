"""Deterministic Markdown builder with explicit evidence layers."""

from __future__ import annotations

import json
from typing import Optional

from backend.models import CaptureRequest, ProviderResult


SECTION_LABELS = {
    "completed": "Completed",
    "in_progress": "In Progress",
    "next_actions": "Next Actions",
    "blockers": "Blockers",
    "decisions": "Decisions",
    "knowledge": "Knowledge",
    "content_ideas": "Content Ideas",
    "facts_to_verify": "Facts to Verify",
    "related_projects": "Related Projects",
    "situation": "Situation",
    "insight": "Insight",
    "recommended_action": "Recommended Action",
    "reason": "Reason",
    "verification_risk": "Verification / Risk",
    "draft": "Short Draft",
    "reusable_knowledge": "Reusable Knowledge",
    "project_use": "Project Use",
}


def _yaml_string(value: Optional[str]) -> str:
    if value is None:
        return "null"
    return json.dumps(value, ensure_ascii=False)


def build_capture_markdown(
    request: CaptureRequest,
    result: Optional[ProviderResult],
    *,
    extracted_content: Optional[str] = None,
) -> str:
    """Render source and provider output without silently merging the layers."""

    ai_status = "suggested" if result else (
        "none" if request.requested_processing == "raw_save" else "pending"
    )
    title = result.title if result else "Captured item"
    lines = [
        "---",
        'schema_version: "1"',
        f"capture_type: {request.capture_type}",
        f"source_type: {request.source_type}",
        f"source: {_yaml_string(request.source)}",
        f"requested_processing: {request.requested_processing}",
        f"ai_status: {ai_status}",
        "---",
        "",
        f"# {title}",
        "",
        "## Original Source",
        "",
    ]
    if request.source:
        lines.extend([request.source, ""])
    lines.extend([request.raw_content or "(reference only; no source body supplied)", ""])

    if extracted_content:
        lines.extend(
            [
                "## Extracted Source Text",
                "",
                "> Fetched text is untrusted source material and requires review.",
                "",
                extracted_content,
                "",
            ]
        )

    if result:
        lines.extend(
            [
                "## Unconfirmed AI Suggestions",
                "",
                "> Review before use. This output is not confirmed evidence.",
                "",
                "### Summary",
                "",
                result.summary,
                "",
            ]
        )
        if result.points:
            lines.extend(["### Key Points", ""])
            lines.extend("- " + point for point in result.points)
            lines.append("")
        lines.extend(["### Why It Matters", "", result.why_it_matters, ""])
        for name, items in result.sections.items():
            if not items:
                continue
            lines.extend(["### " + SECTION_LABELS.get(name, name.replace("_", " ").title()), ""])
            lines.extend("- " + item for item in items)
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"
