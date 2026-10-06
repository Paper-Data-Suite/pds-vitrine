from __future__ import annotations

from dataclasses import replace

import pytest

from vitrine.models import ProfileRevisionRef, SnapshotEditionRef
from vitrine.portfolio_presentation import (
    StudentPortfolioPresentationItem,
    StudentPortfolioPresentationPreparation,
    StudentPortfolioPresentationSection,
)
from vitrine.portfolio_presentation_html import (
    STUDENT_PORTFOLIO_HTML_CONTRACT_VERSION,
    STUDENT_PORTFOLIO_HTML_FILENAME,
    PortfolioPresentationHtmlError,
    render_student_portfolio_html,
)


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
    note: str | None = None,
) -> StudentPortfolioPresentationItem:
    included = disposition == "included"
    return StudentPortfolioPresentationItem(
        entry_plan_id=entry_plan_id,
        plan_position=ordinal,
        section_id="section_1",
        ordinal=ordinal,
        semantic_role=semantic_role,
        content_class=content_class,
        materialization_kind="generated_vitrine" if included else "reference_only",
        disposition=disposition,
        display_title=title,
        display_caption=caption,
        source_credit="Teacher & student selection" if included else None,
        presentation_note=note,
        candidate_id=None,
        selection_id=None,
        placement_id=None,
        snapshot_entry_id=f"snapshot_{ordinal}" if included else None,
        materialization_id=f"materialization_{ordinal}" if included else None,
        omission_id=None,
        technical_relative_path=f"technical/{ordinal}" if included else None,
        media_type=media_type,
        byte_size=18 if included else None,
        output_sha256="a" * 64 if included else None,
        export_file_available=included,
        presentation_filename=filename,
    )


def _preparation() -> StudentPortfolioPresentationPreparation:
    first = StudentPortfolioPresentationSection(
        section_id="section_1",
        label="Baseline <Evidence>",
        purpose="Where the work began & what it showed.",
        order=1,
        obligation="required",
        presentation_directory_name="01-baseline-evidence-0123456789abcdef",
        items=(
            _item(
                entry_plan_id="reflection_entry",
                ordinal=1,
                title='My Reflection <script>alert("x")</script>',
                content_class="reflection",
                semantic_role="reflection",
                filename="my-reflection-0123456789abcdef.txt",
                media_type="text/plain",
                caption="What changed & why it matters.",
            ),
            _item(
                entry_plan_id="reference_entry",
                ordinal=2,
                title="Assessment Snapshot",
                content_class="assessment_summary",
                semantic_role="assessment_summary",
                disposition="reference_only",
                note="No portable file is available for this exact Portfolio edition.",
            ),
        ),
    )
    optional_empty = StudentPortfolioPresentationSection(
        section_id="optional_empty",
        label="Optional Extras",
        purpose="Additional work if present.",
        order=2,
        obligation="optional",
        presentation_directory_name="02-optional-extras-0123456789abcdef",
        items=(),
    )
    required_empty = StudentPortfolioPresentationSection(
        section_id="required_empty",
        label="Closing Reflection",
        purpose="A required closing section.",
        order=3,
        obligation="required",
        presentation_directory_name="03-closing-reflection-0123456789abcdef",
        items=(),
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
        student_display_name='Jordan & Lee <script>alert("student")</script>',
        portfolio_title="Growth & Voice <Portfolio>",
        profile_label="Improvement Portfolio",
        purpose="A record of revision, reflection, and growth.",
        technical_export_relative_path="technical/secret",
        technical_export_inventory_sha256="3" * 64,
        custody_namespace="presentations-bounded-v1",
        sections=(first, optional_empty, required_empty),
        file_item_count=1,
        reference_only_count=1,
        omitted_count=0,
        preparation_fingerprint="4" * 64,
    )


def test_html_is_polished_offline_and_escapes_all_student_visible_text() -> None:
    preparation = _preparation()
    reflection = b'I learned <more> & "better".\nSecond line.'

    result = render_student_portfolio_html(
        preparation,
        text_payloads_by_entry_plan={"reflection_entry": reflection},
    )
    text = result.payload.decode("utf-8")

    assert result.filename == STUDENT_PORTFOLIO_HTML_FILENAME
    assert result.renderer_contract_version == STUDENT_PORTFOLIO_HTML_CONTRACT_VERSION
    assert text.startswith("<!doctype html>")
    assert "<style>" in text
    assert "<script" not in text.casefold()
    assert "http://" not in text.casefold()
    assert "https://" not in text.casefold()
    assert "Growth &amp; Voice &lt;Portfolio&gt;" in text
    assert "Jordan &amp; Lee &lt;script&gt;" in text
    assert "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;" in text
    assert 'I learned &lt;more&gt; &amp; &quot;better&quot;.' in text
    assert "No portable file is available" in text
    assert "Optional Extras" not in text
    assert "Closing Reflection" in text
    assert "No Portfolio items are present in this required section." in text


def test_html_uses_only_bounded_package_relative_links_and_no_technical_ids() -> None:
    preparation = _preparation()
    result = render_student_portfolio_html(
        preparation,
        text_payloads_by_entry_plan={"reflection_entry": b"Exact reflection text."},
    )
    text = result.payload.decode("utf-8")

    expected_href = (
        "01-baseline-evidence-0123456789abcdef/"
        "my-reflection-0123456789abcdef.txt"
    )
    assert f'href="{expected_href}"' in text
    for technical_value in (
        "portfolio_secret",
        "subject_secret",
        "binding_secret",
        "profile_secret",
        "audience_secret",
        "series_secret",
        "export_secret",
        "technical/secret",
        "reflection_entry",
    ):
        assert technical_value not in text


def test_html_bytes_are_deterministic_for_same_frozen_inputs() -> None:
    preparation = _preparation()
    payloads = {"reflection_entry": b"Exact reflection text.\n"}

    first = render_student_portfolio_html(
        preparation,
        text_payloads_by_entry_plan=payloads,
    )
    second = render_student_portfolio_html(
        preparation,
        text_payloads_by_entry_plan=payloads,
    )

    assert first.payload == second.payload
    assert first.sha256 == second.sha256
    assert first.renderer_configuration_sha256 == (
        second.renderer_configuration_sha256
    )


def test_inline_reflection_requires_exact_frozen_bytes() -> None:
    with pytest.raises(PortfolioPresentationHtmlError) as caught:
        render_student_portfolio_html(_preparation())

    assert caught.value.code == (
        "portfolio_presentation_html.reflection_bytes_missing"
    )
    assert caught.value.stage == "reflection"


def test_html_rejects_unbounded_student_file_path() -> None:
    preparation = _preparation()
    first_section = preparation.sections[0]
    reflection = first_section.items[0]
    unsafe_reflection = replace(reflection, presentation_filename="../escape.txt")
    unsafe_section = replace(
        first_section,
        items=(unsafe_reflection, *first_section.items[1:]),
    )
    unsafe_preparation = replace(
        preparation,
        sections=(unsafe_section, *preparation.sections[1:]),
    )

    with pytest.raises(PortfolioPresentationHtmlError) as caught:
        render_student_portfolio_html(
            unsafe_preparation,
            text_payloads_by_entry_plan={"reflection_entry": b"Exact text."},
        )

    assert caught.value.code == "portfolio_presentation_html.unsafe_path"


def test_html_uses_local_image_preview_for_supported_raster_work() -> None:
    preparation = _preparation()
    first_section = preparation.sections[0]
    image_item = replace(
        first_section.items[0],
        entry_plan_id="image_entry",
        display_title="Revised Visual",
        content_class="student_work",
        semantic_role="selected_work",
        presentation_filename="revised-visual-0123456789abcdef.png",
        media_type="image/png",
    )
    image_section = replace(first_section, items=(image_item,))
    image_preparation = replace(
        preparation,
        sections=(image_section,),
        file_item_count=1,
        reference_only_count=0,
    )

    result = render_student_portfolio_html(image_preparation)
    text = result.payload.decode("utf-8")
    expected_href = (
        "01-baseline-evidence-0123456789abcdef/"
        "revised-visual-0123456789abcdef.png"
    )

    assert f'src="{expected_href}"' in text
    assert f'href="{expected_href}"' in text
    assert 'alt="Revised Visual"' in text

def test_html_does_not_reintroduce_permitted_omissions() -> None:
    preparation = _preparation()
    first_section = preparation.sections[0]
    reference_item = first_section.items[1]
    omitted_item = replace(
        reference_item,
        entry_plan_id="omitted_entry",
        ordinal=3,
        display_title="Audience-Prohibited Note",
        disposition="omitted_permitted",
        presentation_note="This omitted content must not appear to the student.",
        omission_id="omission_1",
    )
    prepared = replace(
        preparation,
        sections=(
            replace(
                first_section,
                items=(*first_section.items, omitted_item),
            ),
            *preparation.sections[1:],
        ),
        omitted_count=1,
    )

    result = render_student_portfolio_html(
        prepared,
        text_payloads_by_entry_plan={"reflection_entry": b"Exact reflection text."},
    )
    text = result.payload.decode("utf-8")

    assert "Assessment Snapshot" in text
    assert "Audience-Prohibited Note" not in text
    assert "This omitted content must not appear" not in text
