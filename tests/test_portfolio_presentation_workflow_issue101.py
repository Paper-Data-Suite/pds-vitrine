from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from vitrine.models import (
    ActorAttribution,
    DigestReference,
    PortfolioPresentationArtifact,
    ProfileRevisionRef,
    SnapshotEditionRef,
)
from vitrine.portfolio_presentation import StudentPortfolioPresentationPreparation
from vitrine.portfolio_presentation_contract import (
    STUDENT_PORTFOLIO_PRESENTATION_RENDERER_CONTRACT_VERSION,
    STUDENT_PORTFOLIO_PRESENTATION_RENDERER_ID,
    STUDENT_PORTFOLIO_PRESENTATION_RENDERER_VERSION,
    student_portfolio_presentation_artifact_id,
    student_portfolio_renderer_configuration_sha256,
)
from vitrine.portfolio_presentation_services import (
    PortfolioPresentationBuildError,
    build_student_portfolio_presentation,
)
from vitrine.portfolio_presentation_verification import (
    StudentPortfolioPackageVerification,
)
from vitrine.storage import (
    VitrineStorageConflictError,
    VitrineStoragePartialSuccessError,
)

NOW = datetime(2026, 10, 4, 18, 0, tzinfo=timezone.utc)
ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="teacher_1",
    owning_system="vitrine",
    role_snapshot="teacher",
)
PDF_CONFIGURATION = "d" * 64
RENDERER_CONFIGURATION = student_portfolio_renderer_configuration_sha256(
    pdf_renderer_configuration_sha256=PDF_CONFIGURATION
)
FINGERPRINT = "c" * 64
ARTIFACT_ID = student_portfolio_presentation_artifact_id(
    preparation_fingerprint=FINGERPRINT,
    renderer_configuration_sha256=RENDERER_CONFIGURATION,
)


def _preparation() -> StudentPortfolioPresentationPreparation:
    return StudentPortfolioPresentationPreparation(
        contract_version="vitrine_student_portfolio_presentation_v1",
        observed_state_revision=8,
        snapshot_edition=SnapshotEditionRef(
            snapshot_series_id="series_1",
            edition_number=2,
        ),
        snapshot_export_artifact_id="export_1",
        snapshot_manifest_sha256="a" * 64,
        snapshot_logical_inventory_sha256="b" * 64,
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        profile_binding_id="binding_1",
        profile_revision=ProfileRevisionRef(
            portfolio_profile_id="profile_1",
            profile_revision=3,
        ),
        composition_revision=4,
        audience_context_id="audience_1",
        presentation_class="student_portfolio",
        audience_presentation_class="student_portfolio",
        student_display_name="Jordan Lee",
        portfolio_title="Improvement Portfolio",
        profile_label="Improvement Portfolio",
        purpose="Student-facing review",
        technical_export_relative_path="snapshots/export",
        technical_export_inventory_sha256="e" * 64,
        custody_namespace="presentations-bounded-v1",
        sections=(),
        file_item_count=0,
        reference_only_count=0,
        omitted_count=0,
        preparation_fingerprint=FINGERPRINT,
    )


def _package() -> StudentPortfolioPackageVerification:
    root = "presentations-bounded-v1/vp1_0123456789abcdef01234567"
    return StudentPortfolioPackageVerification(
        presentation_artifact_id=ARTIFACT_ID,
        relative_path=root,
        presentation_manifest_relative_path=(
            f"{root}/portfolio-presentation-manifest.json"
        ),
        presentation_manifest_sha256="1" * 64,
        html_relative_path=f"{root}/portfolio.html",
        html_sha256="2" * 64,
        printable_pdf_relative_path=(
            f"{root}/jordan-lee-improvement-portfolio-0123456789abcdef.pdf"
        ),
        printable_pdf_sha256="3" * 64,
        package_inventory_sha256="4" * 64,
        pdf_renderer_configuration_sha256=PDF_CONFIGURATION,
        renderer_configuration_sha256=RENDERER_CONFIGURATION,
        verified_file_paths=("portfolio.html",),
    )


def _artifact() -> PortfolioPresentationArtifact:
    preparation = _preparation()
    package = _package()
    return PortfolioPresentationArtifact(
        presentation_artifact_id=ARTIFACT_ID,
        snapshot_edition=preparation.snapshot_edition,
        snapshot_export_artifact_id=preparation.snapshot_export_artifact_id,
        portfolio_id=preparation.portfolio_id,
        portfolio_subject_id=preparation.portfolio_subject_id,
        profile_binding_id=preparation.profile_binding_id,
        profile_revision=preparation.profile_revision,
        audience_context_id=preparation.audience_context_id,
        presentation_class=preparation.presentation_class,
        presentation_contract_version=preparation.contract_version,
        renderer_id=STUDENT_PORTFOLIO_PRESENTATION_RENDERER_ID,
        renderer_version=STUDENT_PORTFOLIO_PRESENTATION_RENDERER_VERSION,
        renderer_contract_version=(
            STUDENT_PORTFOLIO_PRESENTATION_RENDERER_CONTRACT_VERSION
        ),
        renderer_configuration_digest=DigestReference(
            value=RENDERER_CONFIGURATION
        ),
        relative_path=package.relative_path,
        presentation_manifest_relative_path=(
            package.presentation_manifest_relative_path
        ),
        presentation_manifest_digest=DigestReference(
            value=package.presentation_manifest_sha256
        ),
        html_relative_path=package.html_relative_path,
        html_digest=DigestReference(value=package.html_sha256),
        printable_pdf_relative_path=package.printable_pdf_relative_path,
        printable_pdf_digest=DigestReference(
            value=package.printable_pdf_sha256
        ),
        package_inventory_digest=DigestReference(
            value=package.package_inventory_sha256
        ),
        generated_at=NOW,
        generated_by=ACTOR,
    )


def _patch_common(monkeypatch: pytest.MonkeyPatch) -> None:
    import vitrine.portfolio_presentation_services as module

    monkeypatch.setattr(
        module,
        "prepare_student_portfolio_presentation",
        lambda *_args, **_kwargs: _preparation(),
    )
    monkeypatch.setattr(
        module,
        "student_portfolio_pdf_renderer_configuration_sha256",
        lambda: PDF_CONFIGURATION,
    )


def test_presentation_identity_is_stable_and_configuration_sensitive() -> None:
    first = student_portfolio_presentation_artifact_id(
        preparation_fingerprint=FINGERPRINT,
        renderer_configuration_sha256=RENDERER_CONFIGURATION,
    )
    second = student_portfolio_presentation_artifact_id(
        preparation_fingerprint=FINGERPRINT,
        renderer_configuration_sha256=RENDERER_CONFIGURATION,
    )
    changed = student_portfolio_presentation_artifact_id(
        preparation_fingerprint=FINGERPRINT,
        renderer_configuration_sha256="f" * 64,
    )

    assert first == second == ARTIFACT_ID
    assert changed != first


def test_exact_existing_presentation_is_verified_and_reused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.portfolio_presentation_services as module

    _patch_common(monkeypatch)
    artifact = _artifact()
    package = _package()
    monkeypatch.setattr(module, "_load_state", lambda *_args: (22, (artifact,)))
    monkeypatch.setattr(
        module,
        "verify_portfolio_presentation",
        lambda *_args, **_kwargs: SimpleNamespace(
            presentation_artifact_id=ARTIFACT_ID
        ),
    )
    monkeypatch.setattr(
        module,
        "verify_student_portfolio_file_package",
        lambda *_args, **_kwargs: package,
    )
    monkeypatch.setattr(
        module,
        "create_student_portfolio_file_package",
        lambda *_args, **_kwargs: pytest.fail("existing presentation must be reused"),
    )

    result = build_student_portfolio_presentation(
        ".",
        snapshot_series_id="series_1",
        edition_number=2,
        snapshot_export_artifact_id="export_1",
        generated_by=ACTOR,
    )

    assert result.disposition == "existing"
    assert result.state_revision == 22
    assert result.presentation_artifact_id == ARTIFACT_ID


def test_durable_unpublished_package_is_adopted_without_regeneration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.portfolio_presentation_services as module

    _patch_common(monkeypatch)
    package = _package()
    state_calls = iter(((22, ()), (22, ())))
    monkeypatch.setattr(module, "_load_state", lambda *_args: next(state_calls))
    monkeypatch.setattr(module, "_package_exists", lambda *_args: True)
    monkeypatch.setattr(
        module,
        "_verify_unpublished_package",
        lambda *_args, **_kwargs: package,
    )
    monkeypatch.setattr(
        module,
        "create_student_portfolio_file_package",
        lambda *_args, **_kwargs: pytest.fail("durable package must not be regenerated"),
    )
    captured: dict[str, object] = {}

    def commit(_root, records, *, expected_state_revision):
        captured["record"] = tuple(records)[0]
        captured["expected"] = expected_state_revision
        return SimpleNamespace(state_revision=23)

    monkeypatch.setattr(module, "commit_record_batch", commit)
    monkeypatch.setattr(
        module,
        "verify_portfolio_presentation",
        lambda *_args, **_kwargs: SimpleNamespace(
            presentation_artifact_id=ARTIFACT_ID
        ),
    )

    result = build_student_portfolio_presentation(
        ".",
        snapshot_series_id="series_1",
        edition_number=2,
        snapshot_export_artifact_id="export_1",
        generated_by=ACTOR,
        clock=lambda: NOW,
    )

    assert result.disposition == "recovered"
    assert result.state_revision == 23
    assert captured["expected"] == 22
    persisted = captured["record"]
    assert isinstance(persisted, PortfolioPresentationArtifact)
    assert persisted.presentation_artifact_id == ARTIFACT_ID


def test_new_package_is_verified_before_canonical_publication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.portfolio_presentation_services as module

    _patch_common(monkeypatch)
    package = _package()
    state_calls = iter(((22, ()), (22, ())))
    monkeypatch.setattr(module, "_load_state", lambda *_args: next(state_calls))
    monkeypatch.setattr(module, "_package_exists", lambda *_args: False)
    calls: list[str] = []
    monkeypatch.setattr(
        module,
        "create_student_portfolio_file_package",
        lambda *_args, **_kwargs: calls.append("package"),
    )
    monkeypatch.setattr(
        module,
        "_verify_unpublished_package",
        lambda *_args, **_kwargs: (calls.append("verify_package"), package)[1],
    )

    def commit(*_args, **_kwargs):
        calls.append("commit")
        return SimpleNamespace(state_revision=23)

    monkeypatch.setattr(module, "commit_record_batch", commit)
    monkeypatch.setattr(
        module,
        "verify_portfolio_presentation",
        lambda *_args, **_kwargs: (
            calls.append("verify_canonical"),
            SimpleNamespace(presentation_artifact_id=ARTIFACT_ID),
        )[1],
    )

    result = build_student_portfolio_presentation(
        ".",
        snapshot_series_id="series_1",
        edition_number=2,
        snapshot_export_artifact_id="export_1",
        generated_by=ACTOR,
        clock=lambda: NOW,
    )

    assert result.disposition == "created"
    assert calls == ["package", "verify_package", "commit", "verify_canonical"]


def test_canonical_commit_failure_preserves_resume_from_exact_edition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.portfolio_presentation_services as module

    _patch_common(monkeypatch)
    package = _package()
    state_calls = iter(((22, ()), (22, ()), (22, ())))
    monkeypatch.setattr(module, "_load_state", lambda *_args: next(state_calls))
    monkeypatch.setattr(module, "_package_exists", lambda *_args: False)
    monkeypatch.setattr(
        module,
        "create_student_portfolio_file_package",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        module,
        "_verify_unpublished_package",
        lambda *_args, **_kwargs: package,
    )

    def conflict(*_args, **_kwargs):
        raise VitrineStorageConflictError("synthetic conflict")

    monkeypatch.setattr(module, "commit_record_batch", conflict)

    with pytest.raises(PortfolioPresentationBuildError) as caught:
        build_student_portfolio_presentation(
            ".",
            snapshot_series_id="series_1",
            edition_number=2,
            snapshot_export_artifact_id="export_1",
            generated_by=ACTOR,
            clock=lambda: NOW,
        )

    assert caught.value.code == "portfolio_presentation_build.canonical_commit_failed"
    assert caught.value.presentation_artifact_id == ARTIFACT_ID
    assert caught.value.next_safe_action == "resume_presentation_existing_edition"

def test_partial_canonical_commit_requires_storage_inspection_before_resume(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.portfolio_presentation_services as module

    _patch_common(monkeypatch)
    package = _package()
    state_calls = iter(((22, ()), (22, ()), (22, ())))
    monkeypatch.setattr(module, "_load_state", lambda *_args: next(state_calls))
    monkeypatch.setattr(module, "_package_exists", lambda *_args: False)
    monkeypatch.setattr(
        module,
        "create_student_portfolio_file_package",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        module,
        "_verify_unpublished_package",
        lambda *_args, **_kwargs: package,
    )

    def partial(*_args, **_kwargs):
        raise VitrineStoragePartialSuccessError(
            "synthetic partial canonical write",
            durable_paths=("records-bounded-v1/example",),
            pointer_published=False,
            state_revision=None,
            state_sha256=None,
        )

    monkeypatch.setattr(module, "commit_record_batch", partial)

    with pytest.raises(PortfolioPresentationBuildError) as caught:
        build_student_portfolio_presentation(
            ".",
            snapshot_series_id="series_1",
            edition_number=2,
            snapshot_export_artifact_id="export_1",
            generated_by=ACTOR,
            clock=lambda: NOW,
        )

    assert caught.value.code == "portfolio_presentation_build.canonical_commit_failed"
    assert caught.value.next_safe_action == (
        "inspect_canonical_storage_then_resume_presentation"
    )



def test_explicit_resume_clears_exact_staging_then_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.portfolio_presentation_services as module

    expected = SimpleNamespace(disposition="created")
    calls: list[str] = []

    def build(*_args, **_kwargs):
        calls.append("build")
        if calls.count("build") == 1:
            raise PortfolioPresentationBuildError(
                "portfolio_presentation_build.package_failed",
                "synthetic retained staging",
                stage="package",
                underlying_code="portfolio_presentation_package.staging_conflict",
                underlying_stage="staging",
                presentation_artifact_id=ARTIFACT_ID,
                next_safe_action="inspect_presentation_staging_then_resume",
            )
        return expected

    def clear(*_args, **kwargs):
        calls.append(f"clear:{kwargs['presentation_artifact_id']}")
        return True

    monkeypatch.setattr(module, "build_student_portfolio_presentation", build)
    monkeypatch.setattr(
        module,
        "clear_student_portfolio_file_package_staging",
        clear,
    )

    result = module.resume_student_portfolio_presentation(
        ".",
        snapshot_series_id="series_1",
        edition_number=2,
        snapshot_export_artifact_id="export_1",
        generated_by=ACTOR,
    )

    assert result is expected
    assert calls == ["build", f"clear:{ARTIFACT_ID}", "build"]
