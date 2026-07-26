from __future__ import annotations

import fnmatch
import hashlib
import html
import ipaddress
import mimetypes
import os
import re
import socket
import stat
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable, Optional, Protocol
from urllib.parse import urlparse, urlsplit, urlunsplit
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
MAX_INBOX_CANDIDATES = 5_000
MAX_DUPLICATE_MATCHES_RECORDED = 5
MAX_METADATA_BYTES = 64 * 1024

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


class UnsafePathError(RuntimeError):
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
    file_size: Optional[int] = None
    processing_status: str = "registered"
    readable_text: str = ""
    source_notes: str = ""
    content_hash: str = ""


@dataclass(frozen=True)
class DuplicateResult:
    status: str
    match_type: str
    matches: tuple[str, ...] = ()
    match_count: int = 0
    diagnostics: tuple[str, ...] = ()


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
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
    _guard_no_symlinks(protected_file)
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


def _guard_no_symlinks(path: Path) -> None:
    absolute = Path(os.path.abspath(os.path.expanduser(str(path))))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        try:
            mode = os.lstat(str(current)).st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise UnsafePathError(f"Symbolic links are not accepted: {current}")


def guard_local_path(path: Path, vault: Path, patterns: Iterable[str]) -> None:
    guard_path(path, vault, patterns)
    _guard_no_symlinks(path)


def _lexically_inside(path: Path, directory: Path) -> bool:
    path_abs = os.path.abspath(os.path.expanduser(str(path)))
    directory_abs = os.path.abspath(os.path.expanduser(str(directory)))
    try:
        return os.path.commonpath([path_abs, directory_abs]) == directory_abs
    except ValueError:
        return False


def guard_vault_note(path: Path, vault: Path, patterns: Iterable[str]) -> None:
    if not _lexically_inside(path, vault):
        raise UnsafePathError("Review and report notes must be inside the selected vault.")
    if path.suffix.lower() != ".md":
        raise UnsafePathError("Review and report notes must be Markdown files.")
    guard_local_path(path, vault, patterns)
    try:
        mode = os.lstat(str(path)).st_mode
    except FileNotFoundError as exc:
        raise UnsafePathError(f"Vault note does not exist: {path}") from exc
    if not stat.S_ISREG(mode):
        raise UnsafePathError(f"Vault note must be a regular file: {path}")


def _single_line(value: object) -> str:
    return " ".join(str(value).replace("\r", "\n").splitlines()).strip()


def parse_iso_date(value: str, label: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO date (YYYY-MM-DD).") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{label} must be an ISO date (YYYY-MM-DD).")
    return parsed


def validate_optional_iso_date(value: str, label: str) -> str:
    cleaned = _single_line(value)
    if cleaned:
        parse_iso_date(cleaned, label)
    return cleaned


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
- Resource Expiry:
- Reminder Date:
- Reminder Note:
- Related Project:
- Related Area:
- Source Filename:
- File Type:
- File Size:
- Content Hash:
- Duplicate Status:
- Duplicate Match Type:
- Duplicate Of:
- Duplicate Match Count:

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
- [ ] Duplicate status reviewed
- [ ] Date and reminder fields reviewed
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
    migrated_root = vault / "10_Work" / "11_Projects"
    legacy_root = vault / "10_Projects"
    if explicit_root:
        explicit_candidate = Path(os.path.abspath(str(vault / explicit_root)))
        approved_roots = {
            Path(os.path.abspath(str(migrated_root))),
            Path(os.path.abspath(str(legacy_root))),
        }
        if explicit_candidate not in approved_roots:
            raise VaultStructureError("Explicit project root must be one of the two approved existing project roots.")
    migrated_project = migrated_root / "14_New_Role_90_Day"
    legacy_project = legacy_root / "14_New_Role_90_Day"
    for candidate in (migrated_root, legacy_root, migrated_project, legacy_project):
        _guard_no_symlinks(candidate)

    migrated_exists = migrated_project.is_dir()
    legacy_exists = legacy_project.is_dir()
    if migrated_exists and legacy_exists:
        raise VaultStructureError("Conflicting 14_New_Role_90_Day projects exist in both approved roots.")
    if migrated_exists:
        return migrated_root
    if legacy_exists:
        return legacy_root
    if migrated_root.is_dir():
        return migrated_root
    if legacy_root.is_dir():
        return legacy_root
    raise VaultStructureError(
        "Could not safely detect an existing project root. Expected 10_Work/11_Projects or 10_Projects. "
        "An explicit root must already exist."
    )


def _ensure_directory(path: Path, vault: Path, patterns: Iterable[str]) -> None:
    guard_local_path(path, vault, patterns)
    if path.exists() and not path.is_dir():
        raise VaultStructureError(f"Expected a directory but found another file type: {path}")
    path.mkdir(exist_ok=True)


def _merge_protected_file(path: Path) -> None:
    _guard_no_symlinks(path)
    if not path.exists():
        path.write_text(protected_paths_markdown(), encoding="utf-8")
        return
    existing = path.read_text(encoding="utf-8")
    normalized = {
        _normalize_pattern(re.sub(r"^[-*]\s+", "", raw.strip()).strip("` "))
        for raw in existing.splitlines()
    }
    missing = [pattern for pattern in DEFAULT_PROTECTED_PATTERNS if _normalize_pattern(pattern) not in normalized]
    if missing:
        separator = "" if existing.endswith("\n") else "\n"
        additions = "\n".join(f"- `{pattern}`" for pattern in missing)
        path.write_text(f"{existing}{separator}{additions}\n", encoding="utf-8")


def _write_managed_template(path: Path, content: str, conflicts: list[str]) -> Path:
    _guard_no_symlinks(path)
    if not path.exists():
        path.write_text(content, encoding="utf-8")
        return path
    if path.read_text(encoding="utf-8") == content:
        return path
    versioned = path.with_name(f"{path.stem}.v2{path.suffix}")
    _guard_no_symlinks(versioned)
    if not versioned.exists():
        versioned.write_text(content, encoding="utf-8")
    conflicts.append(f"Preserved existing {path.name}; managed template is {versioned.name}.")
    return versioned


def initialize_vault(vault: Path, project_root: str = "") -> dict[str, str]:
    _guard_no_symlinks(vault)
    if not vault.is_dir():
        raise VaultStructureError(f"Vault does not exist: {vault}")
    inbox = vault / "00_Inbox"
    _guard_no_symlinks(inbox)
    if not inbox.is_dir():
        raise VaultStructureError("00_Inbox was not found. Refusing to guess or create a duplicate vault.")

    patterns = DEFAULT_PROTECTED_PATTERNS
    system_dir = vault / "90_System"
    templates_dir = system_dir / "Templates"
    _ensure_directory(system_dir, vault, patterns)
    _ensure_directory(templates_dir, vault, patterns)

    protected_file = system_dir / "Protected_Paths.md"
    guard_local_path(protected_file, vault, patterns)
    _merge_protected_file(protected_file)
    patterns = load_protected_patterns(vault)
    conflicts: list[str] = []
    inbox_template = templates_dir / "Inbox_Note.md"
    guard_local_path(inbox_template, vault, patterns)
    managed_inbox_template = _write_managed_template(inbox_template, inbox_template_markdown(), conflicts)
    report_template = templates_dir / "Progress_Update.md"
    guard_local_path(report_template, vault, patterns)
    managed_report_template = _write_managed_template(report_template, progress_template_markdown(), conflicts)

    base = detect_project_root(vault, project_root) / "14_New_Role_90_Day"
    _ensure_directory(base, vault, patterns)
    for folder in (
        "01_Onboarding", "02_Stakeholders", "03_Progress_Reports", "04_Work_Learning",
        "05_System_Development", "06_Decisions", "07_Retrospective",
    ):
        _ensure_directory(base / folder, vault, patterns)
    hub = base / "00_Project_Hub.md"
    guard_local_path(hub, vault, patterns)
    if not hub.exists():
        hub.write_text(
            "# New Role 90 Day Project Hub\n\n"
            "## Purpose\n\nTrack onboarding, stakeholders, work learning, system development, decisions, and reports.\n",
            encoding="utf-8",
        )
    return {
        "vault": str(vault),
        "inbox": str(inbox),
        "protected_paths": str(protected_file),
        "project": str(base),
        "inbox_template": str(managed_inbox_template),
        "report_template": str(managed_report_template),
        "conflicts": "\n".join(conflicts),
    }


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


def validate_public_url(
    url: str,
    resolver: Callable[..., list[tuple[object, ...]]] = socket.getaddrinfo,
) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http and https URLs are supported.")
    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("URL must contain a public hostname without embedded credentials.")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ValueError("Localhost URLs are not allowed.")
    try:
        addresses = [ipaddress.ip_address(hostname)]
    except ValueError:
        try:
            records = resolver(hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise ValueError("URL hostname could not be resolved.") from exc
        addresses = []
        for record in records:
            address = record[4][0]
            parsed_address = ipaddress.ip_address(address.split("%", 1)[0])
            if parsed_address not in addresses:
                addresses.append(parsed_address)
    if not addresses:
        raise ValueError("URL hostname did not resolve to an address.")
    if any(
        not address.is_global
        or address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
        for address in addresses
    ):
        raise ValueError("URL resolved to a non-public address.")
    return url


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    max_redirections = 5

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _fetch_url_text(url: str, max_bytes: int = 2 * 1024 * 1024) -> tuple[str, str]:
    validate_public_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": "BusinessKnowledgeCapture/0.1"})
    opener = urllib.request.build_opener(_SafeRedirectHandler())
    with opener.open(request, timeout=15) as response:
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
    guard_local_path(path, vault, patterns)
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
        return _single_line(title)
    if source.filename:
        return _single_line(Path(source.filename).stem)
    if source.source_url:
        return _single_line(urlparse(source.source_url).netloc) or "Saved URL"
    first = next((line.strip() for line in source.readable_text.splitlines() if line.strip()), "")
    return _single_line(first[:80]) or "Inbox Capture"


def normalize_url_for_duplicate(url: str) -> str:
    try:
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        if scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return ""
        hostname = parsed.hostname.encode("idna").decode("ascii").lower()
        if ":" in hostname:
            hostname = f"[{hostname}]"
        port = parsed.port
    except (UnicodeError, ValueError):
        return ""
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    netloc = hostname if port is None or default_port else f"{hostname}:{port}"
    return urlunsplit((scheme, netloc, parsed.path or "/", parsed.query, ""))


def _read_inbox_prefix(
    path: Path,
    *,
    require_metadata: bool = True,
) -> tuple[str, dict[str, str]]:
    title = ""
    metadata_lines: list[str] = []
    in_metadata = False
    total_bytes = 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            total_bytes += len(line.encode("utf-8"))
            if total_bytes > MAX_METADATA_BYTES:
                raise ValueError("Inbox metadata exceeded the local read limit.")
            stripped = line.rstrip("\r\n")
            if not title:
                title_match = re.match(r"^#\s+(.+)$", stripped)
                if title_match:
                    title = title_match.group(1).strip()
            if stripped == "## Metadata":
                in_metadata = True
                continue
            if in_metadata and line.startswith("## "):
                break
            if not in_metadata and line.startswith("## "):
                break
            if not in_metadata and stripped and not stripped.startswith("# "):
                break
            if in_metadata:
                metadata_lines.append(line)
    metadata = {
        match.group(1).strip(): match.group(2).strip()
        for line in metadata_lines
        for match in [re.match(r"^- ([^:\n]+):[ \t]*(.*)$", line.rstrip("\r\n"))]
        if match
    }
    if require_metadata and not in_metadata:
        raise ValueError("Inbox candidate has no Metadata section.")
    return title, metadata


def _read_inbox_metadata(path: Path) -> dict[str, str]:
    return _read_inbox_prefix(path)[1]


def list_safe_inbox_candidates(
    *,
    vault: Path,
    max_candidates: int = MAX_INBOX_CANDIDATES,
) -> tuple[tuple[Path, ...], tuple[str, ...]]:
    inbox = vault / "00_Inbox"
    patterns = load_protected_patterns(vault)
    guard_local_path(inbox, vault, patterns)
    if not inbox.is_dir():
        raise VaultStructureError("00_Inbox is missing.")

    candidates = sorted(inbox.glob("*.md"), key=lambda path: path.name)
    if len(candidates) > max_candidates:
        raise ValueError(f"Inbox search candidate limit exceeded (maximum {max_candidates}).")

    safe_candidates: list[Path] = []
    diagnostics: list[str] = []
    for candidate in candidates:
        relative = candidate.relative_to(vault).as_posix()
        if candidate.parent != inbox or candidate.suffix.lower() != ".md":
            diagnostics.append(f"{relative}: candidate is outside the flat Markdown Inbox scope.")
            continue
        try:
            guard_local_path(candidate, vault, patterns)
            mode = os.lstat(str(candidate)).st_mode
            if not stat.S_ISREG(mode):
                diagnostics.append(f"{relative}: candidate is not a regular file.")
                continue
        except (OSError, ProtectedPathError, UnsafePathError) as exc:
            diagnostics.append(f"{relative}: {exc.__class__.__name__}.")
            continue
        safe_candidates.append(candidate)
    return tuple(safe_candidates), tuple(diagnostics)


def find_exact_duplicates(
    *,
    vault: Path,
    source: ExtractedSource,
    max_candidates: int = MAX_INBOX_CANDIDATES,
) -> DuplicateResult:
    inbox = vault / "00_Inbox"
    patterns = load_protected_patterns(vault)
    guard_local_path(inbox, vault, patterns)
    if not inbox.is_dir():
        raise VaultStructureError("00_Inbox is missing; refusing to create a duplicate vault.")

    source_hash = source.content_hash.lower() if re.fullmatch(r"[0-9a-fA-F]{64}", source.content_hash) else ""
    normalized_source_url = normalize_url_for_duplicate(source.source_url)
    if not source_hash and not normalized_source_url:
        return DuplicateResult("check_unavailable", "unavailable")

    try:
        candidates, candidate_diagnostics = list_safe_inbox_candidates(
            vault=vault,
            max_candidates=max_candidates,
        )
    except ValueError:
        return DuplicateResult(
            "check_unavailable",
            "unavailable",
            diagnostics=(f"Inbox candidate limit exceeded ({max_candidates}).",),
        )

    content_matches: set[str] = set()
    url_matches: set[str] = set()
    skipped = len(candidate_diagnostics)
    for candidate in candidates:
        try:
            metadata = _read_inbox_metadata(candidate)
        except (OSError, ValueError):
            skipped += 1
            continue

        relative = candidate.relative_to(vault).as_posix()
        candidate_hash = metadata.get("Content Hash", "")
        if source_hash and re.fullmatch(r"[0-9a-fA-F]{64}", candidate_hash) and candidate_hash.lower() == source_hash:
            content_matches.add(relative)
        candidate_url = normalize_url_for_duplicate(metadata.get("Source URL", ""))
        if normalized_source_url and candidate_url == normalized_source_url:
            url_matches.add(relative)

    matches = sorted(content_matches | url_matches)
    diagnostics = (f"{skipped} unsafe or malformed Inbox candidate(s) skipped.",) if skipped else ()
    if not matches:
        return DuplicateResult("unique", "none", diagnostics=diagnostics)
    if content_matches and url_matches:
        match_type = "content_hash_and_url"
    elif content_matches:
        match_type = "content_hash"
    else:
        match_type = "normalized_url"
    return DuplicateResult(
        "exact_duplicate_suggested",
        match_type,
        tuple(matches[:MAX_DUPLICATE_MATCHES_RECORDED]),
        len(matches),
        diagnostics,
    )


def render_inbox_note(*, note_id: str, created: str, title: str, source: ExtractedSource, summary: SummaryResult, classification: ClassificationSuggestion, duplicate: Optional[DuplicateResult] = None, action_required: str = "", deadline: str = "", resource_expiry: str = "", reminder_date: str = "", reminder_note: str = "", related_project: str = "", related_area: str = "", extra_metadata: Iterable[tuple[str, str]] = (), extra_review_items: Iterable[str] = ()) -> str:
    duplicate = duplicate or DuplicateResult("check_unavailable", "unavailable")
    source_notes = source.readable_text[:50_000] if source.source_type in {"text", "voice_transcript"} else source.source_notes
    if source.source_type not in {"text", "voice_transcript"} and source.readable_text:
        source_notes = f"{source_notes}\n\n### Extracted Text\n\n{source.readable_text[:50_000]}".strip()
    relevance = f"Suggested category: **{classification.category}** ({classification.confidence} confidence)."
    if classification.reasons:
        relevance += "\n\nSignals: " + ", ".join(classification.reasons)
    safe_action = _single_line(action_required)
    suggested_actions = safe_action or ("Review the source and add a manual summary before final filing." if summary.status == "pending" else "")
    points = "\n".join(f"- {item}" for item in summary.key_points)
    size = "" if source.file_size is None else str(source.file_size)
    safe_title = _single_line(title)
    safe_related_project = _single_line(related_project)
    safe_related_area = _single_line(related_area)
    safe_deadline = _single_line(deadline)
    safe_resource_expiry = _single_line(resource_expiry)
    safe_reminder_date = _single_line(reminder_date)
    safe_reminder_note = _single_line(reminder_note)
    safe_external_link = _single_line(source.external_file_link)
    safe_source_url = _single_line(source.source_url)
    safe_local_file = _single_line(source.local_file)
    safe_filename = _single_line(source.filename)
    metadata_lines = "".join(
        f"- {_single_line(key)}: {_single_line(value)}\n"
        for key, value in extra_metadata
    )
    review_lines = "".join(
        f"- [ ] {_single_line(label)}\n" for label in extra_review_items
    )
    return f"""# {safe_title}

## Metadata

- ID: {note_id}
- Created: {created}
- Source Type: {source.source_type}
- Source URL: {safe_source_url}
- Local File: {safe_local_file}
- External File Link: {safe_external_link}
- Processing Status: {source.processing_status}
- Summary Status: {summary.status}
- Suggested Category: {classification.category}
- Classification Confidence: {classification.confidence}
- Action Required: {safe_action}
- Deadline: {safe_deadline}
- Resource Expiry: {safe_resource_expiry}
- Reminder Date: {safe_reminder_date}
- Reminder Note: {safe_reminder_note}
- Related Project: {safe_related_project}
- Related Area: {safe_related_area}
- Source Filename: {safe_filename}
- File Type: {source.file_type}
- File Size: {size}
- Content Hash: {source.content_hash}
- Duplicate Status: {duplicate.status}
- Duplicate Match Type: {duplicate.match_type}
- Duplicate Of: {_single_line(", ".join(duplicate.matches))}
- Duplicate Match Count: {duplicate.match_count}
{metadata_lines.rstrip()}

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
- [ ] Duplicate status reviewed
- [ ] Date and reminder fields reviewed
{review_lines.rstrip()}
"""


def capture_inbox_note(*, vault: Path, source: ExtractedSource, title: str = "", summarizer: Optional[Summarizer] = None, manual_summary: str = "", action_required: str = "", deadline: str = "", resource_expiry: str = "", reminder_date: str = "", reminder_note: str = "", related_project: str = "", related_area: str = "", extra_metadata: Iterable[tuple[str, str]] = (), extra_review_items: Iterable[str] = ()) -> tuple[Path, DuplicateResult]:
    deadline = validate_optional_iso_date(deadline, "Deadline")
    resource_expiry = validate_optional_iso_date(resource_expiry, "Resource Expiry")
    reminder_date = validate_optional_iso_date(reminder_date, "Reminder Date")
    reminder_note = _single_line(reminder_note)
    inbox = vault / "00_Inbox"
    guard_local_path(inbox, vault, DEFAULT_PROTECTED_PATTERNS)
    if not inbox.is_dir():
        raise VaultStructureError("00_Inbox is missing; refusing to create a duplicate vault.")
    summarizer = summarizer or DisabledSummarizer()
    duplicate = find_exact_duplicates(vault=vault, source=source)
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
    guard_local_path(output, vault, DEFAULT_PROTECTED_PATTERNS)
    _atomic_write_text(
        output,
        render_inbox_note(
            note_id=note_id,
            created=now.isoformat(timespec="seconds"),
            title=resolved_title,
            source=source,
            summary=summary,
            classification=classification,
            duplicate=duplicate,
            action_required=action_required,
            deadline=deadline,
            resource_expiry=resource_expiry,
            reminder_date=reminder_date,
            reminder_note=reminder_note,
            related_project=related_project,
            related_area=related_area,
            extra_metadata=extra_metadata,
            extra_review_items=extra_review_items,
        ),
    )
    return output, duplicate


def create_inbox_note(*, vault: Path, source: ExtractedSource, title: str = "", summarizer: Optional[Summarizer] = None, manual_summary: str = "", action_required: str = "", deadline: str = "", resource_expiry: str = "", reminder_date: str = "", reminder_note: str = "", related_project: str = "", related_area: str = "") -> Path:
    output, _ = capture_inbox_note(vault=vault, source=source, title=title, summarizer=summarizer, manual_summary=manual_summary, action_required=action_required, deadline=deadline, resource_expiry=resource_expiry, reminder_date=reminder_date, reminder_note=reminder_note, related_project=related_project, related_area=related_area)
    return output


def _replace_metadata(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"(?m)^- {re.escape(key)}:.*$")
    if not pattern.search(text):
        raise ValueError(f"Metadata field not found: {key}")
    return pattern.sub(f"- {key}: {_single_line(value)}", text, count=1)


def _set_or_insert_metadata(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"(?m)^- {re.escape(key)}:.*$")
    replacement = f"- {key}: {_single_line(value)}"
    if pattern.search(text):
        return pattern.sub(replacement, text, count=1)
    anchor = re.search(r"(?m)^- Related Project:.*$", text)
    if not anchor:
        raise ValueError(f"Metadata field not found and insertion point unavailable: {key}")
    return text[:anchor.start()] + replacement + "\n" + text[anchor.start():]


def _mark_review_item(text: str, label: str) -> str:
    unchecked = f"- [ ] {label}"
    checked = f"- [x] {label}"
    if unchecked in text:
        return text.replace(unchecked, checked, 1)
    if checked in text:
        return text
    manual_review = re.search(r"(?m)^## Manual Review[ \t]*$", text)
    if not manual_review:
        raise ValueError("Manual Review section not found.")
    insert_at = text.find("\n", manual_review.end())
    if insert_at < 0:
        return text + f"\n\n{checked}\n"
    return text[:insert_at + 1] + f"\n{checked}" + text[insert_at + 1:]


def review_note(*, vault: Path, note_path: Path, category: str = "", action_required: str = "", related_project: str = "", related_area: str = "", destination: str = "", deadline: str = "", resource_expiry: str = "", reminder_date: str = "", reminder_note: str = "", clear_deadline: bool = False, clear_resource_expiry: bool = False, clear_reminder: bool = False, mark: Iterable[str] = ()) -> Path:
    guard_vault_note(note_path, vault, load_protected_patterns(vault))
    if category and category not in CATEGORIES:
        raise ValueError(f"Category must be one of: {', '.join(CATEGORIES)}")
    deadline = validate_optional_iso_date(deadline, "Deadline")
    resource_expiry = validate_optional_iso_date(resource_expiry, "Resource Expiry")
    reminder_date = validate_optional_iso_date(reminder_date, "Reminder Date")
    reminder_note = _single_line(reminder_note)
    if deadline and clear_deadline:
        raise ValueError("--deadline and --clear-deadline are mutually exclusive.")
    if resource_expiry and clear_resource_expiry:
        raise ValueError(
            "--resource-expiry and --clear-resource-expiry are mutually exclusive."
        )
    if clear_reminder and (reminder_date or reminder_note):
        raise ValueError(
            "--reminder-date/--reminder-note and --clear-reminder are mutually exclusive."
        )
    mark_values = tuple(mark)
    mark_map = {"summary": "Summary reviewed", "classification": "Classification reviewed", "action": "Action confirmed", "links": "Related links added", "destination": "Final destination confirmed", "duplicate": "Duplicate status reviewed", "dates": "Date and reminder fields reviewed", "handoff": "Mobile handoff reviewed", "transcript": "Voice transcript checked"}
    invalid_marks = [item for item in mark_values if item not in mark_map]
    if invalid_marks:
        raise ValueError(f"Unsupported review mark: {invalid_marks[0]}")
    text = note_path.read_text(encoding="utf-8")
    if "transcript" in mark_values:
        source_type = re.search(
            r"(?m)^- Source Type:[ \t]*(.*)$",
            text,
        )
        if not source_type or source_type.group(1).strip() != "voice_transcript":
            raise ValueError(
                "Voice transcript review is not applicable to this note."
            )
    for key, value in {"Suggested Category": category, "Action Required": action_required, "Related Project": related_project, "Related Area": related_area}.items():
        if value:
            text = _replace_metadata(text, key, value)
    for key, value, should_update in (
        ("Deadline", deadline, bool(deadline) or clear_deadline),
        (
            "Resource Expiry",
            resource_expiry,
            bool(resource_expiry) or clear_resource_expiry,
        ),
        ("Reminder Date", reminder_date, bool(reminder_date) or clear_reminder),
        ("Reminder Note", reminder_note, bool(reminder_note) or clear_reminder),
    ):
        if should_update:
            text = _set_or_insert_metadata(text, key, value)
    if action_required:
        safe_action = _single_line(action_required)
        text = re.sub(
            r"(?ms)^## Suggested Actions\s*\n.*?(?=^## Source Notes)",
            lambda _: f"## Suggested Actions\n\n{safe_action}\n\n",
            text,
            count=1,
        )
    if "transcript" in mark_values:
        text = _set_or_insert_metadata(
            text,
            "Transcript Review Status",
            "reviewed",
        )
    for item in mark_values:
        text = _mark_review_item(text, mark_map[item])
    if category:
        text = re.sub(
            r"(?m)^Suggested category: \*\*.*?\*\* \((.*?) confidence\)\.$",
            f"Suggested category: **{category}** (manual confidence).",
            text,
            count=1,
        )
    if destination:
        safe_destination = _single_line(destination)
        if "Final destination:" in text:
            text = re.sub(r"(?m)^Final destination:.*$", f"Final destination: {safe_destination}", text, count=1)
        else:
            text = text.replace("## Manual Review", f"Final destination: {safe_destination}\n\n## Manual Review", 1)
    _atomic_write_text(note_path, text)
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


def _date_review_markdown(events: Iterable[object]) -> str:
    labels = {
        "reminder": "Reminder",
        "deadline": "Deadline",
        "resource_expiry": "Resource Expiry",
    }
    sections: list[str] = []
    for event in events:
        event_type = str(getattr(event, "event_type"))
        event_date = getattr(event, "event_date")
        days_until = int(getattr(event, "days_until"))
        lines = [
            (
                f"### {event_date.isoformat()} — {labels[event_type]} — "
                f"{getattr(event, 'title')}"
            ),
            "",
            f"- Status: {getattr(event, 'status')}",
            (
                f"- Days Overdue: {abs(days_until)}"
                if days_until < 0
                else f"- Days Until: {days_until}"
            ),
        ]
        optional = (
            ("Action Required", getattr(event, "action_required")),
            (
                "Reminder Note",
                getattr(event, "reminder_note")
                if event_type == "reminder"
                else "",
            ),
            ("Related Project", getattr(event, "related_project")),
            ("Related Area", getattr(event, "related_area")),
        )
        lines.extend(f"- {label}: {value}" for label, value in optional if value)
        lines.append(f"- Source Note: `{getattr(event, 'relative_path')}`")
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def _atomic_write_text(path: Path, text: str) -> None:
    temporary_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if temporary_name:
            try:
                Path(temporary_name).unlink()
            except FileNotFoundError:
                pass


def generate_progress_report(*, vault: Path, completed_paths: Iterable[Path], in_progress_paths: Iterable[Path], period_label: str, report_type: str, project_root: str = "", blockers: Iterable[str] = (), commitments: Iterable[str] = (), due_events: Iterable[object] = ()) -> Path:
    if report_type not in {"daily", "weekly"}:
        raise ValueError("report_type must be daily or weekly")
    patterns = load_protected_patterns(vault)
    completed, in_progress = [], []
    for path in completed_paths:
        guard_vault_note(path, vault, patterns)
        completed.append(_parse_note(path))
    for path in in_progress_paths:
        guard_vault_note(path, vault, patterns)
        in_progress.append(_parse_note(path))
    all_notes = completed + in_progress

    def block(lines: Iterable[str], placeholder: str = "- None recorded.") -> str:
        values = [line for line in lines if line]
        return "\n".join(values) if values else placeholder

    action_lines = []
    for note in all_notes:
        action_text = str(note["actions"]).strip()
        if action_text:
            action_lines.append(f"- {action_text}")

    date_events = tuple(due_events)
    in_progress_block = block(_note_line(note) for note in in_progress)
    if date_events:
        in_progress_block += (
            f"\n\n## Date Review\n\n{_date_review_markdown(date_events)}"
        )
    report = f"""# Progress Update

## Period

{period_label}

## Completed

{block(_note_line(note) for note in completed)}

## In Progress

{in_progress_block}

## Evidence

{block(_evidence_lines(all_notes))}

## Blockers／Questions

{block(f'- {item}' for item in blockers if item.strip())}

## Next Steps

{block(action_lines)}

## Commitments Before Next Update

{block((f'- [ ] {item}' for item in commitments if item.strip()), '- [ ] Add commitments after review.')}
"""
    reports_dir = detect_project_root(vault, project_root) / "14_New_Role_90_Day" / "03_Progress_Reports"
    _ensure_directory(reports_dir, vault, patterns)
    stem = f"{date.today().isoformat()}-{report_type}-progress"
    output = reports_dir / f"{stem}.md"
    counter = 2
    while output.exists():
        output = reports_dir / f"{stem}-{counter}.md"
        counter += 1
    guard_local_path(output, vault, patterns)
    _atomic_write_text(output, report)
    return output


def validate_vault(vault: Path) -> list[str]:
    errors: list[str] = []
    try:
        _guard_no_symlinks(vault)
    except UnsafePathError as exc:
        return [str(exc)]
    if not vault.is_dir():
        return [f"Vault does not exist: {vault}"]
    inbox = vault / "00_Inbox"
    if not inbox.is_dir():
        errors.append("00_Inbox is missing.")
    else:
        with os.scandir(str(inbox)) as entries:
            for item in entries:
                if item.is_symlink():
                    errors.append("00_Inbox contains a symbolic link.")
                    break
                if item.is_dir(follow_symlinks=False):
                    errors.append("00_Inbox must remain flat; subdirectories were found.")
                    break
    try:
        detect_project_root(vault)
    except (UnsafePathError, VaultStructureError) as exc:
        errors.append(str(exc))
    protected_file = vault / "90_System" / "Protected_Paths.md"
    try:
        _guard_no_symlinks(protected_file)
    except UnsafePathError as exc:
        errors.append(str(exc))
    else:
        if not protected_file.is_file():
            errors.append("90_System/Protected_Paths.md is missing.")
    return errors
