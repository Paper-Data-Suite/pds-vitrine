from __future__ import annotations

import hashlib
import re
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

import vitrine.paper_reflection_pdf as paper_pdf_module
from tests.test_paper_reflection_printing import _issued
from vitrine.current_portfolio_build import _reflection_target_path, _target_path
from vitrine.paper_reflection_materialization import (
    PaperReflectionMaterialization,
    read_paper_reflection_materialization_bytes,
)
from vitrine.paper_reflection_pdf import (
    PAPER_REFLECTION_PDF_FILENAME,
    render_persisted_reflection_pdf,
)
from vitrine.paper_reflection_printing import (
    persist_reflection_print_route_registrations,
    prepare_reflection_print_plan,
)


def _very_long_semantic_value() -> dict[str, object]:
    return {
        "candidate_id": "candidate_" + ("c" * 12_000),
        "placement_id": "placement_" + ("p" * 12_000),
        "selection_id": "selection_" + ("s" * 12_000),
        "artifact_id": "artifact_" + ("a" * 12_000),
        "source_locator": "source/" + ("nested-" * 2_000) + "student-work.pdf",
        "display_title": "Teacher display label " * 1_000,
    }


def test_current_portfolio_entry_path_does_not_scale_with_semantic_identity() -> None:
    target = _target_path(
        section_order=7,
        position_in_section=3,
        semantic_value=_very_long_semantic_value(),
        media_type="application/pdf",
    )
    assert re.fullmatch(r"section-07/03-entry-[0-9a-f]{16}\.pdf", target)
    assert "candidate_" not in target
    assert "Teacher" not in target


def test_current_portfolio_reflection_path_does_not_scale_with_semantic_identity() -> None:
    target = _reflection_target_path(
        section_order=12,
        position_in_section=8,
        semantic_value=_very_long_semantic_value(),
        media_type="text/plain",
    )
    assert re.fullmatch(r"section-12/08-reflection-[0-9a-f]{16}\.txt", target)
    assert "artifact_" not in target
    assert "student-work" not in target


def test_deep_windows_geometry_keeps_current_portfolio_leaf_bounded() -> None:
    workspace = PureWindowsPath(
        r"C:\Users\teacher\OneDrive - Hillside Public Schools"
    )
    for index in range(5):
        workspace /= f"2026-2027-portfolio-workspace-layer-{index:02d}"

    target = _target_path(
        section_order=4,
        position_in_section=11,
        semantic_value=_very_long_semantic_value(),
        media_type="application/pdf",
    )
    full = workspace / "vitrine" / "snapshots" / "content"
    for part in PurePosixPath(target).parts:
        full /= part

    assert len(str(workspace)) > 200
    assert len(full.name.encode("utf-8")) < 64
    assert "candidate_" not in str(full)
    assert full.name.endswith(".pdf")


def test_paper_reflection_render_keeps_fixed_leaf_and_bounded_temporary_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup, revision, issuance, _pages = _issued(tmp_path, pages=1)
    plan = prepare_reflection_print_plan(
        setup.workspace,
        issuance_id=issuance.issuance_id,
        expected_state_revision=revision,
    )
    persisted = persist_reflection_print_route_registrations(plan)
    destinations: list[Path] = []

    def fake_render(
        _plan: object,
        destination: Path,
        *,
        student_display_name: str | None,
    ) -> None:
        assert student_display_name is not None
        assert len(student_display_name) == 20_000
        destinations.append(destination)
        destination.write_bytes(b"%PDF-issue111-fixture\n")

    monkeypatch.setattr(paper_pdf_module, "_render_pdf", fake_render)

    output = render_persisted_reflection_pdf(
        persisted,
        student_display_name="S" * 20_000,
    )

    assert output.name == PAPER_REFLECTION_PDF_FILENAME
    assert len(destinations) == 1
    assert re.fullmatch(
        r"\.student_reflection_response\.[0-9a-f]{16}\.tmp\.pdf",
        destinations[0].name,
    )
    assert len(destinations[0].name.encode("utf-8")) < 64
    assert output.read_bytes() == b"%PDF-issue111-fixture\n"


def test_historical_core_retained_source_is_consumed_from_exact_persisted_path(
    tmp_path: Path,
) -> None:
    payload = b"%PDF-historical-core-retained-source\n"
    historical_leaf = (
        "source_scan_legacy_fixture__"
        + ("original-student-reflection-" * 3)
        + ".pdf"
    )
    relative = (
        PurePosixPath("scans")
        / "source"
        / "2026-09-26"
        / historical_leaf
    )
    source = tmp_path.joinpath(*relative.parts)
    source.parent.mkdir(parents=True)
    source.write_bytes(payload)

    materialization = PaperReflectionMaterialization(
        reflection_id="reflection_issue111",
        reflection_revision=1,
        paper_finalization_id="paper_finalization_issue111",
        returned_paper_evidence_id="returned_evidence_issue111",
        source_scan_id="source_scan_legacy_fixture",
        source_page_number=1,
        retained_source_relative_path=relative.as_posix(),
        source_sha256=hashlib.sha256(payload).hexdigest(),
        media_type="application/pdf",
    )

    assert read_paper_reflection_materialization_bytes(tmp_path, materialization) == payload
    assert source.is_file()
    assert source.name == historical_leaf
    assert materialization.retained_source_relative_path == relative.as_posix()
