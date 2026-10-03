from __future__ import annotations

import re

import pytest

from vitrine.path_policy import (
    PRESENTATION_DIRECTORY_MAX_LENGTH,
    PRESENTATION_FILENAME_MAX_LENGTH,
    VitrinePathPolicyError,
    build_bounded_presentation_directory_name,
    build_bounded_presentation_filename,
    require_unique_presentation_components,
)


def test_filename_contract_is_deterministic_bounded_and_privacy_minimized() -> None:
    semantic = {
        "snapshot_entry_id": "snapshot_entry_" + ("e" * 10_000),
        "student_id": "student_private_identifier_" + ("s" * 10_000),
        "source_locator": "private/source/" + ("nested-" * 2_000),
    }
    first = build_bounded_presentation_filename(
        "My Revised Argument " * 1_000,
        semantic_domain="student-portfolio-entry",
        semantic_identity=semantic,
        extension=".pdf",
    )
    second = build_bounded_presentation_filename(
        "My Revised Argument " * 1_000,
        semantic_domain="student-portfolio-entry",
        semantic_identity=semantic,
        extension=".pdf",
    )

    assert first == second
    assert len(first.encode("utf-8")) <= PRESENTATION_FILENAME_MAX_LENGTH
    assert first.endswith(".pdf")
    assert "student_private_identifier" not in first
    assert "private" not in first
    assert re.fullmatch(r"[a-z0-9][a-z0-9._-]*", first)


def test_truncated_equal_labels_are_semantically_disambiguated() -> None:
    label = "A Very Long Student Work Title " * 1_000
    first = build_bounded_presentation_filename(
        label,
        semantic_domain="student-portfolio-entry",
        semantic_identity={"snapshot_entry_id": "entry_a"},
        extension=".docx",
    )
    second = build_bounded_presentation_filename(
        label,
        semantic_domain="student-portfolio-entry",
        semantic_identity={"snapshot_entry_id": "entry_b"},
        extension=".docx",
    )

    assert first != second
    assert first.endswith(".docx")
    assert second.endswith(".docx")
    assert len(first.encode("utf-8")) <= PRESENTATION_FILENAME_MAX_LENGTH
    assert len(second.encode("utf-8")) <= PRESENTATION_FILENAME_MAX_LENGTH


@pytest.mark.parametrize(
    "extension",
    (".pdf", ".docx", ".pptx", ".xlsx", ".png", ".jpg", ".tiff", ".md", ".txt", ".json"),
)
def test_supported_shape_extensions_are_preserved_exactly(extension: str) -> None:
    filename = build_bounded_presentation_filename(
        "Portfolio Work",
        semantic_domain="student-portfolio-entry",
        semantic_identity={"entry": extension},
        extension=extension,
    )
    assert filename.endswith(extension)


def test_section_directory_is_readable_ordered_bounded_and_disambiguated() -> None:
    first = build_bounded_presentation_directory_name(
        "Writing Growth Across the Year " * 1_000,
        semantic_domain="student-portfolio-section",
        semantic_identity={"section_id": "growth_a"},
        ordinal=3,
    )
    second = build_bounded_presentation_directory_name(
        "Writing Growth Across the Year " * 1_000,
        semantic_domain="student-portfolio-section",
        semantic_identity={"section_id": "growth_b"},
        ordinal=3,
    )

    assert first.startswith("03-writing-growth-across-the-year-")
    assert second.startswith("03-writing-growth-across-the-year-")
    assert first != second
    assert len(first.encode("utf-8")) <= PRESENTATION_DIRECTORY_MAX_LENGTH
    assert len(second.encode("utf-8")) <= PRESENTATION_DIRECTORY_MAX_LENGTH
    assert "/" not in first
    assert "\\" not in first


def test_section_directory_without_ordinal_remains_bounded() -> None:
    directory = build_bounded_presentation_directory_name(
        "Reflection",
        semantic_domain="student-portfolio-section",
        semantic_identity={"section_id": "reflection"},
    )

    assert directory.startswith("reflection-")
    assert len(directory.encode("utf-8")) <= PRESENTATION_DIRECTORY_MAX_LENGTH


def test_unicode_equivalent_section_labels_have_same_name() -> None:
    first = build_bounded_presentation_directory_name(
        "Résumé",
        semantic_domain="student-portfolio-section",
        semantic_identity={"section_id": "resume"},
        ordinal=2,
    )
    second = build_bounded_presentation_directory_name(
        "Re\u0301sume\u0301",
        semantic_domain="student-portfolio-section",
        semantic_identity={"section_id": "resume"},
        ordinal=2,
    )

    assert first == second
    assert first.startswith("02-resume-")


@pytest.mark.parametrize("ordinal", (True, 0, -1, 10_000))
def test_section_directory_rejects_unbounded_or_invalid_ordinal(
    ordinal: object,
) -> None:
    with pytest.raises(VitrinePathPolicyError):
        build_bounded_presentation_directory_name(
            "Section",
            semantic_domain="student-portfolio-section",
            semantic_identity={"section_id": "section"},
            ordinal=ordinal,  # type: ignore[arg-type]
        )


def test_presentation_inventory_fails_closed_on_portable_collision() -> None:
    with pytest.raises(VitrinePathPolicyError, match="collision"):
        require_unique_presentation_components(
            ("revised-argument-a1.pdf", "REVISED-ARGUMENT-A1.PDF")
        )


def test_presentation_inventory_accepts_distinct_generated_components() -> None:
    first = build_bounded_presentation_filename(
        "Revised Argument",
        semantic_domain="student-portfolio-entry",
        semantic_identity={"entry": "a"},
        extension=".pdf",
    )
    second = build_bounded_presentation_filename(
        "Revised Argument",
        semantic_domain="student-portfolio-entry",
        semantic_identity={"entry": "b"},
        extension=".pdf",
    )

    assert require_unique_presentation_components((first, second)) == (first, second)
