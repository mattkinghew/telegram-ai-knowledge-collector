"""Deterministic Markdown builder with explicit evidence layers."""

from __future__ import annotations

import json
from datetime import date
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

    if result and request.record_type != "free":
        return _build_record_template(request, result)

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


def _items(result: ProviderResult, name: str) -> list[str]:
    return result.sections.get(name, [])


def _bullets(items: list[str]) -> list[str]:
    return ["- " + item for item in items] or ["- (none recorded)"]


def _checkbox(value: str) -> str:
    lowered = value.casefold().strip()
    checked = lowered.endswith(": true") or lowered.endswith(": x") or lowered.startswith("[x]")
    return "[x]" if checked else "[ ]"


def _build_record_template(request: CaptureRequest, result: ProviderResult) -> str:
    """Render allow-listed record templates from validated provider sections."""
    title = result.title
    lines = ["---", 'schema_version: "1"', f"record_type: {request.record_type}", "ai_status: suggested", "---", ""]
    if request.record_type == "daily_control":
        lines += [f"# 每日控制台：{date.today().isoformat()}", "", "## 🚨 系統防呆檢查 (System Check)", ""]
        for label, text in (("設備同步完成", "sync_completed"), ("`00_Inbox` 已整理", "inbox_cleared")):
            value = next((item for item in _items(result, "system_check") if item.startswith(text + ":")), "")
            lines.append(f"- {_checkbox(value)} {label}")
        lines += ["", "## 🎯 今日時間箱 (Timeboxing)", ""]
        labels = {"ai_learning": "AI 學習", "msc": "MSc 課程", "side_work": "副業 / NGO / 工作"}
        entries = {item.split(":", 1)[0]: item for item in _items(result, "timeboxes") if ":" in item}
        for key, label in labels.items():
            raw = entries.get(key, "")
            fields = dict(part.split("=", 1) for part in raw.split("; ")[1:] if "=" in part)
            lines += [f"### [{label}]", f"- 任務：{fields.get('task', '')}", f"- 目標輸出：{fields.get('target_output', '')}", f"- 目前狀態：{fields.get('status', '')}", f"- 下一步：{fields.get('next_action', '')}", ""]
        lines += ["## 🎙️ 微習慣追蹤 (Micro-habits)", ""]
        for label, key in (("英文口語錄製 5 分鐘", "english_5min"), ("AI Agent / Cloud 課程 15 分鐘", "ai_cloud_15min")):
            value = next((item for item in _items(result, "micro_habits") if item.startswith(key + ":")), "")
            lines.append(f"- {_checkbox(value)} {label}")
        lines += ["", "## ✅ 今日完成", ""] + _bullets(_items(result, "completed")) + ["", "## 🔄 進行中", ""] + _bullets(_items(result, "in_progress")) + ["", "## ➡️ 下一步", ""] + _bullets(_items(result, "next_actions"))
        lines += ["", "## 🚧 覆盤與阻力紀錄", ""]
        friction = dict(item.split(":", 1) for item in _items(result, "friction") if ":" in item)
        for heading, key in (("今日卡點", "blocker"), ("原因", "cause"), ("修正策略", "strategy"), ("明日避免再次出現的方法", "prevention")):
            lines += [f"### {heading}", friction.get(key, ""), ""]
        lines += ["## 💡 今日洞察 / 新知識", ""] + _bullets(_items(result, "insights")) + ["", "## ⚠️ 待確認事項", ""] + _bullets(_items(result, "facts_to_verify"))
    else:
        lines += [f"# {title}", ""]
        headings = {
            "work_log": [("已完成", "completed"), ("進行中", "in_progress"), ("下一步", "next_actions"), ("阻礙", "blockers"), ("決策", "decisions"), ("待確認事項", "facts_to_verify")],
            "reflection": [("發生了什麼", "what_happened"), ("做得好的地方", "what_went_well"), ("可以改善的地方", "what_could_improve"), ("學到的事", "lesson"), ("下一個實驗", "next_experiment"), ("待確認事項", "facts_to_verify")],
            "todo": [("任務", "tasks"), ("明確提及的日期", "due_dates_explicit_only"), ("依賴", "dependencies"), ("待確認事項", "facts_to_verify")],
            "meeting_followup": [("重點", "key_points"), ("決策", "decisions"), ("行動項目", "action_items"), ("明確提及的負責人", "owners_explicit_only"), ("待決問題", "open_questions"), ("跟進", "follow_up"), ("待確認事項", "facts_to_verify")],
        }[request.record_type]
        for heading, key in headings:
            lines += [f"## {heading}", ""] + _bullets(_items(result, key)) + [""]
    lines += ["## 📝 原始語音記錄", "", request.raw_content, ""]
    return "\n".join(lines).rstrip() + "\n"
