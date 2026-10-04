"""Deterministic offline HTML rendering for student Portfolio presentations."""

from __future__ import annotations

import hashlib
import html
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from vitrine.path_policy import (
    PRESENTATION_DIRECTORY_MAX_LENGTH,
    PRESENTATION_FILENAME_MAX_LENGTH,
    VitrinePathPolicyError,
    require_generated_component,
)
from vitrine.portfolio_presentation import (
    STUDENT_PORTFOLIO_PRESENTATION_CLASS,
    StudentPortfolioPresentationItem,
    StudentPortfolioPresentationPreparation,
    StudentPortfolioPresentationSection,
)

STUDENT_PORTFOLIO_HTML_FILENAME: Final[str] = "portfolio.html"
STUDENT_PORTFOLIO_HTML_CONTRACT_VERSION: Final[str] = (
    "vitrine_student_portfolio_html_v1"
)
STUDENT_PORTFOLIO_HTML_RENDERER_ID: Final[str] = (
    "vitrine_student_portfolio_html_renderer"
)
STUDENT_PORTFOLIO_HTML_RENDERER_VERSION: Final[str] = "1"

_HTML_RENDERER_CONFIGURATION: Final[dict[str, object]] = {
    "contract_version": STUDENT_PORTFOLIO_HTML_CONTRACT_VERSION,
    "document_language": "en",
    "external_assets": False,
    "active_script": False,
    "image_preview_media_types": ("image/jpeg", "image/png"),
    "inline_reflection_media_types": ("text/markdown", "text/plain"),
    "optional_empty_sections": "omit",
    "required_empty_sections": "show",
}
STUDENT_PORTFOLIO_HTML_RENDERER_CONFIGURATION_SHA256: Final[str] = hashlib.sha256(
    json.dumps(
        _HTML_RENDERER_CONFIGURATION,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()

PORTFOLIO_PRESENTATION_HTML_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        "portfolio_presentation_html.invalid_preparation",
        "portfolio_presentation_html.unsafe_path",
        "portfolio_presentation_html.reflection_bytes_missing",
        "portfolio_presentation_html.reflection_text_invalid",
    }
)

_IMAGE_PREVIEW_MEDIA_TYPES: Final[frozenset[str]] = frozenset(
    {"image/jpeg", "image/png"}
)
_INLINE_REFLECTION_MEDIA_TYPES: Final[frozenset[str]] = frozenset(
    {"text/markdown", "text/plain"}
)
_MEDIA_LABELS: Final[dict[str, str]] = {
    "application/json": "JSON file",
    "application/pdf": "PDF document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": (
        "Presentation"
    ),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": (
        "Spreadsheet"
    ),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (
        "Word document"
    ),
    "image/jpeg": "Image",
    "image/png": "Image",
    "image/tiff": "Image",
    "text/markdown": "Text reflection",
    "text/plain": "Text document",
}


class PortfolioPresentationHtmlError(RuntimeError):
    """Expected deterministic student Portfolio HTML rendering failure."""

    def __init__(self, code: str, message: str, *, stage: str) -> None:
        if code not in PORTFOLIO_PRESENTATION_HTML_ERROR_CODES:
            raise ValueError(f"unsupported Portfolio HTML error code: {code}")
        super().__init__(message)
        self.code = code
        self.stage = stage


@dataclass(frozen=True, slots=True)
class StudentPortfolioHtmlRenderResult:
    filename: str
    payload: bytes
    sha256: str
    byte_size: int
    renderer_id: str
    renderer_version: str
    renderer_contract_version: str
    renderer_configuration_sha256: str


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


def _friendly_key(value: str) -> str:
    words = value.replace("_", " ").replace("-", " ").split()
    return " ".join(word.capitalize() for word in words) or "Portfolio Item"


def _safe_item_href(
    section: StudentPortfolioPresentationSection,
    item: StudentPortfolioPresentationItem,
) -> str:
    if item.presentation_filename is None:
        raise PortfolioPresentationHtmlError(
            "portfolio_presentation_html.unsafe_path",
            "Byte-bearing Portfolio item lacks a student-facing filename.",
            stage="path",
        )
    try:
        directory = require_generated_component(
            section.presentation_directory_name,
            maximum=PRESENTATION_DIRECTORY_MAX_LENGTH,
            field_name="presentation_section_directory",
        )
        filename = require_generated_component(
            item.presentation_filename,
            maximum=PRESENTATION_FILENAME_MAX_LENGTH,
            field_name="presentation_item_filename",
        )
    except VitrinePathPolicyError as error:
        raise PortfolioPresentationHtmlError(
            "portfolio_presentation_html.unsafe_path",
            "Student Portfolio HTML received an unsafe presentation path.",
            stage="path",
        ) from error
    return f"{directory}/{filename}"


def _is_inline_reflection(item: StudentPortfolioPresentationItem) -> bool:
    return (
        item.media_type in _INLINE_REFLECTION_MEDIA_TYPES
        and "reflection" in {item.content_class, item.semantic_role}
        and item.export_file_available
    )


def _inline_reflection_text(
    item: StudentPortfolioPresentationItem,
    text_payloads: Mapping[str, bytes],
) -> str:
    payload = text_payloads.get(item.entry_plan_id)
    if payload is None:
        raise PortfolioPresentationHtmlError(
            "portfolio_presentation_html.reflection_bytes_missing",
            "Exact frozen Reflection bytes are required for inline HTML presentation.",
            stage="reflection",
        )
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PortfolioPresentationHtmlError(
            "portfolio_presentation_html.reflection_text_invalid",
            "Exact frozen text Reflection is not valid UTF-8.",
            stage="reflection",
        ) from error


def _status_text(item: StudentPortfolioPresentationItem) -> str:
    if item.presentation_note:
        return item.presentation_note
    if item.disposition == "reference_only":
        return "No portable file is available for this Portfolio edition."
    if item.disposition == "omitted_permitted":
        return "This item is not included in this Portfolio edition."
    return "Open the exact Portfolio file."


def _render_item(
    section: StudentPortfolioPresentationSection,
    item: StudentPortfolioPresentationItem,
    *,
    text_payloads: Mapping[str, bytes],
) -> str:
    title = _escape(item.display_title)
    content_label = _escape(_friendly_key(item.content_class))
    caption = (
        ""
        if item.display_caption is None
        else f'<p class="item-caption">{_escape(item.display_caption)}</p>'
    )
    credit = (
        ""
        if item.source_credit is None
        else f'<p class="item-credit">{_escape(item.source_credit)}</p>'
    )

    if item.export_file_available:
        href = _safe_item_href(section, item)
        escaped_href = _escape(href)
        media_label = _escape(_MEDIA_LABELS.get(item.media_type or "", "Portfolio file"))
        preview = ""
        if item.media_type in _IMAGE_PREVIEW_MEDIA_TYPES:
            preview = (
                '<a class="work-preview image-preview" '
                f'href="{escaped_href}">'
                f'<img src="{escaped_href}" alt="{title}">'
                "</a>"
            )
        elif _is_inline_reflection(item):
            reflection = _escape(_inline_reflection_text(item, text_payloads))
            preview = (
                '<div class="work-preview reflection-preview">'
                f'<pre>{reflection}</pre>'
                "</div>"
            )
        return (
            '<article class="portfolio-item available">'
            '<div class="item-heading">'
            f'<p class="item-kind">{content_label}</p>'
            f"<h3>{title}</h3>"
            "</div>"
            f"{preview}{caption}{credit}"
            '<div class="item-actions">'
            f'<a class="open-work" href="{escaped_href}">Open {media_label}</a>'
            "</div>"
            "</article>"
        )

    status_class = (
        "reference" if item.disposition == "reference_only" else "omitted"
    )
    status_label = (
        "Reference only"
        if item.disposition == "reference_only"
        else "Not included"
    )
    return (
        f'<article class="portfolio-item {status_class}">'
        '<div class="item-heading">'
        f'<p class="item-kind">{content_label}</p>'
        f"<h3>{title}</h3>"
        "</div>"
        f"{caption}{credit}"
        '<div class="item-status">'
        f'<span class="status-pill">{_escape(status_label)}</span>'
        f"<p>{_escape(_status_text(item))}</p>"
        "</div>"
        "</article>"
    )


def _visible_sections(
    preparation: StudentPortfolioPresentationPreparation,
) -> tuple[StudentPortfolioPresentationSection, ...]:
    return tuple(
        section
        for section in preparation.sections
        if section.items or section.obligation == "required"
    )


def _render_section(
    section: StudentPortfolioPresentationSection,
    *,
    display_index: int,
    text_payloads: Mapping[str, bytes],
) -> str:
    items = "".join(
        _render_item(section, item, text_payloads=text_payloads)
        for item in section.items
    )
    if not section.items:
        items = (
            '<div class="empty-section">'
            "<p>No Portfolio items are present in this required section.</p>"
            "</div>"
        )
    return (
        f'<section class="portfolio-section" id="section-{display_index}">'
        '<div class="section-heading">'
        f'<p class="section-number">Section {display_index:02d}</p>'
        f"<h2>{_escape(section.label)}</h2>"
        f'<p class="section-purpose">{_escape(section.purpose)}</p>'
        "</div>"
        f'<div class="section-items">{items}</div>'
        "</section>"
    )


def _stylesheet() -> str:
    return """
:root {
  color-scheme: light;
  --paper: #f7f4ee;
  --surface: #ffffff;
  --ink: #18212b;
  --muted: #617080;
  --line: #d9d4ca;
  --accent: #3c5f73;
  --accent-soft: #e8f0f3;
  --shadow: 0 18px 45px rgba(24, 33, 43, 0.10);
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
    "Segoe UI", sans-serif;
  line-height: 1.6;
}
a { color: inherit; }
.skip-link {
  position: absolute;
  left: -9999px;
  top: 0;
}
.skip-link:focus {
  left: 1rem;
  top: 1rem;
  z-index: 20;
  padding: .7rem 1rem;
  background: var(--ink);
  color: white;
  border-radius: .4rem;
}
.hero {
  min-height: 54vh;
  display: grid;
  align-content: end;
  padding: clamp(3rem, 8vw, 7rem) clamp(1.4rem, 7vw, 7rem);
  background:
    radial-gradient(circle at 82% 18%, rgba(255,255,255,.17), transparent 28%),
    linear-gradient(135deg, #233847, #496b7d);
  color: white;
}
.hero-inner { max-width: 72rem; }
.eyebrow,
.section-number,
.item-kind,
.contents-title {
  margin: 0 0 .55rem;
  font-size: .76rem;
  font-weight: 750;
  letter-spacing: .12em;
  text-transform: uppercase;
}
.hero h1 {
  max-width: 13ch;
  margin: 0;
  font-family: ui-serif, Georgia, Cambria, "Times New Roman", serif;
  font-size: clamp(3rem, 8vw, 6.6rem);
  font-weight: 500;
  line-height: .96;
  letter-spacing: -.035em;
}
.student-name {
  margin: 1.5rem 0 0;
  font-size: clamp(1.35rem, 3vw, 2.2rem);
  font-weight: 650;
}
.hero-purpose {
  max-width: 46rem;
  margin: 1.1rem 0 0;
  color: rgba(255,255,255,.82);
  font-size: 1.02rem;
}
.contents {
  max-width: 72rem;
  margin: -2rem auto 4rem;
  padding: 1.4rem;
  position: relative;
  background: var(--surface);
  border: 1px solid rgba(24,33,43,.08);
  border-radius: 1rem;
  box-shadow: var(--shadow);
}
.contents ol {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
  gap: .75rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.contents a {
  display: block;
  min-height: 100%;
  padding: .95rem 1rem;
  background: var(--paper);
  border-radius: .65rem;
  text-decoration: none;
  font-weight: 650;
}
.contents a:hover,
.contents a:focus-visible { background: var(--accent-soft); }
main {
  max-width: 72rem;
  margin: 0 auto;
  padding: 0 1.4rem 6rem;
}
.portfolio-section {
  padding: 4rem 0 4.5rem;
  border-top: 1px solid var(--line);
}
.section-heading {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(16rem, .85fr);
  column-gap: 3rem;
  align-items: end;
  margin-bottom: 2rem;
}
.section-number {
  grid-column: 1 / -1;
  color: var(--accent);
}
.section-heading h2 {
  margin: 0;
  font-family: ui-serif, Georgia, Cambria, "Times New Roman", serif;
  font-size: clamp(2rem, 5vw, 3.6rem);
  font-weight: 500;
  line-height: 1.04;
  letter-spacing: -.025em;
}
.section-purpose {
  margin: 0;
  color: var(--muted);
}
.section-items { display: grid; gap: 1.15rem; }
.portfolio-item {
  overflow: hidden;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: .9rem;
  box-shadow: 0 5px 18px rgba(24,33,43,.045);
}
.item-heading { padding: 1.25rem 1.35rem .35rem; }
.item-kind { color: var(--accent); }
.portfolio-item h3 {
  margin: 0;
  font-family: ui-serif, Georgia, Cambria, "Times New Roman", serif;
  font-size: clamp(1.45rem, 3vw, 2.1rem);
  font-weight: 550;
  line-height: 1.12;
}
.item-caption,
.item-credit {
  max-width: 54rem;
  margin: .7rem 1.35rem 0;
}
.item-credit {
  color: var(--muted);
  font-size: .9rem;
}
.work-preview {
  display: block;
  margin: 1rem 1.35rem 0;
  border-radius: .65rem;
  overflow: hidden;
  background: #eef1f2;
}
.image-preview img {
  display: block;
  width: 100%;
  max-height: 46rem;
  object-fit: contain;
  background: #e8ecee;
}
.reflection-preview { padding: 1.35rem; }
.reflection-preview pre {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font: inherit;
  line-height: 1.75;
}
.item-actions { padding: 1.25rem 1.35rem 1.35rem; }
.open-work {
  display: inline-block;
  padding: .7rem 1rem;
  border-radius: .5rem;
  background: var(--ink);
  color: white;
  text-decoration: none;
  font-weight: 700;
}
.open-work:hover,
.open-work:focus-visible { background: var(--accent); }
.item-status {
  margin: .9rem 1.35rem 1.35rem;
  padding: 1rem;
  background: var(--paper);
  border-radius: .65rem;
}
.item-status p { margin: .55rem 0 0; color: var(--muted); }
.status-pill {
  display: inline-block;
  padding: .2rem .55rem;
  border-radius: 999px;
  background: var(--accent-soft);
  color: #284454;
  font-size: .78rem;
  font-weight: 750;
}
.omitted { opacity: .82; }
.empty-section {
  padding: 1.2rem 1.35rem;
  border: 1px dashed var(--line);
  border-radius: .8rem;
  color: var(--muted);
}
.footer {
  padding: 2.5rem 1.4rem 3.5rem;
  text-align: center;
  color: var(--muted);
  border-top: 1px solid var(--line);
}
.footer p { margin: 0; }
@media (max-width: 720px) {
  .hero { min-height: 46vh; }
  .contents { margin: -1.2rem 1rem 3rem; }
  .section-heading { grid-template-columns: 1fr; gap: .9rem; }
}
@media print {
  body { background: white; }
  .hero {
    min-height: 8.5in;
    padding: .8in;
    background: white;
    color: black;
    page-break-after: always;
  }
  .hero-purpose { color: #444; }
  .contents { display: none; }
  main { max-width: none; padding: 0; }
  .portfolio-section { padding: .55in 0; break-before: page; }
  .portfolio-item { box-shadow: none; break-inside: avoid; }
  .open-work { border: 1px solid #333; background: white; color: black; }
  .footer { display: none; }
}
""".strip()


def render_student_portfolio_html(
    preparation: StudentPortfolioPresentationPreparation,
    *,
    text_payloads_by_entry_plan: Mapping[str, bytes] | None = None,
) -> StudentPortfolioHtmlRenderResult:
    """Render one deterministic, offline, student-facing Portfolio HTML document."""

    if not isinstance(preparation, StudentPortfolioPresentationPreparation):
        raise PortfolioPresentationHtmlError(
            "portfolio_presentation_html.invalid_preparation",
            "Student Portfolio HTML requires exact presentation preparation.",
            stage="request",
        )
    if preparation.presentation_class != STUDENT_PORTFOLIO_PRESENTATION_CLASS:
        raise PortfolioPresentationHtmlError(
            "portfolio_presentation_html.invalid_preparation",
            "Prepared presentation is not a student_portfolio output.",
            stage="request",
        )
    payloads: Mapping[str, bytes] = (
        {} if text_payloads_by_entry_plan is None else text_payloads_by_entry_plan
    )
    if any(not isinstance(value, bytes) for value in payloads.values()):
        raise PortfolioPresentationHtmlError(
            "portfolio_presentation_html.invalid_preparation",
            "Inline Portfolio text payloads must be exact bytes.",
            stage="request",
        )
    try:
        filename = require_generated_component(
            STUDENT_PORTFOLIO_HTML_FILENAME,
            maximum=PRESENTATION_FILENAME_MAX_LENGTH,
            field_name="student_portfolio_html_filename",
        )
    except VitrinePathPolicyError as error:
        raise PortfolioPresentationHtmlError(
            "portfolio_presentation_html.unsafe_path",
            "Student Portfolio HTML filename is not portable.",
            stage="path",
        ) from error

    sections = _visible_sections(preparation)
    nav_items = "".join(
        f'<li><a href="#section-{index}">{_escape(section.label)}</a></li>'
        for index, section in enumerate(sections, start=1)
    )
    section_markup = "".join(
        _render_section(
            section,
            display_index=index,
            text_payloads=payloads,
        )
        for index, section in enumerate(sections, start=1)
    )
    student_name = (
        ""
        if preparation.student_display_name is None
        else f'<p class="student-name">{_escape(preparation.student_display_name)}</p>'
    )
    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_escape(preparation.portfolio_title)}</title>
<style>
{_stylesheet()}
</style>
</head>
<body>
<a class="skip-link" href="#portfolio-content">Skip to Portfolio</a>
<header class="hero">
  <div class="hero-inner">
    <p class="eyebrow">{_escape(preparation.profile_label)}</p>
    <h1>{_escape(preparation.portfolio_title)}</h1>
    {student_name}
    <p class="hero-purpose">{_escape(preparation.purpose)}</p>
  </div>
</header>
<nav class="contents" aria-label="Portfolio sections">
  <p class="contents-title">Portfolio contents</p>
  <ol>{nav_items}</ol>
</nav>
<main id="portfolio-content">
{section_markup}
</main>
<footer class="footer">
  <p>A personal Portfolio of selected work and reflection.</p>
</footer>
</body>
</html>
"""
    payload = document.encode("utf-8")
    return StudentPortfolioHtmlRenderResult(
        filename=filename,
        payload=payload,
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_size=len(payload),
        renderer_id=STUDENT_PORTFOLIO_HTML_RENDERER_ID,
        renderer_version=STUDENT_PORTFOLIO_HTML_RENDERER_VERSION,
        renderer_contract_version=STUDENT_PORTFOLIO_HTML_CONTRACT_VERSION,
        renderer_configuration_sha256=(
            STUDENT_PORTFOLIO_HTML_RENDERER_CONFIGURATION_SHA256
        ),
    )


__all__ = [
    "PORTFOLIO_PRESENTATION_HTML_ERROR_CODES",
    "STUDENT_PORTFOLIO_HTML_CONTRACT_VERSION",
    "STUDENT_PORTFOLIO_HTML_FILENAME",
    "STUDENT_PORTFOLIO_HTML_RENDERER_CONFIGURATION_SHA256",
    "STUDENT_PORTFOLIO_HTML_RENDERER_ID",
    "STUDENT_PORTFOLIO_HTML_RENDERER_VERSION",
    "PortfolioPresentationHtmlError",
    "StudentPortfolioHtmlRenderResult",
    "render_student_portfolio_html",
]
