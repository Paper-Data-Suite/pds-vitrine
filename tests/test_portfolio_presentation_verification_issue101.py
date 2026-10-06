from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from vitrine.models import (
    ActorAttribution,
    DigestReference,
    PortfolioPresentationArtifact,
    ProfileRevisionRef,
    SnapshotEditionRef,
)
from vitrine.portfolio_presentation import (
    StudentPortfolioPresentationItem,
    StudentPortfolioPresentationPreparation,
    StudentPortfolioPresentationSection,
)
from vitrine.portfolio_presentation_contract import (
    STUDENT_PORTFOLIO_PRESENTATION_RENDERER_CONTRACT_VERSION,
    STUDENT_PORTFOLIO_PRESENTATION_RENDERER_ID,
    STUDENT_PORTFOLIO_PRESENTATION_RENDERER_VERSION,
    student_portfolio_renderer_configuration_sha256,
)
from vitrine.portfolio_presentation_package import create_student_portfolio_file_package
from vitrine.portfolio_presentation_verification import (
    PortfolioPresentationVerificationError,
    verify_portfolio_presentation,
    verify_student_portfolio_file_package,
)

NOW = datetime(2026, 10, 4, 19, 0, tzinfo=timezone.utc)
ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="teacher_1",
    owning_system="vitrine",
    role_snapshot="teacher",
)
SOURCE = b"exact frozen source bytes\n"
SOURCE_SHA = hashlib.sha256(SOURCE).hexdigest()
PDF = b"%PDF-1.4\n% exact synthetic presentation\n"
PDF_SHA = hashlib.sha256(PDF).hexdigest()
PDF_NAME = "jordan-lee-improvement-portfolio-0123456789abcdef.pdf"
PDF_CONFIGURATION = "d" * 64
MANIFEST_SHA = "a" * 64
LOGICAL_SHA = "b" * 64
EXPORT_SHA = "e" * 64


def _preparation() -> StudentPortfolioPresentationPreparation:
    item = StudentPortfolioPresentationItem(
        entry_plan_id="entry_1",
        plan_position=1,
        section_id="baseline",
        ordinal=1,
        semantic_role="selected_work",
        content_class="student_work",
        materialization_kind="copied_source",
        disposition="included",
        display_title="Argument Paragraph - First Draft",
        display_caption="My starting point.",
        source_credit=None,
        presentation_note=None,
        candidate_id="candidate_1",
        selection_id="selection_1",
        placement_id="placement_1",
        snapshot_entry_id="snapshot_entry_1",
        materialization_id="materialization_1",
        omission_id=None,
        technical_relative_path="section-01/01-entry-opaque",
        media_type="text/plain",
        byte_size=len(SOURCE),
        output_sha256=SOURCE_SHA,
        export_file_available=True,
        presentation_filename="argument-paragraph-first-draft-0123456789abcdef.txt",
    )
    section = StudentPortfolioPresentationSection(
        section_id="baseline",
        label="Baseline Evidence",
        purpose="A starting point for comparison.",
        order=1,
        obligation="required",
        presentation_directory_name="01-baseline-evidence-0123456789abcdef",
        items=(item,),
    )
    return StudentPortfolioPresentationPreparation(
        contract_version="vitrine_student_portfolio_presentation_v1",
        observed_state_revision=20,
        snapshot_edition=SnapshotEditionRef(
            snapshot_series_id="series_1",
            edition_number=1,
        ),
        snapshot_export_artifact_id="export_1",
        snapshot_manifest_sha256=MANIFEST_SHA,
        snapshot_logical_inventory_sha256=LOGICAL_SHA,
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        profile_binding_id="binding_1",
        profile_revision=ProfileRevisionRef(
            portfolio_profile_id="profile_1",
            profile_revision=1,
        ),
        composition_revision=2,
        audience_context_id="audience_1",
        presentation_class="student_portfolio",
        audience_presentation_class="student_portfolio",
        student_display_name="Jordan Lee",
        portfolio_title="Improvement Portfolio",
        profile_label="Improvement Portfolio",
        purpose="Student-facing review",
        technical_export_relative_path="technical-export",
        technical_export_inventory_sha256=EXPORT_SHA,
        custody_namespace="presentations-bounded-v1",
        sections=(section,),
        file_item_count=1,
        reference_only_count=0,
        omitted_count=0,
        preparation_fingerprint="c" * 64,
    )


def _safe(root: str | Path, relative: str) -> Path:
    return Path(root) / "vitrine" / Path(*relative.split("/"))


def _install_package_patches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import vitrine.portfolio_presentation_package as package_module

    export_root = tmp_path / "vitrine" / "technical-export"
    source = export_root / "section-01" / "01-entry-opaque"
    source.parent.mkdir(parents=True)
    source.write_bytes(SOURCE)
    monkeypatch.setattr(package_module, "safe_vitrine_descendant", _safe)
    monkeypatch.setattr(
        package_module,
        "snapshot_export_path_from_relative",
        lambda *_args, **_kwargs: export_root,
    )
    monkeypatch.setattr(
        package_module,
        "verify_snapshot_export",
        lambda *_args, **_kwargs: SimpleNamespace(
            snapshot_series_id="series_1",
            edition_number=1,
            directory_inventory_digest=DigestReference(value=EXPORT_SHA),
            verified_file_paths=("section-01/01-entry-opaque",),
        ),
    )
    monkeypatch.setattr(
        package_module,
        "render_student_portfolio_pdf",
        lambda *_args, **_kwargs: SimpleNamespace(
            filename=PDF_NAME,
            payload=PDF,
            sha256=PDF_SHA,
            byte_size=len(PDF),
            page_count=4,
            renderer_id="vitrine_student_portfolio_pdf_renderer",
            renderer_version="1",
            renderer_contract_version="vitrine_student_portfolio_pdf_v1",
            renderer_configuration_sha256=PDF_CONFIGURATION,
            item_dispositions=(
                SimpleNamespace(
                    entry_plan_id="entry_1",
                    print_disposition="rendered_from_exact_source",
                    page_count=1,
                ),
            ),
        ),
    )


def _install_verification_patches(monkeypatch: pytest.MonkeyPatch) -> None:
    import vitrine.portfolio_presentation_verification as module

    monkeypatch.setattr(module, "safe_vitrine_descendant", _safe)
    monkeypatch.setattr(
        module,
        "verify_snapshot_edition",
        lambda *_args, **_kwargs: SimpleNamespace(
            manifest_digest=DigestReference(value=MANIFEST_SHA),
            logical_inventory_digest=DigestReference(value=LOGICAL_SHA),
        ),
    )
    monkeypatch.setattr(
        module,
        "verify_snapshot_export",
        lambda *_args, **_kwargs: SimpleNamespace(
            snapshot_series_id="series_1",
            edition_number=1,
            directory_inventory_digest=DigestReference(value=EXPORT_SHA),
        ),
    )


def test_published_package_verifies_exact_files_and_generated_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_package_patches(monkeypatch, tmp_path)
    _install_verification_patches(monkeypatch)
    preparation = _preparation()
    created = create_student_portfolio_file_package(
        tmp_path,
        preparation,
        presentation_artifact_id="presentation_exact",
    )

    verified = verify_student_portfolio_file_package(
        tmp_path,
        preparation,
        presentation_artifact_id="presentation_exact",
        expected_manifest_sha256=created.manifest_sha256,
        expected_html_sha256=created.html_sha256,
        expected_printable_pdf_sha256=created.printable_pdf_sha256,
        expected_package_inventory_sha256=created.package_inventory_sha256,
    )

    assert verified.presentation_manifest_sha256 == created.manifest_sha256
    assert verified.html_sha256 == created.html_sha256
    assert verified.printable_pdf_sha256 == created.printable_pdf_sha256
    assert verified.package_inventory_sha256 == created.package_inventory_sha256
    assert verified.pdf_renderer_configuration_sha256 == PDF_CONFIGURATION
    assert len(verified.verified_file_paths) == 3


def test_verification_detects_one_changed_source_byte(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_package_patches(monkeypatch, tmp_path)
    _install_verification_patches(monkeypatch)
    preparation = _preparation()
    created = create_student_portfolio_file_package(
        tmp_path,
        preparation,
        presentation_artifact_id="presentation_tampered",
    )
    root = _safe(tmp_path, created.relative_path)
    source = root / "01-baseline-evidence-0123456789abcdef" / (
        "argument-paragraph-first-draft-0123456789abcdef.txt"
    )
    source.write_bytes(SOURCE[:-1] + b"X")

    with pytest.raises(PortfolioPresentationVerificationError) as caught:
        verify_student_portfolio_file_package(
            tmp_path,
            preparation,
            presentation_artifact_id="presentation_tampered",
        )

    assert caught.value.code == "portfolio_presentation_verification.file_mismatch"


def test_verification_rejects_unexpected_package_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_package_patches(monkeypatch, tmp_path)
    _install_verification_patches(monkeypatch)
    preparation = _preparation()
    created = create_student_portfolio_file_package(
        tmp_path,
        preparation,
        presentation_artifact_id="presentation_extra",
    )
    root = _safe(tmp_path, created.relative_path)
    (root / "unexpected.txt").write_text("unexpected", encoding="utf-8")

    with pytest.raises(PortfolioPresentationVerificationError) as caught:
        verify_student_portfolio_file_package(
            tmp_path,
            preparation,
            presentation_artifact_id="presentation_extra",
        )

    assert caught.value.code == "portfolio_presentation_verification.unexpected_file"


def test_canonical_verification_binds_exact_artifact_and_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.portfolio_presentation_verification as module

    _install_package_patches(monkeypatch, tmp_path)
    _install_verification_patches(monkeypatch)
    preparation = _preparation()
    created = create_student_portfolio_file_package(
        tmp_path,
        preparation,
        presentation_artifact_id="presentation_canonical",
    )
    renderer_configuration = student_portfolio_renderer_configuration_sha256(
        pdf_renderer_configuration_sha256=PDF_CONFIGURATION
    )
    artifact = PortfolioPresentationArtifact(
        presentation_artifact_id="presentation_canonical",
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
            value=renderer_configuration
        ),
        relative_path=created.relative_path,
        presentation_manifest_relative_path=created.manifest_relative_path,
        presentation_manifest_digest=DigestReference(value=created.manifest_sha256),
        html_relative_path=created.html_relative_path,
        html_digest=DigestReference(value=created.html_sha256),
        printable_pdf_relative_path=created.printable_pdf_relative_path,
        printable_pdf_digest=DigestReference(value=created.printable_pdf_sha256),
        package_inventory_digest=DigestReference(
            value=created.package_inventory_sha256
        ),
        generated_at=NOW,
        generated_by=ACTOR,
    )
    monkeypatch.setattr(
        module,
        "load_current_records_with_state",
        lambda *_args, **_kwargs: (SimpleNamespace(state_revision=21), (artifact,)),
    )
    monkeypatch.setattr(
        module,
        "prepare_student_portfolio_presentation",
        lambda *_args, **_kwargs: preparation,
    )

    verified = verify_portfolio_presentation(
        tmp_path,
        presentation_artifact_id="presentation_canonical",
    )

    assert verified.presentation_artifact_id == "presentation_canonical"
    assert verified.snapshot_export_artifact_id == "export_1"
    assert verified.printable_pdf_sha256 == created.printable_pdf_sha256


def test_package_uses_bounded_staging_and_publishes_without_residue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_package_patches(monkeypatch, tmp_path)
    created = create_student_portfolio_file_package(
        tmp_path,
        _preparation(),
        presentation_artifact_id="presentation_staged",
    )

    final_root = _safe(tmp_path, created.relative_path)
    namespace = final_root.parent
    assert final_root.is_dir()
    assert not any(path.name.startswith("staging-") for path in namespace.iterdir())
    assert not any(path.name.startswith("publication-") for path in namespace.iterdir())


def test_existing_staging_is_preserved_for_explicit_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.portfolio_presentation_package as module

    _install_package_patches(monkeypatch, tmp_path)
    relative = module._presentation_staging_relative_path("presentation_interrupted")
    staging = _safe(tmp_path, relative)
    staging.mkdir(parents=True)
    marker = staging / "partial-marker.txt"
    marker.write_text("partial", encoding="utf-8")

    with pytest.raises(module.PortfolioPresentationPackageError) as caught:
        create_student_portfolio_file_package(
            tmp_path,
            _preparation(),
            presentation_artifact_id="presentation_interrupted",
        )

    assert caught.value.code == "portfolio_presentation_package.staging_conflict"
    assert marker.read_text(encoding="utf-8") == "partial"


def test_explicit_staging_recovery_clears_only_bounded_residue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vitrine.portfolio_presentation_package as module

    _install_package_patches(monkeypatch, tmp_path)
    artifact_id = "presentation_resume"
    staging = _safe(
        tmp_path,
        module._presentation_staging_relative_path(artifact_id),
    )
    lock = _safe(
        tmp_path,
        module._presentation_publication_lock_relative_path(artifact_id),
    )
    staging.mkdir(parents=True)
    (staging / "partial.txt").write_text("partial", encoding="utf-8")
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_bytes(b"vitrine-presentation-publication-v1\n")

    cleaned = module.clear_student_portfolio_file_package_staging(
        tmp_path,
        presentation_artifact_id=artifact_id,
    )

    assert cleaned is True
    assert not staging.exists()
    assert not lock.exists()
