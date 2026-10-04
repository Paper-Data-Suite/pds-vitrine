from __future__ import annotations

from io import BytesIO

import pypdfium2 as pdfium
from PIL import Image
from reportlab.pdfgen.canvas import Canvas

from vitrine.models import ProfileRevisionRef, SnapshotEditionRef
from vitrine.portfolio_presentation import (
    StudentPortfolioPresentationItem,
    StudentPortfolioPresentationPreparation,
    StudentPortfolioPresentationSection,
)
from vitrine.portfolio_presentation_pdf import (
    STUDENT_PORTFOLIO_PDF_CONTRACT_VERSION,
    PortfolioPresentationPdfError,
    render_student_portfolio_pdf,
)


def _pdf_bytes() -> bytes:
    target = BytesIO()
    pdf = Canvas(target, invariant=1)
    pdf.setTitle("Exact source")
    pdf.drawString(72, 720, "Exact frozen source PDF page")
    pdf.showPage()
    pdf.save()
    return target.getvalue()


def _png_bytes() -> bytes:
    image = Image.new("RGB", (320, 180), "white")
    target = BytesIO()
    image.save(target, format="PNG")
    image.close()
    return target.getvalue()


def _item(
    *,
    entry_plan_id: str,
    ordinal: int,
    title: str,
    content_class: str,
    semantic_role: str,
    disposition: str = "included",
    filename: str | None = None,
    media_type: str | None = None,
    caption: str | None = None,
) -> StudentPortfolioPresentationItem:
    included = disposition == "included"
    return StudentPortfolioPresentationItem(
        entry_plan_id=entry_plan_id,
        plan_position=ordinal,
        section_id="section_1",
        ordinal=ordinal,
        semantic_role=semantic_role,
        content_class=content_class,
        materialization_kind="copied_source" if included else "reference_only",
        disposition=disposition,
        display_title=title,
        display_caption=caption,
        source_credit=None,
        presentation_note=(
            "No portable file is available for this exact Portfolio edition."
            if disposition == "reference_only"
            else None
        ),
        candidate_id=None,
        selection_id=None,
        placement_id=None,
        snapshot_entry_id=f"snapshot_{ordinal}" if included else None,
        materialization_id=f"materialization_{ordinal}" if included else None,
        omission_id=(
            f"omission_{ordinal}" if disposition == "omitted_permitted" else None
        ),
        technical_relative_path=f"technical/{ordinal}" if included else None,
        media_type=media_type,
        byte_size=1 if included else None,
        output_sha256="a" * 64 if included else None,
        export_file_available=included,
        presentation_filename=filename,
    )


def _preparation() -> StudentPortfolioPresentationPreparation:
    section = StudentPortfolioPresentationSection(
        section_id="section_1",
        label="Baseline Evidence",
        purpose="Where the work began and what it showed.",
        order=1,
        obligation="required",
        presentation_directory_name="01-baseline-evidence-0123456789abcdef",
        items=(
            _item(
                entry_plan_id="pdf_entry",
                ordinal=1,
                title="Argument Paragraph - First Draft",
                content_class="student_work",
                semantic_role="selected_work",
                filename="argument-first-draft-0123456789abcdef.pdf",
                media_type="application/pdf",
                caption="The baseline draft.",
            ),
            _item(
                entry_plan_id="image_entry",
                ordinal=2,
                title="Revised Visual",
                content_class="student_work",
                semantic_role="selected_work",
                filename="revised-visual-0123456789abcdef.png",
                media_type="image/png",
            ),
            _item(
                entry_plan_id="reflection_entry",
                ordinal=3,
                title="Comparison Reflection",
                content_class="reflection",
                semantic_role="reflection",
                filename="comparison-reflection-0123456789abcdef.txt",
                media_type="text/plain",
            ),
            _item(
                entry_plan_id="digital_entry",
                ordinal=4,
                title="Presentation Slides",
                content_class="student_work",
                semantic_role="selected_work",
                filename="presentation-slides-0123456789abcdef.pptx",
                media_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "presentationml.presentation"
                ),
            ),
            _item(
                entry_plan_id="reference_entry",
                ordinal=5,
                title="Assessment Snapshot",
                content_class="assessment_summary",
                semantic_role="assessment_summary",
                disposition="reference_only",
            ),
            _item(
                entry_plan_id="omitted_entry",
                ordinal=6,
                title="Audience-Prohibited Note",
                content_class="feedback",
                semantic_role="feedback",
                disposition="omitted_permitted",
            ),
        ),
    )
    return StudentPortfolioPresentationPreparation(
        contract_version="vitrine_student_portfolio_presentation_v1",
        observed_state_revision=10,
        snapshot_edition=SnapshotEditionRef(
            snapshot_series_id="series_secret", edition_number=4
        ),
        snapshot_export_artifact_id="export_secret",
        snapshot_manifest_sha256="1" * 64,
        snapshot_logical_inventory_sha256="2" * 64,
        portfolio_id="portfolio_secret",
        portfolio_subject_id="subject_secret",
        profile_binding_id="binding_secret",
        profile_revision=ProfileRevisionRef(
            portfolio_profile_id="profile_secret", profile_revision=2
        ),
        composition_revision=5,
        audience_context_id="audience_secret",
        presentation_class="student_portfolio",
        audience_presentation_class="student_portfolio",
        student_display_name="Jordan Lee",
        portfolio_title="Improvement Portfolio",
        profile_label="Improvement Portfolio",
        purpose="A record of revision, reflection, and growth.",
        technical_export_relative_path="technical/secret",
        technical_export_inventory_sha256="3" * 64,
        custody_namespace="presentations-bounded-v1",
        sections=(section,),
        file_item_count=4,
        reference_only_count=1,
        omitted_count=1,
        preparation_fingerprint="4" * 64,
    )


def _payloads() -> dict[str, bytes]:
    return {
        "pdf_entry": _pdf_bytes(),
        "image_entry": _png_bytes(),
        "reflection_entry": b"I changed my evidence and explained why.\nSecond line.",
        "digital_entry": b"PK synthetic exact presentation bytes",
    }


def _extract_text(payload: bytes) -> str:
    document = pdfium.PdfDocument(payload)
    parts: list[str] = []
    try:
        for index in range(len(document)):
            page = document[index]
            text_page = page.get_textpage()
            try:
                parts.append(text_page.get_text_range())
            finally:
                text_page.close()
                page.close()
    finally:
        document.close()
    return "\n".join(parts)


def test_pdf_is_binder_ready_and_preserves_explicit_print_dispositions() -> None:
    result = render_student_portfolio_pdf(
        _preparation(),
        presentation_artifact_id="presentation_1",
        source_payloads_by_entry_plan=_payloads(),
    )

    assert result.payload.startswith(b"%PDF-")
    assert result.filename.startswith("jordan-lee-improvement-portfolio-")
    assert result.filename.endswith(".pdf")
    assert result.renderer_contract_version == STUDENT_PORTFOLIO_PDF_CONTRACT_VERSION
    assert result.page_count >= 8
    assert [item.entry_plan_id for item in result.item_dispositions] == [
        "pdf_entry",
        "image_entry",
        "reflection_entry",
        "digital_entry",
        "reference_entry",
        "omitted_entry",
    ]
    assert [item.print_disposition for item in result.item_dispositions] == [
        "rendered_from_exact_source",
        "rendered_from_exact_source",
        "rendered_from_exact_source",
        "digital_attachment_only",
        "reference_only",
        "omitted_permitted",
    ]
    assert result.item_dispositions[-1].page_count == 0

    text = _extract_text(result.payload)
    assert "Improvement Portfolio" in text
    assert "Jordan Lee" in text
    assert "Baseline Evidence" in text
    assert "Comparison Reflection" in text
    assert "I changed my evidence and explained why." in text
    assert "Presentation Slides" in text
    assert "Digital attachment" in text
    assert "Assessment Snapshot" in text
    assert "Reference only" in text
    assert "Audience-Prohibited Note" not in text


def test_pdf_visible_surface_does_not_expose_technical_identity() -> None:
    result = render_student_portfolio_pdf(
        _preparation(),
        presentation_artifact_id="presentation_secret",
        source_payloads_by_entry_plan=_payloads(),
    )
    text = _extract_text(result.payload)

    for technical_value in (
        "presentation_secret",
        "portfolio_secret",
        "subject_secret",
        "binding_secret",
        "profile_secret",
        "audience_secret",
        "series_secret",
        "export_secret",
        "technical/secret",
        "pdf_entry",
    ):
        assert technical_value not in text


def test_pdf_bytes_are_deterministic_for_same_exact_inputs_and_environment() -> None:
    preparation = _preparation()
    payloads = _payloads()
    first = render_student_portfolio_pdf(
        preparation,
        presentation_artifact_id="presentation_deterministic",
        source_payloads_by_entry_plan=payloads,
    )
    second = render_student_portfolio_pdf(
        preparation,
        presentation_artifact_id="presentation_deterministic",
        source_payloads_by_entry_plan=payloads,
    )

    assert first.payload == second.payload
    assert first.sha256 == second.sha256
    assert first.renderer_configuration_sha256 == second.renderer_configuration_sha256


def test_pdf_requires_exact_bytes_for_every_byte_bearing_item() -> None:
    payloads = _payloads()
    payloads.pop("image_entry")

    try:
        render_student_portfolio_pdf(
            _preparation(),
            presentation_artifact_id="presentation_missing",
            source_payloads_by_entry_plan=payloads,
        )
    except PortfolioPresentationPdfError as error:
        assert error.code == "portfolio_presentation_pdf.source_missing"
        assert error.stage == "source"
    else:
        raise AssertionError("missing exact source bytes did not fail closed")
