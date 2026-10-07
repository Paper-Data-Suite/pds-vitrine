"""Issue #102 Slice 3: verified local-use boundary for completed output."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from pds_core.local_open import LocalOpenError

from vitrine import portfolio_output_opening as opening
from vitrine.models import (
    ActorAttribution,
    DigestReference,
    PortfolioPresentationArtifact,
    ProfileRevisionRef,
    SnapshotEditionRef,
    SnapshotExportArtifact,
)
from vitrine.portfolio_presentation_verification import (
    PortfolioPresentationVerificationError,
)

NOW = datetime(2026, 10, 6, 22, 0, tzinfo=timezone.utc)
ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="teacher_1",
    owning_system="vitrine",
    role_snapshot="teacher",
)
PROFILE = ProfileRevisionRef(portfolio_profile_id="profile_1", profile_revision=2)
EDITION = SnapshotEditionRef(snapshot_series_id="series_1", edition_number=3)


def _presentation() -> PortfolioPresentationArtifact:
    root = "presentations-bounded-v1/presentation_1"
    return PortfolioPresentationArtifact(
        presentation_artifact_id="presentation_1",
        snapshot_edition=EDITION,
        snapshot_export_artifact_id="export_1",
        portfolio_id="portfolio_1",
        portfolio_subject_id="subject_1",
        profile_binding_id="binding_1",
        profile_revision=PROFILE,
        audience_context_id="audience_1",
        presentation_class="student_portfolio",
        presentation_contract_version="vitrine_student_portfolio_presentation_v1",
        renderer_id="vitrine_student_portfolio_renderer",
        renderer_version="1",
        renderer_contract_version="vitrine_student_portfolio_renderer_v1",
        renderer_configuration_digest=DigestReference(value="1" * 64),
        relative_path=root,
        presentation_manifest_relative_path=f"{root}/presentation-manifest.json",
        presentation_manifest_digest=DigestReference(value="2" * 64),
        html_relative_path=f"{root}/portfolio.html",
        html_digest=DigestReference(value="3" * 64),
        printable_pdf_relative_path=f"{root}/portfolio.pdf",
        printable_pdf_digest=DigestReference(value="4" * 64),
        package_inventory_digest=DigestReference(value="5" * 64),
        generated_at=NOW,
        generated_by=ACTOR,
    )


def _export() -> SnapshotExportArtifact:
    return SnapshotExportArtifact(
        snapshot_export_artifact_id="export_1",
        snapshot_edition=EDITION,
        export_format="directory_package",
        export_contract_version="snapshot_directory_v1",
        included_entry_ids=("entry_1",),
        excluded_entry_ids=(),
        packager_id="snapshot_packager",
        packager_version="1",
        configuration_digest=DigestReference(value="6" * 64),
        generated_at=NOW,
        relative_path="snapshots/exports-bounded-v1/export_1",
        directory_inventory_digest=DigestReference(value="7" * 64),
        validation_result="verified",
    )


def _install_canonical(monkeypatch: pytest.MonkeyPatch) -> None:
    presentation = _presentation()
    export = _export()
    monkeypatch.setattr(
        opening,
        "load_current_records_with_state",
        lambda *_args: (SimpleNamespace(state_revision=44), (presentation, export)),
    )


def _make_targets(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    presentation_root = (
        tmp_path / "vitrine" / "presentations-bounded-v1" / "presentation_1"
    )
    presentation_root.mkdir(parents=True)
    html = presentation_root / "portfolio.html"
    pdf = presentation_root / "portfolio.pdf"
    html.write_text("<html></html>", encoding="utf-8")
    pdf.write_bytes(b"%PDF-1.4\n")
    export_root = (
        tmp_path / "vitrine" / "snapshots" / "exports-bounded-v1" / "export_1"
    )
    export_root.mkdir(parents=True)
    return presentation_root, html, pdf, export_root


def test_presentation_actions_verify_before_exact_core_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_canonical(monkeypatch)
    presentation_root, html, pdf, _export_root = _make_targets(tmp_path)
    events: list[tuple[str, object]] = []

    def verify(_root: Path, *, presentation_artifact_id: str):
        events.append(("verify", presentation_artifact_id))
        return SimpleNamespace(presentation_artifact_id=presentation_artifact_id)

    monkeypatch.setattr(opening, "verify_portfolio_presentation", verify)
    monkeypatch.setattr(
        opening,
        "open_local_path",
        lambda path: events.append(("open", Path(path))) or Path(path),
    )

    assert opening.open_student_portfolio_html(
        tmp_path, presentation_artifact_id="presentation_1"
    ) == html.resolve()
    assert opening.open_printable_student_portfolio(
        tmp_path, presentation_artifact_id="presentation_1"
    ) == pdf.resolve()
    assert opening.open_student_portfolio_folder(
        tmp_path, presentation_artifact_id="presentation_1"
    ) == presentation_root.resolve()

    assert events == [
        ("verify", "presentation_1"),
        ("open", html.resolve()),
        ("verify", "presentation_1"),
        ("open", pdf.resolve()),
        ("verify", "presentation_1"),
        ("open", presentation_root.resolve()),
    ]


def test_technical_export_verifies_exact_artifact_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_canonical(monkeypatch)
    _presentation_root, _html, _pdf, export_root = _make_targets(tmp_path)
    events: list[tuple[str, object]] = []

    def verify(_root: Path, *, snapshot_export_artifact_id: str):
        events.append(("verify", snapshot_export_artifact_id))
        return SimpleNamespace(
            snapshot_export_artifact_id=snapshot_export_artifact_id
        )

    monkeypatch.setattr(opening, "verify_snapshot_export", verify)
    monkeypatch.setattr(
        opening,
        "open_local_path",
        lambda path: events.append(("open", Path(path))) or Path(path),
    )

    assert opening.open_technical_export_folder(
        tmp_path, snapshot_export_artifact_id="export_1"
    ) == export_root.resolve()
    assert events == [
        ("verify", "export_1"),
        ("open", export_root.resolve()),
    ]


def test_verification_failure_prevents_local_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_canonical(monkeypatch)
    _make_targets(tmp_path)
    opened: list[Path] = []

    def fail(*_args: object, **_kwargs: object):
        raise PortfolioPresentationVerificationError(
            "portfolio_presentation_verification.file_mismatch",
            "synthetic mismatch",
            stage="verification",
        )

    monkeypatch.setattr(opening, "verify_portfolio_presentation", fail)
    monkeypatch.setattr(
        opening, "open_local_path", lambda path: opened.append(Path(path))
    )

    with pytest.raises(opening.PortfolioOutputOpenError) as caught:
        opening.open_student_portfolio_html(
            tmp_path, presentation_artifact_id="presentation_1"
        )

    assert caught.value.code == "portfolio_output.verification_failed"
    assert caught.value.underlying_code == (
        "portfolio_presentation_verification.file_mismatch"
    )
    assert opened == []


def test_workspace_escaping_symlink_is_rejected_after_verification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    presentation = _presentation()
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (outside / "portfolio.html").write_text("<html></html>", encoding="utf-8")
    (outside / "portfolio.pdf").write_bytes(b"%PDF-1.4\n")
    vitrine = tmp_path / "vitrine"
    vitrine.mkdir()
    link = vitrine / "presentations-bounded-v1" / "presentation_1"
    link.parent.mkdir()
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (NotImplementedError, OSError):
        pytest.skip("Directory symlinks are unavailable on this platform.")

    monkeypatch.setattr(
        opening,
        "load_current_records_with_state",
        lambda *_args: (SimpleNamespace(state_revision=44), (presentation,)),
    )
    monkeypatch.setattr(
        opening,
        "verify_portfolio_presentation",
        lambda *_args, **_kwargs: SimpleNamespace(
            presentation_artifact_id="presentation_1"
        ),
    )
    opened: list[Path] = []
    monkeypatch.setattr(
        opening, "open_local_path", lambda path: opened.append(Path(path))
    )

    with pytest.raises(opening.PortfolioOutputOpenError) as caught:
        opening.open_student_portfolio_html(
            tmp_path, presentation_artifact_id="presentation_1"
        )

    assert caught.value.code == "portfolio_output.unsafe_target"
    assert opened == []


@pytest.mark.parametrize(
    "relative",
    (
        "http://example.test/portfolio.html",
        "https://example.test/portfolio.html",
        "file:///tmp/portfolio.html",
    ),
)
def test_url_targets_are_rejected_before_core_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative: str,
) -> None:
    opened: list[Path] = []
    monkeypatch.setattr(
        opening, "open_local_path", lambda path: opened.append(Path(path))
    )

    with pytest.raises(opening.PortfolioOutputOpenError) as caught:
        opening._resolve_vitrine_target(
            tmp_path,
            relative,
            target_kind="file",
        )

    assert caught.value.code == "portfolio_output.unsafe_target"
    assert opened == []


def test_wrong_target_kind_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    folder = tmp_path / "vitrine" / "folder"
    folder.mkdir(parents=True)
    opened: list[Path] = []
    monkeypatch.setattr(
        opening, "open_local_path", lambda path: opened.append(Path(path))
    )

    with pytest.raises(opening.PortfolioOutputOpenError):
        opening._resolve_vitrine_target(
            tmp_path,
            "folder",
            target_kind="file",
        )

    assert opened == []


def test_core_local_open_failure_is_wrapped_without_changing_custody(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_canonical(monkeypatch)
    _presentation_root, html, _pdf, _export_root = _make_targets(tmp_path)
    monkeypatch.setattr(
        opening,
        "verify_portfolio_presentation",
        lambda *_args, **_kwargs: SimpleNamespace(
            presentation_artifact_id="presentation_1"
        ),
    )

    before = html.read_bytes()

    def fail(_path: Path):
        raise LocalOpenError("synthetic viewer failure")

    monkeypatch.setattr(opening, "open_local_path", fail)

    with pytest.raises(opening.PortfolioOutputOpenError) as caught:
        opening.open_student_portfolio_html(
            tmp_path, presentation_artifact_id="presentation_1"
        )

    assert caught.value.code == "portfolio_output.local_open_failed"
    assert html.read_bytes() == before
