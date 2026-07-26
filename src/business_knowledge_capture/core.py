from __future__ import annotations

import fnmatch
import hashlib
import html
import mimetypes
import os
import re
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Iterable, Protocol
from urllib.parse import urlparse
from xml.etree import ElementTree

DEFAULT_PROTECTED_PATTERNS = (
    "20_Areas/25_Self_Management/**",
    "25_Self_Management/**",
    "Private/**",
    "Credentials/**",
    ".env",
    ".obsidian/**",
)
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".jpg", ".jpeg", ".png", ".mp3", ".mp4"}
MEDIA_EXTENSIONS = {".mp3", ".mp4"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
TEXT_EXTENSIONS = {".txt", ".md"}
CATEGORIES = ("重要知識", "次要知識", "資源", "其他")

IMPORTANT_KEYWORDS = {
    "新工作": 4, "onboarding": 4, "stakeholder": 3, "職涯": 4, "career": 3,
    "ai pm": 4, "product manager": 4, "ai engineer": 4, "python": 2,
    "api": 2, "sql": 2, "docker": 2, "aws": 3, "google ai": 3,
    "考試": 3, "exam": 3, "數碼轉型": 4, "digital transformation": 4,
    "顧問": 3, "consulting": 3, "商業變現": 4, "revenue": 3,
    "pricing": 3, "香氣": 4, "fragrance": 4, "中華文化": 4,
    "重要趨勢": 3, "必須": 2, "action required": 3,
}
RESOURCE_KEYWORDS = {
    "funding": 4, "資助": 4, "比賽": 4, "competition": 4, "招募": 4,
    "recruit": 4, "招聘": 4, "job opening": 4, "課程": 3, "course": 3,
    "認證": 3, "certification": 3, "免費": 3, "free": 2, "優惠": 3,
    "discount": 3, "合作": 3, "partnership": 3, "deadline": 4,
    "截止": 4, "apply": 2, "application": 2,
}
SECONDARY_KEYWORDS = {
    "參考": 2, "reference": 2, "guide": 2, "教學": 2, "案例": 2,
    "case study": 2, "framework": 2, "method": 1, "工具": 1, "tool": 1,
}


class ProtectedPathError(RuntimeError):
    pass


class VaultStructureError(RuntimeError):
    pass


@dataclass(frozen=True)
class SummaryResult:
    status: str
    one_line: str = ""
    key_points: tuple[str, ...] = ()
    reason: str = ""


class Summarizer(Protocol):
    name: str

    def summarize(self, text: str, manual_summary: str = "") -> SummaryResult:
        ...


class DisabledSummarizer:
    name = "disabled"

    def summarize(self, text: str, manual_summary: str = "") -> SummaryResult:
        return SummaryResult("pending", reason="No approved AI provider is configured; summary was not generated.")


class ManualSummarizer:
    name = "manual"

    def summarize(self, text: str, manual_summary: str = "") -> SummaryResult:
        cleaned = manual_summary.strip()
        if not cleaned:
            return SummaryResult("pending", reason="Manual summary was not supplied.")
        return SummaryResult("completed_manual", one_line=cleaned)


class OptionalAIAdapter:
    name = "optional-ai-disabled"

    def summarize(self, text: str, manual_summary: str = "") -> SummaryResult:
        return SummaryResult("pending", reason="Optional AI adapter is disabled until an approved provider is configured.")


@dataclass(frozen=True)
class ClassificationSuggestion:
    category: str
    confidence: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ExtractedSource:
    source_type: str
    source_url: str = ""
    local_file: str = ""
    external_file_link: str = ""
    filename: str = ""
    file_type: str = ""
    file_size: int | None = None
    processing_status: str = "registered"
    readable_text: str = ""
    source_notes: str = ""
    content_hash: str = ""


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            cleaned = " ".join(data.split())
            if cleaned:
                self.parts.append(cleaned)

    def text(self) -> str:
        return "\n".join(self.parts)


def _normalize_pattern(pattern: str) -> str:
    return pattern.strip().replace("\\", "/").lstrip("./")


def protected_paths_markdown() -> str:
    return """# Protected Paths

These paths must be excluded before traversal or file access.

- `20_Areas/25_Self_Management/**`
- `25_Self_Management/**`
- `Private/**`
- `Credentials/**`
- `.env`
- `.obsidian/**`

All scripts and agents must not read, list, stat, hash, copy, move, rename, summarize, or index protected content.
"""


def load_protected_patterns(vault: Path) -> tuple[str, ...]:
    patterns = list(DEFAULT_PROTECTED_PATTERNS)
    protected_file = vault / "90_System" / "Protected_Paths.md"
    if protected_file.is_file():
        for raw in protected_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = re.sub(r"^[-*]\s+", "", raw.strip()).strip("` ")
            if not line or line.startswith("#") or line.startswith(">"):
                continue
            if "/" in line or line in {".env", "Private", "Credentials"}:
                patterns.append(line)
    return tuple(dict.fromkeys(_normalize_pattern(p) for p in patterns if p.strip()))


def _lexical_relative(path: Path, vault: Path) -> str:
    path_abs = os.path.abspath(os.path.expanduser(str(path)))
    vault_abs = os.path.abspath(os.path.expanduser(str(vault)))
    try:
        common = os.path.commonpath([path_abs, vault_abs])
    except ValueError:
        return PurePosixPath(path_abs.replace("\\", "/")).as_posix()
    if common == vault_abs:
        return os.path.relpath(path_abs, vault_abs).replace("\\", "/")
    return PurePosixPath(path_abs.replace("\\", "/")).as_posix()


def is_protected_path(path: Path, vault: Path, patterns: Iterable[str]) -> bool:
    relative = _lexical_relative(path, vault).strip("/")
    parts = PurePosixPath(relative).parts
    if ".env" in parts or (parts and parts[-1] == ".env"):
        return True
    if any(part in {"Credentials", "Private", ".obsidian", "25_Self_Management"} for part in parts):
        return True
    for raw_pattern in patterns:
        pattern = _normalize_pattern(raw_pattern)
        prefix = pattern[:-3].rstrip("/") if pattern.endswith("/**") else ""
        if prefix and (relative == prefix or relative.startswith(prefix + "/")):
            return True
        if fnmatch.fnmatch(relative, pattern):
            return True
        if "/" not in pattern and pattern in parts:
            return True
    return False


def guard_path(path: Path, vault: Path, patterns: Iterable[str]) -> None:
    if is_protected_path(path, vault, patterns):
        raise ProtectedPathError(f"Protected path blocked before filesystem access: {path}")


def inbox_template_markdown() -> str:
    return """# {{title}}

## Metadata

- ID:
- Created:
- Source Type:
- Source URL:
- Local File:
- External File Link:
- Processing Status:
- Summary Status:
- Suggested Category:
- Classification Confidence:
- Action Required:
- Deadline:
- Related Project:
- Related Area:
- Source Filename:
- File Type:
- File Size:
- Content Hash:

## One-line Summary

## Key Points

## Relevance

## Suggested Actions

## Source Notes

## Manual Review

- [ ] Summary reviewed
- [ ] Classification reviewed
- [ ] Action confirmed
- [ ] Related links added
- [ ] Final destination confirmed
"""


def progress_template_markdown() -> str:
    return """# Progress Update

## Period

## Completed

## In Progress

## Evidence

## Blockers／Questions

## Next Steps

## Commitments Before Next Update
"""


def detect_project_root(vault: Path, explicit_root: str = "") -> Path:
    for candidate in (vault / "10_Work" / "11_Projects", vault / "10_Projects"):
        if candidate.is_dir():
            return candidate
    if explicit_root:
        return vault / explicit_root
    raise VaultStructureError(
        "Could not safely detect an existing project root. Expected 10_Work/11_Projects or 10_Projects. "
        "Pass --project-root only after confirming the intended existing structure."
    )


def initialize_vault(vault: Path, project_root: str = "") -> dict[str, str]:
    if not vault.is_dir():
        raise VaultStructureError(f"Vault does not exist: {vault}")
    inbox = vault / "00_Inbox"
    if not inbox.is_dir():
        raise VaultStructureError("00_Inbox was not found. Refusing to guess or create a duplicate vault.")

    system_dir = vault / "90_System"
    templates_dir = system_dir / "Templates"
    system_dir.mkdir(exist_ok=True)
    templates_dir.mkdir(exist_ok=True)

    protected_file = system_dir / "Protected_Paths.md"
    if not protected_file.exists():
        protected_file.write_text(protected_paths_markdown(), encoding="utf-8")
    inbox_template = templates_dir / "Inbox_Note.md"
    if not inbox_template.exists():
        inbox_template.write_text(inbox_template_markdown(), encoding="utf-8")
    report_template = templates_dir / "Progress_Update.md"
    if not report_template.exists():
        report_template.write_text(progress_template_markdown(), encoding="utf-8")

    base = detect_project_root(vault, project_root) / "14_New_Role_90_Day"
    base.mkdir(parents=True, exist_ok=True)
    for folder in (
        "01_Onboarding", "02_Stakeholders", "03_Progress_Reports", "04_Work_Learning",
        "05_System_Development", "06_Decisions", "07_Retrospective",
    ):
        (base / folder).mkdir(exist_ok=True)
    hub = base / "00_Project_Hub.md"
    if not hub.exists():
        hub.write_text(
            "# New Role 90 Day Project Hub\n\n"
            "## Purpose\n\nTrack onboarding, stakeholders, work learning, system development, decisions, and reports.\n",
            encoding="utf-8",
        )
    return {"vault": str(vault), "inbox": str(inbox), "protected_paths": str(protected_file), "project": str(base)}


def _read_text_file(path: Path, max_chars: int = 100_000) -> str:
    return path.read_text(encoding="utf-8", errors="replace")[:max_chars]


def _read_docx(path: Path, max_chars: int = 100_000) -> str:
    with zipfile.ZipFile(path) as archive:
        xml_bytes = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml_bytes)
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs: list[str] = []
    for paragraph in root.iter(ns + "p"):
        joined = "".join(node.text or "" for node in paragraph.iter(ns + "t")).strip()
        if joined:
            paragraphs.append(joined)
    return "\n".join(paragraphs)[:max_chars]


def _read_pdf(path: Path, max_chars: int = 100_000) -> tuple[str, str]:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        return "", "PDF registered; install the optional 'pdf' dependency for local text extraction."
    reader = PdfReader(str(path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    return text[:max_chars], "PDF text extracted locally with pypdf."


def _hash_file(path: Path, max_bytes: int = 20 * 1024 * 1024) -> str:
    if path.stat().st_size > max_bytes:
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fetch_url_text(url: str, max_bytes: int = 2 * 1024 * 1024) -> tuple[str, str]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http and https URLs are supported.")
    request = urllib.request.Request(url, headers={"User-Agent": "BusinessKnowledgeCapture/0.1"})
    with urllib.request.urlopen(request, timeout=15) as response:
        content_type = response.headers.get_content_type()
        raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise ValueError("URL response exceeded the 2 MB safety limit.")
        charset = response.headers.get_content_charset() or "utf-8"
    decoded = raw.decode(charset, errors="replace")
    if content_type == "text/html":
        parser = _TextExtractor()
        parser.feed(decoded)
        return html.unescape(parser.text()), f"Fetched HTML ({content_type}) with explicit --fetch-url."
    if content_type.startswith("text/"):
        return decoded, f"Fetched text ({content_type}) with explicit --fetch-url."
    return "", f"URL content type {content_type} was registered but not extracted."


def extract_source(*, vault: Path, patterns: Iterable[str], text: str = "", url: str = "", file_path: str = "", external_file_link: str = "", fetch_url: bool = False) -> ExtractedSource:
    if sum(bool(item) for item in (text, url, file_path)) != 1:
        raise ValueError("Provide exactly one source: text, URL, or local file path.")
    if text:
        content = text.strip()
        return ExtractedSource("text", external_file_link=external_file_link, processing_status="text_ready", readable_text=content, source_notes=content, content_hash=hashlib.sha256(content.encode()).hexdigest())
    if url:
        readable, status, notes = "", "url_registered", "URL recorded; remote content was not fetched."
        if fetch_url:
            try:
                readable, notes = _fetch_url_text(url)
                status = "text_ready" if readable else "url_registered"
            except Exception as exc:
                status = "url_fetch_failed"
                notes = f"URL preserved. Fetch failed: {type(exc).__name__}: {exc}"
        return ExtractedSource("url", source_url=url, external_file_link=external_file_link, processing_status=status, readable_text=readable, source_notes=notes, content_hash=hashlib.sha256(url.encode()).hexdigest())

    path = Path(os.path.expanduser(file_path))
    guard_path(path, vault, patterns)
    suffix = path.suffix.lower()
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if suffix not in SUPPORTED_EXTENSIONS:
        return ExtractedSource("file", local_file=str(path), external_file_link=external_file_link, filename=path.name, file_type=mime_type, processing_status="unsupported_type", source_notes=f"Unsupported file extension: {suffix or '(none)'}. Original path preserved.")
    if not path.is_file():
        return ExtractedSource("file", local_file=str(path), external_file_link=external_file_link, filename=path.name, file_type=mime_type, processing_status="source_missing", source_notes="File path recorded, but the file was not available. No source was deleted.")

    size, digest = path.stat().st_size, _hash_file(path)
    readable, status, notes = "", "registered", ""
    try:
        if suffix in TEXT_EXTENSIONS:
            readable, status, notes = _read_text_file(path), "text_ready", "Plain text extracted locally."
        elif suffix == ".docx":
            readable = _read_docx(path)
            status = "text_ready" if readable else "awaiting_text_extraction"
            notes = "DOCX text extracted locally." if readable else "DOCX contained no readable paragraph text."
        elif suffix == ".pdf":
            readable, notes = _read_pdf(path)
            status = "text_ready" if readable else "awaiting_text_extraction"
        elif suffix in IMAGE_EXTENSIONS:
            status, notes = "registered_metadata_only", "Image registered. OCR is intentionally out of scope for this MVP."
        elif suffix in MEDIA_EXTENSIONS:
            status, notes = "awaiting_transcription", "Media registered. Transcription is not configured."
    except Exception as exc:
        status, notes = "extraction_failed", f"Original path preserved. Extraction failed: {type(exc).__name__}: {exc}"
    return ExtractedSource("file", local_file=str(path), external_file_link=external_file_link, filename=path.name, file_type=mime_type, file_size=size, processing_status=status, readable_text=readable, source_notes=notes, content_hash=digest)


def classify(text: str, *, deadline: str = "") -> ClassificationSuggestion:
    normalized = " ".join(text.lower().split())

    def score(keywords: dict[str, int]) -> tuple[int, list[str]]:
        hits = [keyword for keyword in keywords if keyword in normalized]
        return sum(keywords[keyword] for keyword in hits), hits

    resource_score, resource_hits = score(RESOURCE_KEYWORDS)
    important_score, important_hits = score(IMPORTANT_KEYWORDS)
    secondary_score, secondary_hits = score(SECONDARY_KEYWORDS)
    if deadline.strip():
        resource_score += 4
        resource_hits.append("deadline field")
    category, top_score, hits = max(
        [("資源", resource_score, resource_hits), ("重要知識", important_score, important_hits), ("次要知識", secondary_score, secondary_hits)],
        key=lambda item: item[1],
    )
    if top_score == 0:
        if len(normalized) >= 80:
            return ClassificationSuggestion("次要知識", "low", ("Readable content exists but no main-line or resource signal matched.",))
        return ClassificationSuggestion("其他", "low", ("Insufficient or low-signal content.",))
    confidence = "high" if top_score >= 7 else "medium" if top_score >= 3 else "low"
    return ClassificationSuggestion(category, confidence, tuple(hits[:6]))


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", value.strip(), flags=re.UNICODE)
    return re.sub(r"-+", "-", cleaned).strip("-")[:60] or "untitled"


def _safe_title(title: str, source: ExtractedSource) -> str:
    if title.strip():
        return title.strip()
    if source.filename:
        return Path(source.filename).stem
    if source.source_url:
        return urlparse(source.source_url).netloc or "Saved URL"
    first = next((line.strip() for line in source.readable_text.splitlines() if line.strip()), "")
    return first[:80] or "Inbox Capture"


def render_inbox_note(*, note_id: str, created: str, title: str, source: ExtractedSource, summary: SummaryResult, classification: ClassificationSuggestion, action_required: str = "", deadline: str = "", related_project: str = "", related_area: str = "") -> str:
    source_notes = source.readable_text[:50_000] if source.source_type == "text" else source.source_notes
    if source.source_type != "text" and source.readable_text:
        source_notes = f"{source_notes}\n\n### Extracted Text\n\n{source.readable_text[:50_000]}".strip()
    relevance = f"Suggested category: **{classification.category}** ({classification.confidence} confidence)."
    if classification.reasons:
        relevance += "\n\nSignals: " + ", ".join(classification.reasons)
    suggested_actions = action_required.strip() or ("Review the source and add a manual summary before final filing." if summary.status == "pending" else "")
    points = "\n".join(f"- {item}" for item in summary.key_points)
    size = "" if source.file_size is None else str(source.file_size)
    return f"""# {title}

## Metadata

- ID: {note_id}
- Created: {created}
- Source Type: {source.source_type}
- Source URL: {source.source_url}
- Local File: {source.local_file}
- External File Link: {source.external_file_link}
- Processing Status: {source.processing_status}
- Summary Status: {summary.status}
- Suggested Category: {classification.category}
- Classification Confidence: {classification.confidence}
- Action Required: {action_required}
- Deadline: {deadline}
- Related Project: {related_project}
- Related Area: {related_area}
- Source Filename: {source.filename}
- File Type: {source.file_type}
- File Size: {size}
- Content Hash: {source.content_hash}

## One-line Summary

{summary.one_line}

## Key Points

{points}

## Relevance

{relevance}

## Suggested Actions

{suggested_actions}

## Source Notes

{source_notes}

{summary.reason if summary.status == 'pending' else ''}

## Manual Review

- [ ] Summary reviewed
- [ ] Classification reviewed
- [ ] Action confirmed
- [ ] Related links added
- [ ] Final destination confirmed
"""


def create_inbox_note(*, vault: Path, source: ExtractedSource, title: str = "", summarizer: Summarizer | None = None, manual_summary: str = "", action_required: str = "", deadline: str = "", related_project: str = "", related_area: str = "") -> Path:
    inbox = vault / "00_Inbox"
    if not inbox.is_dir():
        raise VaultStructureError("00_Inbox is missing; refusing to create a duplicate vault.")
    summarizer = summarizer or DisabledSummarizer()
    summary = summarizer.summarize(source.readable_text, manual_summary)
    classification = classify("\n".join(filter(None, [source.readable_text, title, action_required, related_project, related_area])), deadline=deadline)
    now = datetime.now().astimezone()
    identity = source.content_hash or source.source_url or source.local_file or source.readable_text
    note_id = f"BKC-{now:%Y%m%d%H%M%S}-{hashlib.sha256(identity.encode()).hexdigest()[:8]}"
    resolved_title = _safe_title(title, source)
    stem = f"{now:%Y%m%d-%H%M%S}-{_slugify(resolved_title)}"
    output = inbox / f"{stem}.md"
    counter = 2
    while output.exists():
        output = inbox / f"{stem}-{counter}.md"
        counter += 1
    output.write_text(render_inbox_note(note_id=note_id, created=now.isoformat(timespec="seconds"), title=resolved_title, source=source, summary=summary, classification=classification, action_required=action_required, deadline=deadline, related_project=related_project, related_area=related_area), encoding="utf-8")
    return output


def _replace_metadata(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"(?m)^- {re.escape(key)}:.*$")
    if not pattern.search(text):
        raise ValueError(f"Metadata field not found: {key}")
    return pattern.sub(f"- {key}: {value}", text, count=1)


def review_note(*, vault: Path, note_path: Path, category: str = "", action_required: str = "", related_project: str = "", related_area: str = "", destination: str = "", mark: Iterable[str] = ()) -> Path:
    guard_path(note_path, vault, load_protected_patterns(vault))
    if category and category not in CATEGORIES:
        raise ValueError(f"Category must be one of: {', '.join(CATEGORIES)}")
    text = note_path.read_text(encoding="utf-8")
    for key, value in {"Suggested Category": category, "Action Required": action_required, "Related Project": related_project, "Related Area": related_area}.items():
        if value:
            text = _replace_metadata(text, key, value)
    mark_map = {"summary": "Summary reviewed", "classification": "Classification reviewed", "action": "Action confirmed", "links": "Related links added", "destination": "Final destination confirmed"}
    for item in mark:
        text = text.replace(f"- [ ] {mark_map[item]}", f"- [x] {mark_map[item]}", 1)
    if destination and "Final destination:" not in text:
        text = text.replace("## Manual Review", f"Final destination: {destination}\n\n## Manual Review", 1)
    note_path.write_text(text, encoding="utf-8")
    return note_path


def _parse_note(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8", errors="replace")
    title_match = re.search(r"(?m)^#\s+(.+)$", text)
    metadata = {match.group(1).strip(): match.group(2).strip() for match in re.finditer(r"(?m)^- ([^:\n]+):[ \t]*(.*)$", text)}

    def section(name: str) -> str:
        match = re.search(rf"(?ms)^## {re.escape(name)}\s*\n(.*?)(?=^## |\Z)", text)
        return match.group(1).strip() if match else ""

    return {"title": title_match.group(1).strip() if title_match else path.stem, "metadata": metadata, "summary": section("One-line Summary"), "actions": section("Suggested Actions")}


def _note_line(note: dict[str, object]) -> str:
    summary = str(note["summary"]).strip()
    return f"- **{note['title']}** — {summary}" if summary else f"- **{note['title']}**"


def _evidence_lines(notes: Iterable[dict[str, object]]) -> list[str]:
    lines: list[str] = []
    for note in notes:
        metadata = note["metadata"]
        assert isinstance(metadata, dict)
        for label, value in (("External", metadata.get("External File Link", "")), ("Source", metadata.get("Source URL", "")), ("Local file", metadata.get("Local File", ""))):
            if value:
                lines.append(f"- **{note['title']}** — {label}: {value}")
    return lines


def generate_progress_report(*, vault: Path, completed_paths: Iterable[Path], in_progress_paths: Iterable[Path], period_label: str, report_type: str, project_root: str = "", blockers: Iterable[str] = (), commitments: Iterable[str] = ()) -> Path:
    if report_type not in {"daily", "weekly"}:
        raise ValueError("report_type must be daily or weekly")
    patterns = load_protected_patterns(vault)
    completed, in_progress = [], []
    for path in completed_paths:
        guard_path(path, vault, patterns)
        completed.append(_parse_note(path))
    for path in in_progress_paths:
        guard_path(path, vault, patterns)
        in_progress.append(_parse_note(path))
    all_notes = completed + in_progress

    def block(lines: Iterable[str], placeholder: str = "- None recorded.") -> str:
        values = [line for line in lines if line]
        return "\n".join(values) if values else placeholder

    report = f"""# Progress Update

## Period

{period_label}

## Completed

{block(_note_line(note) for note in completed)}

## In Progress

{block(_note_line(note) for note in in_progress)}

## Evidence

{block(_evidence_lines(all_notes))}

## Blockers／Questions

{block(f'- {item}' for item in blockers if item.strip())}

## Next Steps

{block(f'- {str(note["actions"]).strip()}' for note in all_notes if str(note["actions"]).strip())}

## Commitments Before Next Update

{block((f'- [ ] {item}' for item in commitments if item.strip()), '- [ ] Add commitments after review.')}
"""
    reports_dir = detect_project_root(vault, project_root) / "14_New_Role_90_Day" / "03_Progress_Reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{date.today().isoformat()}-{report_type}-progress"
    output = reports_dir / f"{stem}.md"
    counter = 2
    while output.exists():
        output = reports_dir / f"{stem}-{counter}.md"
        counter += 1
    output.write_text(report, encoding="utf-8")
    return output


def validate_vault(vault: Path) -> list[str]:
    errors: list[str] = []
    if not vault.is_dir():
        return [f"Vault does not exist: {vault}"]
    inbox = vault / "00_Inbox"
    if not inbox.is_dir():
        errors.append("00_Inbox is missing.")
    elif any(item.is_dir() for item in inbox.iterdir()):
        errors.append("00_Inbox must remain flat; subdirectories were found.")
    if not (vault / "90_System" / "Protected_Paths.md").is_file():
        errors.append("90_System/Protected_Paths.md is missing.")
    return errors
