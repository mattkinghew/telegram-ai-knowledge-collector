"""Deterministic provider used by all normal tests and local demos."""

from __future__ import annotations

from backend.models import CaptureRequest, ProviderResult


class MockProvider:
    def process(self, request: CaptureRequest) -> ProviderResult:
        mode = request.requested_processing
        if mode == "raw_save":
            raise ValueError("raw_save must not call an AI provider")
        if mode == "voice_structure":
            sections = {
                "completed": ["Recorded the fictional completed item."],
                "in_progress": ["Continue the fictional work."],
                "next_actions": ["Verify the result before acting."],
                "blockers": [],
                "decisions": [],
                "knowledge": ["Raw evidence remains separate from suggestions."],
                "content_ideas": [],
                "facts_to_verify": ["Confirm this mock result with real evidence."],
                "related_projects": list(request.allowed_projects[:3]),
            }
            summary = "A fictional voice capture was structured for review."
        elif mode == "recommendation":
            sections = {
                "situation": ["A fictional capture needs human review."],
                "insight": ["Keeping evidence separate reduces accidental overclaiming."],
                "recommended_action": ["Review the raw source before using the suggestion."],
                "reason": ["The provider output is unconfirmed."],
                "verification_risk": ["Check source accuracy and project fit."],
            }
            summary = "Review the evidence before applying this fictional recommendation."
        elif mode == "short_article":
            sections = {
                "draft": [
                    "AI draft: This fictional short article shows how a bounded capture can become a reviewable draft while the original source stays visible. A human should verify every claim before reuse or publication."
                ]
            }
            summary = "A bounded fictional short draft is ready for review."
        elif mode == "project_knowledge":
            sections = {
                "reusable_knowledge": ["Keep raw evidence and derived guidance separate."],
                "project_use": ["Apply only after a human assigns the correct project."],
                "facts_to_verify": ["Confirm the source and current project context."],
            }
            summary = "Reusable fictional project knowledge was prepared for review."
        else:
            sections = {}
            summary = "A fictional source was summarized for review."
        return ProviderResult(
            processing_mode=mode,
            title="Fictional capture",
            summary=summary,
            points=[
                "The original source is preserved.",
                "The generated output remains unconfirmed.",
            ],
            why_it_matters="This supports a lossless, reviewable capture workflow.",
            sections=sections,
        )
