from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from vitrine.completed_portfolio import (
    COMPLETED_PORTFOLIO_HISTORY_CONTRACT_VERSION,
    CompletedPortfolioHistoryError,
    project_completed_portfolio_history,
)
from vitrine.models import (
    ActorAttribution,
    AudienceContext,
    DigestReference,
    Portfolio,
    PortfolioPresentationArtifact,
    ProfileRevisionRef,
    SnapshotCurrentPointerRevision,
    SnapshotEdition,
    SnapshotEditionRef,
    SnapshotExportArtifact,
    SnapshotManifest,
    SnapshotSeal,
    SnapshotSeries,
)

NOW = datetime(2026, 10, 6, 20, 0, tzinfo=timezone.utc)
ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="teacher_1",
    owning_system="vitrine",
    role_snapshot="teacher",
)
PROFILE = ProfileRevisionRef(
    portfolio_profile_id="profile_improvement",
    profile_revision=3,
)


def _digest(value: str) -> DigestReference:
    return DigestReference(value=value * 64)


def _audience(
    *,
    audience_context_id: str,
    portfolio_id: str = "portfolio_1",
    subject_id: str = "subject_1",
    purpose: str,
    presentation_class: str = "student_portfolio",
    created_at: datetime = NOW,
) -> AudienceContext:
    return AudienceContext(
        audience_context_id=audience_context_id,
        portfolio_id=portfolio_id,
        portfolio_subject_id=subject_id,
        profile_binding_id="binding_1",
        profile_revision=PROFILE,
        audience_rule_id=f"rule_{audience_context_id}",
        audience_class="student",
        purpose=purpose,
        subject_scope="single_subject",
        allowed_content_classes=("student_work",),
        prohibited_content_classes=("private_teacher_note",),
        required_review_classes=(),
        presentation_class=presentation_class,
        retention_policy_reference=None,
        created_at=created_at,
        created_by=ACTOR,
    )


def _edition_records(
    *,
    series_id: str,
    edition_number: int,
    audience_context_id: str,
    created_at: datetime,
    predecessor_edition: int | None = None,
) -> tuple[SnapshotManifest, SnapshotSeal, SnapshotEdition]:
    reference = SnapshotEditionRef(
        snapshot_series_id=series_id,
        edition_number=edition_number,
    )
    manifest = SnapshotManifest(
        manifest_id=f"manifest_{series_id}_{edition_number}",
        manifest_contract_version="snapshot_manifest_v1",
        snapshot_edition=reference,
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        profile_binding_id="binding_1",
        profile_revision=PROFILE,
        composition_revision=edition_number,
        audience_context_id=audience_context_id,
        entry_ids=(f"entry_{series_id}_{edition_number}",),
        omission_ids=(),
        created_at=created_at,
        created_by=ACTOR,
    )
    seal = SnapshotSeal(
        seal_id=f"seal_{series_id}_{edition_number}",
        snapshot_edition=reference,
        manifest_id=manifest.manifest_id,
        manifest_digest=_digest("a"),
        logical_inventory_digest=_digest("b"),
        sealed_at=created_at,
        sealed_by=ACTOR,
    )
    edition = SnapshotEdition(
        snapshot_series_id=series_id,
        edition_number=edition_number,
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        profile_binding_id="binding_1",
        profile_revision=PROFILE,
        composition_revision=edition_number,
        audience_context_id=audience_context_id,
        manifest_id=manifest.manifest_id,
        seal_id=seal.seal_id,
        created_at=created_at,
        created_by=ACTOR,
        predecessor_edition=predecessor_edition,
    )
    return manifest, seal, edition


def _export(
    *,
    artifact_id: str,
    series_id: str,
    edition_number: int,
    generated_at: datetime,
    predecessor: str | None = None,
) -> SnapshotExportArtifact:
    return SnapshotExportArtifact(
        snapshot_export_artifact_id=artifact_id,
        snapshot_edition=SnapshotEditionRef(
            snapshot_series_id=series_id,
            edition_number=edition_number,
        ),
        export_format="directory_package",
        export_contract_version="snapshot_directory_v1",
        included_entry_ids=(f"entry_{series_id}_{edition_number}",),
        excluded_entry_ids=(),
        packager_id="snapshot_packager",
        packager_version="1",
        configuration_digest=_digest("c"),
        generated_at=generated_at,
        relative_path=f"exports/{artifact_id}",
        directory_inventory_digest=_digest("d"),
        validation_result="verified",
        predecessor_export_artifact_id=predecessor,
    )


def _presentation(
    *,
    artifact_id: str,
    export_id: str,
    series_id: str,
    edition_number: int,
    audience_context_id: str,
    generated_at: datetime,
    predecessor: str | None = None,
) -> PortfolioPresentationArtifact:
    root = f"presentations/{artifact_id}"
    return PortfolioPresentationArtifact(
        presentation_artifact_id=artifact_id,
        snapshot_edition=SnapshotEditionRef(
            snapshot_series_id=series_id,
            edition_number=edition_number,
        ),
        snapshot_export_artifact_id=export_id,
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        profile_binding_id="binding_1",
        profile_revision=PROFILE,
        audience_context_id=audience_context_id,
        presentation_class="student_portfolio",
        presentation_contract_version="vitrine_student_portfolio_presentation_v1",
        renderer_id="student_portfolio_renderer",
        renderer_version="1",
        renderer_contract_version="student_portfolio_renderer_v1",
        renderer_configuration_digest=_digest("e"),
        relative_path=root,
        presentation_manifest_relative_path=f"{root}/presentation-manifest.json",
        presentation_manifest_digest=_digest("f"),
        html_relative_path=f"{root}/portfolio.html",
        html_digest=_digest("1"),
        printable_pdf_relative_path=f"{root}/portfolio.pdf",
        printable_pdf_digest=_digest("2"),
        package_inventory_digest=_digest("3"),
        generated_at=generated_at,
        generated_by=ACTOR,
        predecessor_presentation_artifact_id=predecessor,
    )


def _records() -> tuple[object, ...]:
    portfolio = Portfolio(
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        created_at=NOW - timedelta(days=30),
        created_by=ACTOR,
        title_snapshot="Improvement Portfolio",
    )
    student = _audience(
        audience_context_id="audience_student",
        purpose="Student Review",
        created_at=NOW - timedelta(days=20),
    )
    family = _audience(
        audience_context_id="audience_family",
        purpose="Family Review",
        created_at=NOW - timedelta(days=10),
    )
    student_series = SnapshotSeries(
        snapshot_series_id="series_student",
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=portfolio.portfolio_subject_id,
        snapshot_purpose="improvement",
        audience_context_id=student.audience_context_id,
        created_at=NOW - timedelta(days=20),
        created_by=ACTOR,
    )
    family_series = SnapshotSeries(
        snapshot_series_id="series_family",
        portfolio_id=portfolio.portfolio_id,
        portfolio_subject_id=portfolio.portfolio_subject_id,
        snapshot_purpose="family_review",
        audience_context_id=family.audience_context_id,
        created_at=NOW - timedelta(days=10),
        created_by=ACTOR,
        predecessor_series_id=student_series.snapshot_series_id,
    )

    student_1 = _edition_records(
        series_id=student_series.snapshot_series_id,
        edition_number=1,
        audience_context_id=student.audience_context_id,
        created_at=NOW - timedelta(days=8),
    )
    student_2 = _edition_records(
        series_id=student_series.snapshot_series_id,
        edition_number=2,
        audience_context_id=student.audience_context_id,
        created_at=NOW - timedelta(days=2),
        predecessor_edition=1,
    )
    family_1 = _edition_records(
        series_id=family_series.snapshot_series_id,
        edition_number=1,
        audience_context_id=family.audience_context_id,
        created_at=NOW - timedelta(days=1),
    )

    export_old = _export(
        artifact_id="export_student_old",
        series_id=student_series.snapshot_series_id,
        edition_number=1,
        generated_at=NOW - timedelta(days=8),
    )
    export_new = _export(
        artifact_id="export_student_new",
        series_id=student_series.snapshot_series_id,
        edition_number=1,
        generated_at=NOW - timedelta(days=7),
        predecessor=export_old.snapshot_export_artifact_id,
    )
    presentation_old = _presentation(
        artifact_id="presentation_student_old",
        export_id=export_old.snapshot_export_artifact_id,
        series_id=student_series.snapshot_series_id,
        edition_number=1,
        audience_context_id=student.audience_context_id,
        generated_at=NOW - timedelta(days=6),
    )
    presentation_new = _presentation(
        artifact_id="presentation_student_new",
        export_id=export_new.snapshot_export_artifact_id,
        series_id=student_series.snapshot_series_id,
        edition_number=1,
        audience_context_id=student.audience_context_id,
        generated_at=NOW - timedelta(days=5),
        predecessor=presentation_old.presentation_artifact_id,
    )
    current = SnapshotCurrentPointerRevision(
        snapshot_current_pointer_id="pointer_student",
        pointer_revision=1,
        snapshot_series_id=student_series.snapshot_series_id,
        edition_number=1,
        pointed_at=NOW - timedelta(days=4),
        pointed_by=ACTOR,
        authority_reference="teacher_confirmation",
        reason="Keep reviewed Edition 1 current.",
    )

    return (
        portfolio,
        student,
        family,
        student_series,
        family_series,
        *student_1,
        *student_2,
        *family_1,
        export_old,
        export_new,
        presentation_old,
        presentation_new,
        current,
    )


def test_completed_history_projects_multiple_series_without_global_edition_sequence() -> None:
    history = project_completed_portfolio_history(_records(), portfolio_id="portfolio_1")

    assert history.contract_version == COMPLETED_PORTFOLIO_HISTORY_CONTRACT_VERSION
    assert history.completed_edition_count == 3
    assert [item.snapshot_series_id for item in history.series] == [
        "series_family",
        "series_student",
    ]
    assert [item.edition_number for item in history.series[0].editions] == [1]
    assert [item.edition_number for item in history.series[1].editions] == [2, 1]
    assert history.series[0].audience_purpose == "Family Review"
    assert history.series[1].audience_purpose == "Student Review"


def test_current_status_comes_only_from_exact_pointer_not_newest_edition() -> None:
    history = project_completed_portfolio_history(_records(), portfolio_id="portfolio_1")
    student = next(item for item in history.series if item.snapshot_series_id == "series_student")

    assert student.current_edition_number == 1
    assert [(item.edition_number, item.is_current) for item in student.editions] == [
        (2, False),
        (1, True),
    ]
    family = next(item for item in history.series if item.snapshot_series_id == "series_family")
    assert family.current_edition_number is None
    assert family.editions[0].is_current is False


def test_export_and_presentation_history_is_exact_and_deterministically_newest_first() -> None:
    history = project_completed_portfolio_history(_records(), portfolio_id="portfolio_1")
    student = next(item for item in history.series if item.snapshot_series_id == "series_student")
    edition = next(item for item in student.editions if item.edition_number == 1)

    assert [item.snapshot_export_artifact_id for item in edition.exports] == [
        "export_student_new",
        "export_student_old",
    ]
    assert [item.presentation_artifact_id for item in edition.presentations] == [
        "presentation_student_new",
        "presentation_student_old",
    ]
    assert edition.presentations[0].snapshot_export_artifact_id == "export_student_new"
    assert edition.presentations[0].predecessor_presentation_artifact_id == (
        "presentation_student_old"
    )


def test_series_with_no_completed_editions_remains_discoverable_without_inference() -> None:
    records = list(_records())
    records.extend(
        (
            _audience(
                audience_context_id="audience_showcase",
                purpose="Showcase",
                presentation_class="showcase",
                created_at=NOW,
            ),
            SnapshotSeries(
                snapshot_series_id="series_showcase",
                portfolio_id="portfolio_1",
                portfolio_subject_id="subject_1",
                snapshot_purpose="showcase",
                audience_context_id="audience_showcase",
                created_at=NOW,
                created_by=ACTOR,
            ),
        )
    )

    history = project_completed_portfolio_history(records, portfolio_id="portfolio_1")

    assert history.series[0].snapshot_series_id == "series_showcase"
    assert history.series[0].presentation_class == "showcase"
    assert history.series[0].editions == ()


def test_projection_rejects_presentation_whose_context_disagrees_with_edition() -> None:
    records = list(_records())
    presentation = next(
        item
        for item in records
        if isinstance(item, PortfolioPresentationArtifact)
        and item.presentation_artifact_id == "presentation_student_new"
    )
    records[records.index(presentation)] = replace(
        presentation,
        portfolio_subject_id="different_subject",
    )

    with pytest.raises(CompletedPortfolioHistoryError) as caught:
        project_completed_portfolio_history(records, portfolio_id="portfolio_1")

    assert caught.value.code == "completed_portfolio.canonical_history_inconsistent"


def test_projection_rejects_competing_current_pointer_identities() -> None:
    records = list(_records())
    records.append(
        SnapshotCurrentPointerRevision(
            snapshot_current_pointer_id="pointer_competing",
            pointer_revision=1,
            snapshot_series_id="series_student",
            edition_number=2,
            pointed_at=NOW,
            pointed_by=ACTOR,
            authority_reference="synthetic_conflict",
            reason="Synthetic competing pointer.",
        )
    )

    with pytest.raises(CompletedPortfolioHistoryError) as caught:
        project_completed_portfolio_history(records, portfolio_id="portfolio_1")

    assert caught.value.code == "completed_portfolio.current_pointer_inconsistent"


def test_projection_is_record_only_and_does_not_require_custody_bytes() -> None:
    history = project_completed_portfolio_history(_records(), portfolio_id="portfolio_1")
    student = next(item for item in history.series if item.snapshot_series_id == "series_student")
    edition = next(item for item in student.editions if item.edition_number == 1)

    assert edition.exports[0].relative_path == "exports/export_student_new"
    assert edition.presentations[0].html_relative_path.endswith("/portfolio.html")
    assert edition.presentations[0].printable_pdf_relative_path.endswith("/portfolio.pdf")
