from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from vitrine.models import DigestReference, ProfileRevisionRef, SnapshotEditionRef
from vitrine.portfolio_presentation import (
    StudentPortfolioPresentationItem,
    StudentPortfolioPresentationPreparation,
    StudentPortfolioPresentationSection,
    presentation_artifact_custody_relative_path,
)
from vitrine.portfolio_presentation_package import (
    PRESENTATION_MANIFEST_FILENAME,
    PortfolioPresentationPackageError,
    create_student_portfolio_file_package,
)

PAYLOAD = b"exact frozen student work bytes\n"
PAYLOAD_SHA = hashlib.sha256(PAYLOAD).hexdigest()
EXPORT_SHA = "e" * 64
MANIFEST_SHA = "a" * 64
LOGICAL_SHA = "b" * 64
FINGERPRINT = "c" * 64


def _item(
    *,
    entry_plan_id: str,
    disposition: str,
    export_file_available: bool,
    presentation_filename: str | None,
    technical_relative_path: str | None,
) -> StudentPortfolioPresentationItem:
    return StudentPortfolioPresentationItem(
        entry_plan_id=entry_plan_id,
        plan_position={"entry_file": 1, "entry_ref": 2, "entry_omit": 3}[entry_plan_id],
        section_id="selected_work",
        ordinal={"entry_file": 1, "entry_ref": 2, "entry_omit": 3}[entry_plan_id],
        semantic_role="selected_work",
        content_class=("student_work" if disposition == "included" else "assessment_summary"),
        materialization_kind=("copied_source" if disposition == "included" else "reference_only"),
        disposition=disposition,
        display_title={
            "entry_file": "Revised Argument",
            "entry_ref": "Benchmark Snapshot",
            "entry_omit": "Optional Note",
        }[entry_plan_id],
        display_caption=(
            "A meaningful student-facing caption."
            if disposition == "included"
            else None
        ),
        source_credit=None,
        presentation_note=(
            None
            if disposition == "included"
            else "No portable file is available for this exact Portfolio Edition."
        ),
        candidate_id=f"candidate_{entry_plan_id}",
        selection_id=f"selection_{entry_plan_id}",
        placement_id=f"placement_{entry_plan_id}",
        snapshot_entry_id="snapshot_entry_1" if disposition == "included" else None,
        materialization_id=(
            "materialization_1" if disposition != "omitted_permitted" else None
        ),
        omission_id="omission_1" if disposition == "omitted_permitted" else None,
        technical_relative_path=technical_relative_path,
        media_type="application/pdf" if disposition == "included" else None,
        byte_size=len(PAYLOAD) if disposition == "included" else None,
        output_sha256=PAYLOAD_SHA if disposition == "included" else None,
        export_file_available=export_file_available,
        presentation_filename=presentation_filename,
    )


def _preparation() -> StudentPortfolioPresentationPreparation:
    section = StudentPortfolioPresentationSection(
        section_id="selected_work",
        label="Selected Work",
        purpose="Work selected to show growth.",
        order=1,
        obligation="required",
        presentation_directory_name="01-selected-work-0123456789abcdef",
        items=(
            _item(
                entry_plan_id="entry_file",
                disposition="included",
                export_file_available=True,
                presentation_filename="revised-argument-0123456789abcdef.pdf",
                technical_relative_path="section-01/01-entry-opaque",
            ),
            _item(
                entry_plan_id="entry_ref",
                disposition="reference_only",
                export_file_available=False,
                presentation_filename=None,
                technical_relative_path=None,
            ),
            _item(
                entry_plan_id="entry_omit",
                disposition="omitted_permitted",
                export_file_available=False,
                presentation_filename=None,
                technical_relative_path=None,
            ),
        ),
    )
    return StudentPortfolioPresentationPreparation(
        contract_version="vitrine_student_portfolio_presentation_v1",
        observed_state_revision=8,
        snapshot_edition=SnapshotEditionRef(
            snapshot_series_id="series_1", edition_number=1
        ),
        snapshot_export_artifact_id="export_1",
        snapshot_manifest_sha256=MANIFEST_SHA,
        snapshot_logical_inventory_sha256=LOGICAL_SHA,
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        profile_binding_id="binding_1",
        profile_revision=ProfileRevisionRef(
            portfolio_profile_id="profile_1", profile_revision=2
        ),
        composition_revision=3,
        audience_context_id="audience_1",
        presentation_class="student_portfolio",
        audience_presentation_class="student_portfolio",
        student_display_name="Jordan Lee",
        portfolio_title="Improvement Portfolio",
        profile_label="Improvement Portfolio",
        purpose="Student reflection and review",
        technical_export_relative_path="technical-export",
        technical_export_inventory_sha256=EXPORT_SHA,
        custody_namespace="presentations-bounded-v1",
        sections=(section,),
        file_item_count=1,
        reference_only_count=1,
        omitted_count=1,
        preparation_fingerprint=FINGERPRINT,
    )


def _install_test_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Path:
    import vitrine.portfolio_presentation_package as module

    export_root = tmp_path / "vitrine" / "technical-export"
    source = export_root / "section-01" / "01-entry-opaque"
    source.parent.mkdir(parents=True)
    source.write_bytes(PAYLOAD)

    def fake_safe_vitrine_descendant(root: str | Path, relative_path: str) -> Path:
        return Path(root) / "vitrine" / Path(*relative_path.split("/"))

    monkeypatch.setattr(module, "safe_vitrine_descendant", fake_safe_vitrine_descendant)
    monkeypatch.setattr(
        module,
        "snapshot_export_path_from_relative",
        lambda _root, _relative: export_root,
    )
    monkeypatch.setattr(
        module,
        "verify_snapshot_export",
        lambda *_args, **_kwargs: SimpleNamespace(
            snapshot_export_artifact_id="export_1",
            snapshot_series_id="series_1",
            edition_number=1,
            directory_inventory_digest=DigestReference(value=EXPORT_SHA),
            verified_file_paths=("section-01/01-entry-opaque",),
        ),
    )
    return export_root


def test_file_package_copies_exact_bytes_and_writes_honest_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_test_paths(monkeypatch, tmp_path)
    result = create_student_portfolio_file_package(
        tmp_path,
        _preparation(),
        presentation_artifact_id="presentation_1",
    )

    package_root = tmp_path / "vitrine" / Path(*result.relative_path.split("/"))
    copied = package_root / "01-selected-work-0123456789abcdef" / (
        "revised-argument-0123456789abcdef.pdf"
    )
    assert copied.read_bytes() == PAYLOAD
    assert result.copied_file_paths == (
        "01-selected-work-0123456789abcdef/"
        "revised-argument-0123456789abcdef.pdf",
    )

    manifest_payload = (package_root / PRESENTATION_MANIFEST_FILENAME).read_bytes()
    assert hashlib.sha256(manifest_payload).hexdigest() == result.manifest_sha256
    manifest = json.loads(manifest_payload)
    assert manifest["snapshot"]["manifest_sha256"] == MANIFEST_SHA
    assert manifest["snapshot"]["logical_inventory_sha256"] == LOGICAL_SHA
    assert manifest["technical_export"]["directory_inventory_sha256"] == EXPORT_SHA
    assert manifest["generated_outputs"] == {"html": None, "printable_pdf": None}

    file_item, reference_item, omitted_item = manifest["sections"][0]["items"]
    assert file_item["presentation_relative_path"].endswith(".pdf")
    assert file_item["sha256"] == PAYLOAD_SHA
    assert file_item["byte_size"] == len(PAYLOAD)
    assert reference_item["disposition"] == "reference_only"
    assert reference_item["presentation_relative_path"] is None
    assert reference_item["sha256"] is None
    assert omitted_item["disposition"] == "omitted_permitted"
    assert omitted_item["presentation_relative_path"] is None

    manifest_text = manifest_payload.decode("utf-8")
    assert "section-01/01-entry-opaque" not in manifest_text
    assert "technical-export" not in manifest_text


def test_file_package_is_create_only_and_never_overwrites_successful_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_test_paths(monkeypatch, tmp_path)
    preparation = _preparation()
    first = create_student_portfolio_file_package(
        tmp_path,
        preparation,
        presentation_artifact_id="presentation_1",
    )
    package_root = tmp_path / "vitrine" / Path(*first.relative_path.split("/"))
    manifest_before = (package_root / PRESENTATION_MANIFEST_FILENAME).read_bytes()

    with pytest.raises(PortfolioPresentationPackageError) as caught:
        create_student_portfolio_file_package(
            tmp_path,
            preparation,
            presentation_artifact_id="presentation_1",
        )

    assert caught.value.code == "portfolio_presentation_package.custody_conflict"
    assert (package_root / PRESENTATION_MANIFEST_FILENAME).read_bytes() == manifest_before


def test_copy_mismatch_fails_closed_and_rolls_back_partial_custody(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    export_root = _install_test_paths(monkeypatch, tmp_path)
    (export_root / "section-01" / "01-entry-opaque").write_bytes(b"tampered")

    with pytest.raises(PortfolioPresentationPackageError) as caught:
        create_student_portfolio_file_package(
            tmp_path,
            _preparation(),
            presentation_artifact_id="presentation_bad",
        )

    assert caught.value.code == "portfolio_presentation_package.source_mismatch"
    relative = presentation_artifact_custody_relative_path("presentation_bad")
    final_root = tmp_path / "vitrine" / Path(*relative.split("/"))
    assert not final_root.exists()


def test_manifest_bytes_are_deterministic_for_same_exact_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_root = tmp_path / "first"
    _install_test_paths(monkeypatch, first_root)
    first = create_student_portfolio_file_package(
        first_root,
        _preparation(),
        presentation_artifact_id="presentation_deterministic",
    )
    first_package = first_root / "vitrine" / Path(*first.relative_path.split("/"))
    first_manifest = (first_package / PRESENTATION_MANIFEST_FILENAME).read_bytes()

    second_root = tmp_path / "second"
    _install_test_paths(monkeypatch, second_root)
    second = create_student_portfolio_file_package(
        second_root,
        _preparation(),
        presentation_artifact_id="presentation_deterministic",
    )
    second_package = second_root / "vitrine" / Path(*second.relative_path.split("/"))
    second_manifest = (second_package / PRESENTATION_MANIFEST_FILENAME).read_bytes()

    assert first_manifest == second_manifest
    assert first.manifest_sha256 == second.manifest_sha256
    assert first.package_inventory_sha256 == second.package_inventory_sha256
