from __future__ import annotations

import pytest

from vitrine.path_policy import (
    CUSTODY_TOKEN_MAX_LENGTH,
    CUSTODY_TOKEN_PREFIX,
    PRESENTATION_FILENAME_MAX_LENGTH,
    VITRINE_PATH_POLICY_VERSION,
    VitrinePathPolicyError,
    build_bounded_custody_token,
    build_bounded_presentation_filename,
    require_generated_component,
)


def test_path_policy_contract_is_explicit_v1() -> None:
    assert VITRINE_PATH_POLICY_VERSION == "vitrine_path_policy_v1"


def test_custody_token_is_fixed_bounded_and_identity_independent_in_size() -> None:
    short = build_bounded_custody_token(
        domain="record-storage",
        semantic_identity={"record_type": "portfolio", "identity": ["portfolio_1"]},
    )
    long = build_bounded_custody_token(
        domain="record-storage",
        semantic_identity={
            "record_type": "portfolio_profile_requirement",
            "identity": ["profile_" + ("x" * 10_000), 1, "requirement_" + ("y" * 10_000)],
        },
    )

    assert short.startswith(CUSTODY_TOKEN_PREFIX)
    assert long.startswith(CUSTODY_TOKEN_PREFIX)
    assert len(short) == CUSTODY_TOKEN_MAX_LENGTH
    assert len(long) == CUSTODY_TOKEN_MAX_LENGTH


def test_custody_token_is_domain_separated_and_structurally_unambiguous() -> None:
    first = build_bounded_custody_token(
        domain="record-storage",
        semantic_identity=["a", "bc"],
    )
    second = build_bounded_custody_token(
        domain="record-storage",
        semantic_identity=["ab", "c"],
    )
    other_domain = build_bounded_custody_token(
        domain="snapshot-custody",
        semantic_identity=["a", "bc"],
    )

    assert first != second
    assert first != other_domain


def test_presentation_filename_is_readable_bounded_and_exactly_suffixed() -> None:
    filename = build_bounded_presentation_filename(
        "Jordan Rivera — Revised Argument Paragraph!!!",
        semantic_domain="student-portfolio-entry",
        semantic_identity={"entry_id": "entry_1"},
        extension=".pdf",
    )

    assert filename.startswith("jordan-rivera-revised-argument-paragraph-")
    assert filename.endswith(".pdf")
    assert len(filename.encode("utf-8")) <= PRESENTATION_FILENAME_MAX_LENGTH


def test_presentation_filename_does_not_scale_with_display_text() -> None:
    filename = build_bounded_presentation_filename(
        "Extremely Long Student Work Title " * 500,
        semantic_domain="student-portfolio-entry",
        semantic_identity={"entry_id": "entry_long"},
        extension=".docx",
    )

    assert len(filename.encode("utf-8")) <= PRESENTATION_FILENAME_MAX_LENGTH
    assert filename.endswith(".docx")


def test_distinct_semantic_identities_disambiguate_same_readable_label() -> None:
    first = build_bounded_presentation_filename(
        "Revised Argument",
        semantic_domain="student-portfolio-entry",
        semantic_identity={"entry_id": "entry_a"},
        extension=".pdf",
    )
    second = build_bounded_presentation_filename(
        "Revised Argument",
        semantic_domain="student-portfolio-entry",
        semantic_identity={"entry_id": "entry_b"},
        extension=".pdf",
    )

    assert first != second
    assert first.rsplit("-", 1)[0] == second.rsplit("-", 1)[0]


def test_canonically_equivalent_labels_produce_same_filename() -> None:
    first = build_bounded_presentation_filename(
        "Résumé",
        semantic_domain="student-portfolio-entry",
        semantic_identity={"entry_id": "entry_resume"},
        extension=".pdf",
    )
    second = build_bounded_presentation_filename(
        "Re\u0301sume\u0301",
        semantic_domain="student-portfolio-entry",
        semantic_identity={"entry_id": "entry_resume"},
        extension=".pdf",
    )

    assert first == second
    assert first.startswith("resume-")


def test_non_ascii_label_uses_explicit_portable_fallback() -> None:
    filename = build_bounded_presentation_filename(
        "東京",
        semantic_domain="student-portfolio-entry",
        semantic_identity={"entry_id": "entry_tokyo"},
        extension=".pdf",
    )

    assert filename.startswith("item-")
    assert filename.endswith(".pdf")


@pytest.mark.parametrize(
    "extension",
    ("pdf", ".PDF", ".tar.gz", "../pdf", ".pdf/", ".", ""),
)
def test_presentation_filename_rejects_unsupported_extension_forms(
    extension: str,
) -> None:
    with pytest.raises(VitrinePathPolicyError):
        build_bounded_presentation_filename(
            "Student Work",
            semantic_domain="student-portfolio-entry",
            semantic_identity={"entry_id": "entry_1"},
            extension=extension,
        )


@pytest.mark.parametrize(
    "domain",
    ("", " Record-storage", "Record-storage", "record storage", "x" * 65),
)
def test_policy_rejects_invalid_domains(domain: str) -> None:
    with pytest.raises(VitrinePathPolicyError):
        build_bounded_custody_token(
            domain=domain,
            semantic_identity={"id": "x"},
        )


def test_policy_rejects_noncanonical_semantic_identity() -> None:
    with pytest.raises(VitrinePathPolicyError):
        build_bounded_custody_token(
            domain="record-storage",
            semantic_identity=object(),
        )


def test_generated_component_validation_is_budgeted_and_portable() -> None:
    assert require_generated_component(
        "portfolio-index.html",
        maximum=32,
    ) == "portfolio-index.html"

    with pytest.raises(VitrinePathPolicyError):
        require_generated_component("x" * 33, maximum=32)
    with pytest.raises(VitrinePathPolicyError):
        require_generated_component("folder/file.pdf", maximum=64)
    with pytest.raises(VitrinePathPolicyError):
        require_generated_component("con.txt", maximum=64)
