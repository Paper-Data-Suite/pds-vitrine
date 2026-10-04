"""Deterministic binder-ready PDF rendering for student Portfolio presentations."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
from collections.abc import Mapping
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Final

from vitrine.path_policy import (
    VitrinePathPolicyError,
    build_bounded_presentation_filename,
)
from vitrine.portfolio_presentation import (
    STUDENT_PORTFOLIO_PRESENTATION_CLASS,
    StudentPortfolioPresentationItem,
    StudentPortfolioPresentationPreparation,
    StudentPortfolioPresentationSection,
)

STUDENT_PORTFOLIO_PDF_CONTRACT_VERSION: Final[str] = (
    "vitrine_student_portfolio_pdf_v1"
)
STUDENT_PORTFOLIO_PDF_RENDERER_ID: Final[str] = (
    "vitrine_student_portfolio_pdf_renderer"
)
STUDENT_PORTFOLIO_PDF_RENDERER_VERSION: Final[str] = "1"
STUDENT_PORTFOLIO_PDF_FILENAME_DOMAIN: Final[str] = "student-portfolio-printable-pdf"

PDF_PRINT_DISPOSITIONS: Final[frozenset[str]] = frozenset(
    {
        "rendered_from_exact_source",
        "digital_attachment_only",
        "reference_only",
        "omitted_permitted",
    }
)
PORTFOLIO_PRESENTATION_PDF_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        "portfolio_presentation_pdf.invalid_preparation",
        "portfolio_presentation_pdf.renderer_unavailable",
        "portfolio_presentation_pdf.unsafe_filename",
        "portfolio_presentation_pdf.source_missing",
        "portfolio_presentation_pdf.source_invalid",
        "portfolio_presentation_pdf.text_invalid",
        "portfolio_presentation_pdf.render_failed",
    }
)

_RENDER_DPI: Final[int] = 144
_PAGE_WIDTH_POINTS: Final[float] = 612.0
_PAGE_HEIGHT_POINTS: Final[float] = 792.0
_MARGIN_POINTS: Final[float] = 54.0
_ITEM_HEADER_HEIGHT_POINTS: Final[float] = 92.0
_SUPPORTED_RENDER_MEDIA_TYPES: Final[frozenset[str]] = frozenset(
    {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/tiff",
        "text/markdown",
        "text/plain",
    }
)
_TEXT_MEDIA_TYPES: Final[frozenset[str]] = frozenset(
    {"text/markdown", "text/plain"}
)
_IMAGE_MEDIA_TYPES: Final[frozenset[str]] = frozenset(
    {"image/jpeg", "image/png", "image/tiff"}
)
_RENDERER_CONFIGURATION_BASE: Final[dict[str, object]] = {
    "contract_version": STUDENT_PORTFOLIO_PDF_CONTRACT_VERSION,
    "page_size": "letter",
    "page_width_points": _PAGE_WIDTH_POINTS,
    "page_height_points": _PAGE_HEIGHT_POINTS,
    "margin_points": _MARGIN_POINTS,
    "item_header_height_points": _ITEM_HEADER_HEIGHT_POINTS,
    "pdf_source_render_dpi": _RENDER_DPI,
    "markdown_treatment": "literal_plain_text",
    "text_encoding": "utf-8",
    "standard_font_encoding": "windows-1252",
    "supported_render_media_types": tuple(sorted(_SUPPORTED_RENDER_MEDIA_TYPES)),
    "unsupported_byte_item_treatment": "digital_attachment_only",
    "reference_only_treatment": "visible_status_page",
    "omitted_permitted_treatment": "machine_manifest_only",
    "reportlab_invariant": True,
}


class PortfolioPresentationPdfError(RuntimeError):
    """Expected deterministic student Portfolio PDF rendering failure."""

    def __init__(self, code: str, message: str, *, stage: str) -> None:
        if code not in PORTFOLIO_PRESENTATION_PDF_ERROR_CODES:
            raise ValueError(f"unsupported Portfolio PDF error code: {code}")
        super().__init__(message)
        self.code = code
        self.stage = stage


@dataclass(frozen=True, slots=True)
class StudentPortfolioPdfItemDisposition:
    entry_plan_id: str
    print_disposition: str
    page_count: int

    def __post_init__(self) -> None:
        if self.print_disposition not in PDF_PRINT_DISPOSITIONS:
            raise ValueError("unsupported student Portfolio PDF print disposition")
        if self.page_count < 0:
            raise ValueError("student Portfolio PDF page_count must be nonnegative")


@dataclass(frozen=True, slots=True)
class StudentPortfolioPdfRenderResult:
    filename: str
    payload: bytes
    sha256: str
    byte_size: int
    page_count: int
    renderer_id: str
    renderer_version: str
    renderer_contract_version: str
    renderer_configuration_sha256: str
    item_dispositions: tuple[StudentPortfolioPdfItemDisposition, ...]


@dataclass(frozen=True, slots=True)
class _RendererDependencies:
    canvas_type: Any
    image_reader_type: Any
    pdfium: Any
    pil_image: Any
    pil_image_sequence: Any
    package_versions: dict[str, str]


def _load_renderer_dependencies() -> _RendererDependencies:
    try:
        import pypdfium2 as pdfium
        from PIL import Image, ImageSequence
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen.canvas import Canvas
    except ImportError as error:
        raise PortfolioPresentationPdfError(
            "portfolio_presentation_pdf.renderer_unavailable",
            "Printable Portfolio rendering requires the Vitrine paper dependencies.",
            stage="dependencies",
        ) from error

    versions: dict[str, str] = {}
    for distribution in ("reportlab", "pypdfium2", "Pillow"):
        try:
            versions[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError as error:
            raise PortfolioPresentationPdfError(
                "portfolio_presentation_pdf.renderer_unavailable",
                "Printable Portfolio renderer dependency metadata is unavailable.",
                stage="dependencies",
            ) from error
    return _RendererDependencies(
        canvas_type=Canvas,
        image_reader_type=ImageReader,
        pdfium=pdfium,
        pil_image=Image,
        pil_image_sequence=ImageSequence,
        package_versions=versions,
    )


def _configuration_sha256(dependencies: _RendererDependencies) -> str:
    value = {
        **_RENDERER_CONFIGURATION_BASE,
        "dependency_versions": dependencies.package_versions,
    }
    payload = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _display_label(preparation: StudentPortfolioPresentationPreparation) -> str:
    if preparation.student_display_name:
        return f"{preparation.student_display_name} - {preparation.portfolio_title}"
    return preparation.portfolio_title


def _build_filename(
    preparation: StudentPortfolioPresentationPreparation,
    *,
    presentation_artifact_id: str,
) -> str:
    try:
        return build_bounded_presentation_filename(
            _display_label(preparation),
            semantic_domain=STUDENT_PORTFOLIO_PDF_FILENAME_DOMAIN,
            semantic_identity={
                "presentation_artifact_id": presentation_artifact_id,
                "snapshot_series_id": (
                    preparation.snapshot_edition.snapshot_series_id
                ),
                "edition_number": preparation.snapshot_edition.edition_number,
                "presentation_contract_version": preparation.contract_version,
                "pdf_contract_version": STUDENT_PORTFOLIO_PDF_CONTRACT_VERSION,
            },
            extension=".pdf",
        )
    except VitrinePathPolicyError as error:
        raise PortfolioPresentationPdfError(
            "portfolio_presentation_pdf.unsafe_filename",
            "Printable Portfolio filename could not be bounded safely.",
            stage="filename",
        ) from error


def _require_pdf_text(value: str, *, field_name: str) -> str:
    try:
        value.encode("cp1252")
    except UnicodeEncodeError as error:
        raise PortfolioPresentationPdfError(
            "portfolio_presentation_pdf.text_invalid",
            f"{field_name} contains text outside the renderer's exact font encoding.",
            stage="text",
        ) from error
    return value


def _wrap_words(
    text: str,
    *,
    width_points: float,
    font_name: str,
    font_size: float,
    string_width: Any,
) -> tuple[str, ...]:
    if not text:
        return ("",)
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if string_width(candidate, font_name, font_size) <= width_points:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = ""
        remaining = word
        while remaining and string_width(
            remaining, font_name, font_size
        ) > width_points:
            split = len(remaining)
            while split > 1 and string_width(
                remaining[:split], font_name, font_size
            ) > width_points:
                split -= 1
            if split == 1 and string_width(
                remaining[:1], font_name, font_size
            ) > width_points:
                raise PortfolioPresentationPdfError(
                    "portfolio_presentation_pdf.text_invalid",
                    "Printable Portfolio text contains a glyph that cannot fit safely.",
                    stage="text",
                )
            lines.append(remaining[:split])
            remaining = remaining[split:]
        current = remaining
    if current or not lines:
        lines.append(current)
    return tuple(lines)


def _wrap_preserving_newlines(
    text: str,
    *,
    width_points: float,
    font_name: str,
    font_size: float,
    string_width: Any,
) -> tuple[str, ...]:
    lines: list[str] = []
    for logical_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not logical_line:
            lines.append("")
            continue
        lines.extend(
            _wrap_words(
                logical_line,
                width_points=width_points,
                font_name=font_name,
                font_size=font_size,
                string_width=string_width,
            )
        )
    return tuple(lines) or ("",)


def _set_fill_rgb(pdf: Any, red: float, green: float, blue: float) -> None:
    pdf.setFillColorRGB(red, green, blue)


def _draw_footer(pdf: Any, page_number: int) -> None:
    _set_fill_rgb(pdf, 0.37, 0.42, 0.46)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(_MARGIN_POINTS, 28, "Student Portfolio")
    pdf.drawRightString(
        _PAGE_WIDTH_POINTS - _MARGIN_POINTS,
        28,
        f"Page {page_number}",
    )


def _show_page(pdf: Any, page_number: int, *, footer: bool = True) -> int:
    if footer:
        _draw_footer(pdf, page_number)
    pdf.showPage()
    return page_number + 1


def _draw_cover(
    pdf: Any,
    preparation: StudentPortfolioPresentationPreparation,
    *,
    string_width: Any,
) -> None:
    _set_fill_rgb(pdf, 0.13, 0.22, 0.28)
    pdf.rect(0, 0, _PAGE_WIDTH_POINTS, _PAGE_HEIGHT_POINTS, fill=1, stroke=0)
    _set_fill_rgb(pdf, 1.0, 1.0, 1.0)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(
        _MARGIN_POINTS,
        _PAGE_HEIGHT_POINTS - 82,
        _require_pdf_text(preparation.profile_label.upper(), field_name="Profile label"),
    )
    title = _require_pdf_text(preparation.portfolio_title, field_name="Portfolio title")
    title_lines = _wrap_words(
        title,
        width_points=_PAGE_WIDTH_POINTS - 2 * _MARGIN_POINTS,
        font_name="Times-Roman",
        font_size=34,
        string_width=string_width,
    )
    y = _PAGE_HEIGHT_POINTS - 170
    pdf.setFont("Times-Roman", 34)
    for line in title_lines:
        pdf.drawString(_MARGIN_POINTS, y, line)
        y -= 39
    if preparation.student_display_name:
        y -= 14
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(
            _MARGIN_POINTS,
            y,
            _require_pdf_text(
                preparation.student_display_name,
                field_name="Student display name",
            ),
        )
        y -= 30
    purpose = _require_pdf_text(preparation.purpose, field_name="Portfolio purpose")
    purpose_lines = _wrap_words(
        purpose,
        width_points=380,
        font_name="Helvetica",
        font_size=11,
        string_width=string_width,
    )
    pdf.setFont("Helvetica", 11)
    _set_fill_rgb(pdf, 0.86, 0.90, 0.92)
    for line in purpose_lines:
        pdf.drawString(_MARGIN_POINTS, y, line)
        y -= 15
    _set_fill_rgb(pdf, 1.0, 1.0, 1.0)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(_MARGIN_POINTS, 54, "Selected work, reflection, and growth")


def _visible_items(
    section: StudentPortfolioPresentationSection,
) -> tuple[StudentPortfolioPresentationItem, ...]:
    return tuple(
        item for item in section.items if item.disposition != "omitted_permitted"
    )


def _visible_sections(
    preparation: StudentPortfolioPresentationPreparation,
) -> tuple[StudentPortfolioPresentationSection, ...]:
    return tuple(
        section
        for section in preparation.sections
        if _visible_items(section) or section.obligation == "required"
    )


def _draw_contents(
    pdf: Any,
    sections: tuple[StudentPortfolioPresentationSection, ...],
    *,
    string_width: Any,
) -> None:
    _set_fill_rgb(pdf, 0.10, 0.13, 0.16)
    pdf.setFont("Times-Bold", 30)
    pdf.drawString(_MARGIN_POINTS, 700, "Portfolio Contents")
    y = 644.0
    for index, section in enumerate(sections, start=1):
        label = _require_pdf_text(section.label, field_name="Section label")
        purpose = _require_pdf_text(section.purpose, field_name="Section purpose")
        pdf.setFont("Helvetica-Bold", 10)
        _set_fill_rgb(pdf, 0.23, 0.37, 0.45)
        pdf.drawString(_MARGIN_POINTS, y, f"SECTION {index:02d}")
        y -= 22
        pdf.setFont("Times-Bold", 18)
        _set_fill_rgb(pdf, 0.10, 0.13, 0.16)
        for line in _wrap_words(
            label,
            width_points=430,
            font_name="Times-Bold",
            font_size=18,
            string_width=string_width,
        ):
            pdf.drawString(_MARGIN_POINTS, y, line)
            y -= 21
        pdf.setFont("Helvetica", 9)
        _set_fill_rgb(pdf, 0.37, 0.42, 0.46)
        for line in _wrap_words(
            purpose,
            width_points=430,
            font_name="Helvetica",
            font_size=9,
            string_width=string_width,
        )[:2]:
            pdf.drawString(_MARGIN_POINTS, y, line)
            y -= 12
        y -= 22
        if y < 100:
            break


def _draw_section_divider(
    pdf: Any,
    section: StudentPortfolioPresentationSection,
    *,
    display_index: int,
    string_width: Any,
) -> None:
    _set_fill_rgb(pdf, 0.94, 0.93, 0.90)
    pdf.rect(0, 0, _PAGE_WIDTH_POINTS, _PAGE_HEIGHT_POINTS, fill=1, stroke=0)
    _set_fill_rgb(pdf, 0.23, 0.37, 0.45)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(_MARGIN_POINTS, 674, f"SECTION {display_index:02d}")
    label = _require_pdf_text(section.label, field_name="Section label")
    pdf.setFont("Times-Bold", 32)
    _set_fill_rgb(pdf, 0.10, 0.13, 0.16)
    y = 626.0
    for line in _wrap_words(
        label,
        width_points=470,
        font_name="Times-Bold",
        font_size=32,
        string_width=string_width,
    ):
        pdf.drawString(_MARGIN_POINTS, y, line)
        y -= 38
    y -= 10
    purpose = _require_pdf_text(section.purpose, field_name="Section purpose")
    pdf.setFont("Helvetica", 11)
    _set_fill_rgb(pdf, 0.32, 0.36, 0.39)
    for line in _wrap_words(
        purpose,
        width_points=410,
        font_name="Helvetica",
        font_size=11,
        string_width=string_width,
    ):
        pdf.drawString(_MARGIN_POINTS, y, line)
        y -= 15


def _item_kind(item: StudentPortfolioPresentationItem) -> str:
    words = item.content_class.replace("_", " ").replace("-", " ").split()
    return " ".join(word.capitalize() for word in words) or "Portfolio Item"


def _draw_item_heading(
    pdf: Any,
    section: StudentPortfolioPresentationSection,
    item: StudentPortfolioPresentationItem,
    *,
    source_page_label: str | None,
    string_width: Any,
) -> float:
    _set_fill_rgb(pdf, 0.23, 0.37, 0.45)
    pdf.setFont("Helvetica-Bold", 8)
    heading = f"{section.label} / {_item_kind(item)}"
    pdf.drawString(
        _MARGIN_POINTS,
        742,
        _require_pdf_text(heading.upper(), field_name="Item heading"),
    )
    title = _require_pdf_text(item.display_title, field_name="Item title")
    pdf.setFont("Times-Bold", 20)
    _set_fill_rgb(pdf, 0.10, 0.13, 0.16)
    y = 714.0
    for line in _wrap_words(
        title,
        width_points=470,
        font_name="Times-Bold",
        font_size=20,
        string_width=string_width,
    )[:2]:
        pdf.drawString(_MARGIN_POINTS, y, line)
        y -= 23
    if source_page_label:
        pdf.setFont("Helvetica", 8)
        _set_fill_rgb(pdf, 0.37, 0.42, 0.46)
        pdf.drawRightString(
            _PAGE_WIDTH_POINTS - _MARGIN_POINTS,
            742,
            _require_pdf_text(source_page_label, field_name="Source page label"),
        )
    if item.display_caption:
        caption = _require_pdf_text(item.display_caption, field_name="Item caption")
        pdf.setFont("Helvetica", 9)
        _set_fill_rgb(pdf, 0.32, 0.36, 0.39)
        for line in _wrap_words(
            caption,
            width_points=470,
            font_name="Helvetica",
            font_size=9,
            string_width=string_width,
        )[:2]:
            pdf.drawString(_MARGIN_POINTS, y, line)
            y -= 12
    pdf.setStrokeColorRGB(0.82, 0.82, 0.80)
    pdf.line(_MARGIN_POINTS, y - 7, _PAGE_WIDTH_POINTS - _MARGIN_POINTS, y - 7)
    return y - 22


def _draw_status_page(
    pdf: Any,
    section: StudentPortfolioPresentationSection,
    item: StudentPortfolioPresentationItem,
    *,
    title: str,
    message: str,
    string_width: Any,
) -> None:
    y = _draw_item_heading(
        pdf,
        section,
        item,
        source_page_label=None,
        string_width=string_width,
    )
    _set_fill_rgb(pdf, 0.94, 0.93, 0.90)
    pdf.roundRect(
        _MARGIN_POINTS,
        y - 138,
        _PAGE_WIDTH_POINTS - 2 * _MARGIN_POINTS,
        116,
        8,
        fill=1,
        stroke=0,
    )
    _set_fill_rgb(pdf, 0.10, 0.13, 0.16)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(
        _MARGIN_POINTS + 18,
        y - 54,
        _require_pdf_text(title, field_name="Status title"),
    )
    pdf.setFont("Helvetica", 10)
    for index, line in enumerate(
        _wrap_words(
            _require_pdf_text(message, field_name="Status message"),
            width_points=430,
            font_name="Helvetica",
            font_size=10,
            string_width=string_width,
        )[:4]
    ):
        pdf.drawString(_MARGIN_POINTS + 18, y - 78 - (index * 14), line)


def _draw_pil_image(
    pdf: Any,
    image_reader_type: Any,
    image: Any,
    *,
    top_y: float,
) -> None:
    width = float(image.width)
    height = float(image.height)
    if width <= 0 or height <= 0:
        raise PortfolioPresentationPdfError(
            "portfolio_presentation_pdf.source_invalid",
            "Printable Portfolio image has invalid dimensions.",
            stage="image",
        )
    available_width = _PAGE_WIDTH_POINTS - 2 * _MARGIN_POINTS
    available_height = top_y - 58.0
    scale = min(available_width / width, available_height / height)
    draw_width = width * scale
    draw_height = height * scale
    x = (_PAGE_WIDTH_POINTS - draw_width) / 2
    y = 48 + (available_height - draw_height) / 2
    pdf.drawImage(
        image_reader_type(image),
        x,
        y,
        width=draw_width,
        height=draw_height,
        preserveAspectRatio=True,
        anchor="c",
        mask="auto",
    )


def _render_pdf_source(
    pdf: Any,
    dependencies: _RendererDependencies,
    section: StudentPortfolioPresentationSection,
    item: StudentPortfolioPresentationItem,
    payload: bytes,
    *,
    page_number: int,
    string_width: Any,
) -> tuple[int, int]:
    try:
        document = dependencies.pdfium.PdfDocument(payload)
        source_page_count = len(document)
        if source_page_count < 1:
            raise ValueError("PDF contains no pages")
        pages_added = 0
        for source_index in range(source_page_count):
            page = document[source_index]
            bitmap = None
            image = None
            try:
                bitmap = page.render(scale=_RENDER_DPI / 72.0)
                image = bitmap.to_pil().convert("RGB")
                top_y = _draw_item_heading(
                    pdf,
                    section,
                    item,
                    source_page_label=(
                        f"Source page {source_index + 1} of {source_page_count}"
                    ),
                    string_width=string_width,
                )
                _draw_pil_image(
                    pdf,
                    dependencies.image_reader_type,
                    image,
                    top_y=top_y,
                )
                page_number = _show_page(pdf, page_number)
                pages_added += 1
            finally:
                if image is not None:
                    image.close()
                if bitmap is not None:
                    bitmap.close()
                page.close()
        document.close()
        return page_number, pages_added
    except PortfolioPresentationPdfError:
        raise
    except Exception as error:
        raise PortfolioPresentationPdfError(
            "portfolio_presentation_pdf.source_invalid",
            "Exact frozen PDF source could not be rendered safely.",
            stage="pdf_source",
        ) from error


def _render_image_source(
    pdf: Any,
    dependencies: _RendererDependencies,
    section: StudentPortfolioPresentationSection,
    item: StudentPortfolioPresentationItem,
    payload: bytes,
    *,
    page_number: int,
    string_width: Any,
) -> tuple[int, int]:
    try:
        source = dependencies.pil_image.open(BytesIO(payload))
        frames = tuple(frame.copy().convert("RGB") for frame in dependencies.pil_image_sequence.Iterator(source))
        source.close()
        if not frames:
            raise ValueError("image contains no frames")
        pages_added = 0
        for index, image in enumerate(frames, start=1):
            try:
                label = None if len(frames) == 1 else f"Image page {index} of {len(frames)}"
                top_y = _draw_item_heading(
                    pdf,
                    section,
                    item,
                    source_page_label=label,
                    string_width=string_width,
                )
                _draw_pil_image(
                    pdf,
                    dependencies.image_reader_type,
                    image,
                    top_y=top_y,
                )
                page_number = _show_page(pdf, page_number)
                pages_added += 1
            finally:
                image.close()
        return page_number, pages_added
    except PortfolioPresentationPdfError:
        raise
    except Exception as error:
        raise PortfolioPresentationPdfError(
            "portfolio_presentation_pdf.source_invalid",
            "Exact frozen image source could not be rendered safely.",
            stage="image_source",
        ) from error


def _render_text_source(
    pdf: Any,
    section: StudentPortfolioPresentationSection,
    item: StudentPortfolioPresentationItem,
    payload: bytes,
    *,
    page_number: int,
    string_width: Any,
) -> tuple[int, int]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PortfolioPresentationPdfError(
            "portfolio_presentation_pdf.text_invalid",
            "Exact frozen text source is not valid UTF-8.",
            stage="text_source",
        ) from error
    _require_pdf_text(text, field_name="Exact Portfolio text")
    logical_lines = _wrap_preserving_newlines(
        text,
        width_points=_PAGE_WIDTH_POINTS - 2 * _MARGIN_POINTS,
        font_name="Helvetica",
        font_size=10,
        string_width=string_width,
    )
    pages_added = 0
    line_index = 0
    while line_index < len(logical_lines) or pages_added == 0:
        y = _draw_item_heading(
            pdf,
            section,
            item,
            source_page_label=None,
            string_width=string_width,
        )
        pdf.setFont("Helvetica", 10)
        _set_fill_rgb(pdf, 0.10, 0.13, 0.16)
        while line_index < len(logical_lines) and y >= 62:
            pdf.drawString(_MARGIN_POINTS, y, logical_lines[line_index])
            y -= 14
            line_index += 1
        page_number = _show_page(pdf, page_number)
        pages_added += 1
    return page_number, pages_added


def _render_byte_item(
    pdf: Any,
    dependencies: _RendererDependencies,
    section: StudentPortfolioPresentationSection,
    item: StudentPortfolioPresentationItem,
    payload: bytes,
    *,
    page_number: int,
    string_width: Any,
) -> tuple[int, StudentPortfolioPdfItemDisposition]:
    media_type = item.media_type or ""
    if media_type == "application/pdf":
        page_number, page_count = _render_pdf_source(
            pdf,
            dependencies,
            section,
            item,
            payload,
            page_number=page_number,
            string_width=string_width,
        )
        disposition = "rendered_from_exact_source"
    elif media_type in _IMAGE_MEDIA_TYPES:
        page_number, page_count = _render_image_source(
            pdf,
            dependencies,
            section,
            item,
            payload,
            page_number=page_number,
            string_width=string_width,
        )
        disposition = "rendered_from_exact_source"
    elif media_type in _TEXT_MEDIA_TYPES:
        page_number, page_count = _render_text_source(
            pdf,
            section,
            item,
            payload,
            page_number=page_number,
            string_width=string_width,
        )
        disposition = "rendered_from_exact_source"
    else:
        filename = item.presentation_filename or "the digital Portfolio file"
        _draw_status_page(
            pdf,
            section,
            item,
            title="Digital attachment",
            message=(
                "This item is preserved in the digital Portfolio as "
                f"{filename}, but its media type is not rendered into the "
                "printable packet."
            ),
            string_width=string_width,
        )
        page_number = _show_page(pdf, page_number)
        page_count = 1
        disposition = "digital_attachment_only"
    return page_number, StudentPortfolioPdfItemDisposition(
        entry_plan_id=item.entry_plan_id,
        print_disposition=disposition,
        page_count=page_count,
    )


def render_student_portfolio_pdf(
    preparation: StudentPortfolioPresentationPreparation,
    *,
    presentation_artifact_id: str,
    source_payloads_by_entry_plan: Mapping[str, bytes],
) -> StudentPortfolioPdfRenderResult:
    """Render one deterministic letter-size printable student Portfolio packet."""

    if not isinstance(preparation, StudentPortfolioPresentationPreparation):
        raise PortfolioPresentationPdfError(
            "portfolio_presentation_pdf.invalid_preparation",
            "Printable Portfolio requires exact presentation preparation.",
            stage="request",
        )
    if preparation.presentation_class != STUDENT_PORTFOLIO_PRESENTATION_CLASS:
        raise PortfolioPresentationPdfError(
            "portfolio_presentation_pdf.invalid_preparation",
            "Prepared presentation is not a student_portfolio output.",
            stage="request",
        )
    if not isinstance(presentation_artifact_id, str) or not presentation_artifact_id:
        raise PortfolioPresentationPdfError(
            "portfolio_presentation_pdf.invalid_preparation",
            "Printable Portfolio requires a presentation artifact identity.",
            stage="request",
        )
    if any(not isinstance(value, bytes) for value in source_payloads_by_entry_plan.values()):
        raise PortfolioPresentationPdfError(
            "portfolio_presentation_pdf.invalid_preparation",
            "Printable Portfolio source payloads must be exact bytes.",
            stage="request",
        )

    for section in preparation.sections:
        for item in section.items:
            if item.export_file_available and item.entry_plan_id not in source_payloads_by_entry_plan:
                raise PortfolioPresentationPdfError(
                    "portfolio_presentation_pdf.source_missing",
                    "Printable Portfolio is missing exact frozen source bytes.",
                    stage="source",
                )

    dependencies = _load_renderer_dependencies()
    configuration_sha256 = _configuration_sha256(dependencies)
    filename = _build_filename(
        preparation,
        presentation_artifact_id=presentation_artifact_id,
    )

    try:
        from reportlab.pdfbase.pdfmetrics import stringWidth

        output = BytesIO()
        pdf = dependencies.canvas_type(
            output,
            pagesize=(_PAGE_WIDTH_POINTS, _PAGE_HEIGHT_POINTS),
            invariant=1,
            pageCompression=1,
        )
        pdf.setTitle("Student Portfolio")
        pdf.setCreator(STUDENT_PORTFOLIO_PDF_RENDERER_ID)
        pdf.setSubject("Printable student Portfolio")

        page_number = 1
        _draw_cover(pdf, preparation, string_width=stringWidth)
        page_number = _show_page(pdf, page_number, footer=False)

        sections = _visible_sections(preparation)
        _draw_contents(pdf, sections, string_width=stringWidth)
        page_number = _show_page(pdf, page_number)

        outcomes_by_entry_plan: dict[str, StudentPortfolioPdfItemDisposition] = {}
        for display_index, section in enumerate(sections, start=1):
            _draw_section_divider(
                pdf,
                section,
                display_index=display_index,
                string_width=stringWidth,
            )
            page_number = _show_page(pdf, page_number)
            visible_items = _visible_items(section)
            if not visible_items:
                continue
            for item in visible_items:
                if item.disposition == "reference_only":
                    _draw_status_page(
                        pdf,
                        section,
                        item,
                        title="Reference only",
                        message=(
                            item.presentation_note
                            or "No portable file is available for this Portfolio edition."
                        ),
                        string_width=stringWidth,
                    )
                    page_number = _show_page(pdf, page_number)
                    outcomes_by_entry_plan[item.entry_plan_id] = (
                        StudentPortfolioPdfItemDisposition(
                            entry_plan_id=item.entry_plan_id,
                            print_disposition="reference_only",
                            page_count=1,
                        )
                    )
                    continue
                if not item.export_file_available:
                    raise PortfolioPresentationPdfError(
                        "portfolio_presentation_pdf.invalid_preparation",
                        "Visible Portfolio item has no printable or reference-only disposition.",
                        stage="inventory",
                    )
                payload = source_payloads_by_entry_plan[item.entry_plan_id]
                page_number, outcome = _render_byte_item(
                    pdf,
                    dependencies,
                    section,
                    item,
                    payload,
                    page_number=page_number,
                    string_width=stringWidth,
                )
                outcomes_by_entry_plan[item.entry_plan_id] = outcome

        for section in preparation.sections:
            for item in section.items:
                if item.disposition == "omitted_permitted":
                    outcomes_by_entry_plan[item.entry_plan_id] = (
                        StudentPortfolioPdfItemDisposition(
                            entry_plan_id=item.entry_plan_id,
                            print_disposition="omitted_permitted",
                            page_count=0,
                        )
                    )

        pdf.save()
        payload = output.getvalue()
        if not payload.startswith(b"%PDF-"):
            raise PortfolioPresentationPdfError(
                "portfolio_presentation_pdf.render_failed",
                "Printable Portfolio renderer did not produce a PDF payload.",
                stage="render",
            )
    except PortfolioPresentationPdfError:
        raise
    except Exception as error:
        raise PortfolioPresentationPdfError(
            "portfolio_presentation_pdf.render_failed",
            "Printable Portfolio could not be rendered deterministically.",
            stage="render",
        ) from error

    return StudentPortfolioPdfRenderResult(
        filename=filename,
        payload=payload,
        sha256=_sha256(payload),
        byte_size=len(payload),
        page_count=page_number - 1,
        renderer_id=STUDENT_PORTFOLIO_PDF_RENDERER_ID,
        renderer_version=STUDENT_PORTFOLIO_PDF_RENDERER_VERSION,
        renderer_contract_version=STUDENT_PORTFOLIO_PDF_CONTRACT_VERSION,
        renderer_configuration_sha256=configuration_sha256,
        item_dispositions=tuple(
            outcomes_by_entry_plan[item.entry_plan_id]
            for section in preparation.sections
            for item in section.items
        ),
    )


__all__ = [
    "PDF_PRINT_DISPOSITIONS",
    "PORTFOLIO_PRESENTATION_PDF_ERROR_CODES",
    "STUDENT_PORTFOLIO_PDF_CONTRACT_VERSION",
    "STUDENT_PORTFOLIO_PDF_FILENAME_DOMAIN",
    "STUDENT_PORTFOLIO_PDF_RENDERER_ID",
    "STUDENT_PORTFOLIO_PDF_RENDERER_VERSION",
    "PortfolioPresentationPdfError",
    "StudentPortfolioPdfItemDisposition",
    "StudentPortfolioPdfRenderResult",
    "render_student_portfolio_pdf",
]
