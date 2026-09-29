"""Printable PDF renderer for immutable Vitrine paper Reflection issuance."""

from __future__ import annotations

import os
import secrets
from io import BytesIO
from pathlib import Path
from typing import Final

import qrcode
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from vitrine.models import CurationTargetRef
from vitrine.paper_reflection_printing import (
    PersistedReflectionPrintRoutes,
    ReflectionPrintPlan,
)

PAPER_REFLECTION_PDF_FILENAME: Final[str] = "student_reflection_response.pdf"


class PaperReflectionPdfError(RuntimeError):
    """Raised when an exact persisted paper Reflection plan cannot be rendered."""


def reflection_pdf_path(plan: ReflectionPrintPlan) -> Path:
    """Return the governed class/module/work PDF destination for one issuance."""

    if not plan.pages:
        raise PaperReflectionPdfError("Reflection print plan has no response pages.")
    first = plan.pages[0]
    if any(
        page.class_id != first.class_id or page.work_id != first.work_id
        for page in plan.pages
    ):
        raise PaperReflectionPdfError(
            "Reflection print plan pages do not share one class/work identity."
        )
    return (
        plan.workspace_root
        / "classes"
        / first.class_id
        / "modules"
        / "vitrine"
        / "work"
        / first.work_id
        / "templates"
        / PAPER_REFLECTION_PDF_FILENAME
    )


def render_persisted_reflection_pdf(
    persisted: PersistedReflectionPrintRoutes,
    *,
    student_display_name: str | None = None,
) -> Path:
    """Render exact immutable issuance/routes to a printable letter-size PDF."""

    plan = persisted.plan
    if len(plan.pages) != len(plan.routes):
        raise PaperReflectionPdfError(
            "Reflection pages and persisted route plans do not align."
        )
    if tuple(route.page for route in plan.routes) != plan.pages:
        raise PaperReflectionPdfError(
            "Reflection route ordering differs from issuance page ordering."
        )

    output = reflection_pdf_path(plan)
    _prepare_output_parent(plan.workspace_root, output.parent)
    if os.path.lexists(output) and (
        output.is_symlink() or not output.is_file()
    ):
        raise PaperReflectionPdfError(
            "Printable Reflection destination is not an ordinary file."
        )

    temporary = output.with_name(
        f".{output.stem}.{secrets.token_hex(8)}.tmp.pdf"
    )
    if os.path.lexists(temporary):
        raise PaperReflectionPdfError(
            "Printable Reflection temporary destination already exists."
        )
    try:
        _render_pdf(
            plan,
            temporary,
            student_display_name=student_display_name,
        )
        if temporary.is_symlink() or not temporary.is_file():
            raise PaperReflectionPdfError(
                "Printable Reflection renderer did not create an ordinary file."
            )
        os.replace(temporary, output)
    except Exception:
        try:
            if os.path.lexists(temporary):
                temporary.unlink()
        except OSError:
            pass
        raise
    return output


def _prepare_output_parent(root: Path, parent: Path) -> None:
    root_abs = Path(os.path.abspath(root))
    parent_abs = Path(os.path.abspath(parent))
    try:
        parent_abs.relative_to(root_abs)
    except ValueError as error:
        raise PaperReflectionPdfError(
            "Printable Reflection path escapes the workspace."
        ) from error

    current = root_abs
    if current.is_symlink():
        raise PaperReflectionPdfError("Workspace root must not be a symlink.")
    for part in parent_abs.relative_to(root_abs).parts:
        current = current / part
        if os.path.lexists(current):
            if current.is_symlink() or not current.is_dir():
                raise PaperReflectionPdfError(
                    "Printable Reflection path contains a non-directory or link."
                )
        else:
            current.mkdir()


def _render_pdf(
    plan: ReflectionPrintPlan,
    destination: Path,
    *,
    student_display_name: str | None,
) -> None:
    pdf = Canvas(str(destination), pagesize=letter, invariant=1)
    pdf.setTitle("Vitrine Student Reflection")
    issuance = plan.issuance

    for route in plan.routes:
        page = route.page
        page_width, page_height = letter
        margin = 0.55 * inch
        qr_size = 1.0 * inch
        qr_x = page_width - margin - qr_size
        qr_y = page_height - margin - qr_size
        text_width = qr_x - margin - 0.18 * inch

        pdf.setFont("Helvetica-Bold", 15)
        pdf.drawString(
            margin,
            page_height - margin - 14,
            "Student Reflection",
        )
        pdf.setFont("Helvetica", 9)
        label = student_display_name or issuance.student_reference.student_id
        identity_lines = (
            f"Student: {label}",
            (
                "Class: "
                f"{issuance.student_reference.class_id} "
                f"({issuance.student_reference.school_year})"
            ),
            f"Portfolio Reflection requirement: {issuance.reflection_requirement_id}",
        )
        y = page_height - margin - 34
        for value in identity_lines:
            pdf.drawString(
                margin,
                y,
                _fit_text(value, "Helvetica", 9, text_width),
            )
            y -= 12

        pdf.drawImage(
            _qr_image(route.payload_text),
            qr_x,
            qr_y,
            width=qr_size,
            height=qr_size,
            preserveAspectRatio=True,
            mask="auto",
        )

        header_bottom = page_height - margin - qr_size - 0.18 * inch
        pdf.setFont("Helvetica", 6)
        pdf.drawString(
            margin,
            header_bottom + 12,
            f"Page ID: {page.response_page_id}",
        )
        pdf.drawString(
            margin,
            header_bottom + 4,
            f"Route ID: {page.route_id}",
        )
        pdf.line(margin, header_bottom, page_width - margin, header_bottom)

        prompt_y = header_bottom - 0.25 * inch
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(margin, prompt_y, "Prompt")
        prompt_y -= 14
        pdf.setFont("Helvetica", 10)
        for line in _wrap_text(
            issuance.prompt_snapshot,
            font_name="Helvetica",
            font_size=10,
            max_width=page_width - 2 * margin,
        ):
            pdf.drawString(margin, prompt_y, line)
            prompt_y -= 13

        prompt_y -= 6
        pdf.setFont("Helvetica", 7)
        pdf.drawString(
            margin,
            prompt_y,
            f"Prompt: {issuance.prompt_id} / version {issuance.prompt_version}",
        )
        prompt_y -= 10
        for value in exact_curated_target_lines(issuance.target_references):
            for line in _wrap_exact_text(
                value,
                font_name="Helvetica",
                font_size=7,
                max_width=page_width - 2 * margin,
            ):
                pdf.drawString(margin, prompt_y, line)
                prompt_y -= 9

        writing_top = prompt_y - 0.18 * inch
        writing_bottom = margin + 0.35 * inch
        writing_left = margin + 0.18 * inch
        writing_right = page_width - margin
        pdf.setLineWidth(0.35)
        line_y = writing_top
        while line_y >= writing_bottom:
            pdf.line(writing_left, line_y, writing_right, line_y)
            line_y -= 0.31 * inch

        pdf.setFont("Helvetica", 8)
        pdf.drawString(margin, margin - 6, "Vitrine paper Reflection")
        pdf.drawRightString(
            page_width - margin,
            margin - 6,
            f"Page {page.logical_page_number} of {page.total_pages}",
        )
        pdf.showPage()

    pdf.save()


def exact_curated_target_lines(
    target_references: tuple[CurationTargetRef, ...],
) -> tuple[str, ...]:
    lines = [f"Exact curated targets ({len(target_references)}):"]
    if not target_references:
        lines.append("Target: none")
        return tuple(lines)

    lines.extend(
        f"Target {index}: {target.target_kind}:{target.target_id}"
        for index, target in enumerate(target_references, start=1)
    )
    return tuple(lines)


def _wrap_exact_text(
    text: str,
    *,
    font_name: str,
    font_size: int,
    max_width: float,
) -> tuple[str, ...]:
    if not text:
        return ("",)
    if stringWidth(text, font_name, font_size) <= max_width:
        return (text,)

    lines: list[str] = []
    remaining = text
    while remaining:
        split = len(remaining)
        while (
            split > 1
            and stringWidth(
                remaining[:split],
                font_name,
                font_size,
            )
            > max_width
        ):
            split -= 1
        if split == 1 and stringWidth(
            remaining[:1],
            font_name,
            font_size,
        ) > max_width:
            raise PaperReflectionPdfError(
                "Printable Reflection target identifier cannot fit on the page."
            )
        lines.append(remaining[:split])
        remaining = remaining[split:]
    return tuple(lines)


def _qr_image(payload: str) -> ImageReader:
    image = qrcode.make(payload)
    data = BytesIO()
    image.save(data, format="PNG")
    data.seek(0)
    return ImageReader(data)


def _fit_text(
    text: str,
    font_name: str,
    font_size: int,
    max_width: float,
) -> str:
    if stringWidth(text, font_name, font_size) <= max_width:
        return text
    suffix = "..."
    value = text
    while value and stringWidth(
        value + suffix,
        font_name,
        font_size,
    ) > max_width:
        value = value[:-1]
    return value + suffix


def _wrap_text(
    text: str,
    *,
    font_name: str,
    font_size: int,
    max_width: float,
) -> tuple[str, ...]:
    words = text.split()
    if not words:
        return ("",)
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if stringWidth(candidate, font_name, font_size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return tuple(lines)


__all__ = [
    "PAPER_REFLECTION_PDF_FILENAME",
    "PaperReflectionPdfError",
    "exact_curated_target_lines",
    "reflection_pdf_path",
    "render_persisted_reflection_pdf",
]
