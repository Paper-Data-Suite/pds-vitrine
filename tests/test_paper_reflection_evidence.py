from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pds_core.route_registrations import resolve_route_registration
from pds_core.scan_retention import retain_source_scan

from scripts.curation_fixture_support import (
    ACTOR,
    REFLECTION_REQUIREMENT_ID,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
    fixed_clock,
)
from vitrine.models import (
    CurationTargetRef,
    PortfolioReflection,
    ReflectionPromptIssuance,
    ReflectionResponsePage,
    ReflectionReturnedPaperEvidence,
    record_from_json_bytes,
    record_to_canonical_json_bytes,
)
from vitrine.paper_reflection_evidence import PaperReflectionRetainedSourceError
from vitrine.paper_reflection_printing import (
    persist_reflection_print_route_registrations,
    prepare_reflection_print_plan,
)
from vitrine.paper_reflection_route_handler import (
    handle_vitrine_reflection_response_page_route,
)
from vitrine.paper_reflection_services import prepare_reflection_issuance
from vitrine.storage import load_current_records, load_current_state

INTAKE = datetime(2026, 9, 25, 18, 0, tzinfo=timezone.utc)


def _routed_page(tmp_path: Path):
    setup = build_curation_fixture_workspace(tmp_path)
    issued = prepare_reflection_issuance(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="growth_compare",
        prompt_version="1",
        prompt_snapshot="Compare the curated works without assuming improvement.",
        target_scope="portfolio",
        target_references=(
            CurationTargetRef(
                target_kind="portfolio",
                target_id=setup.portfolio_id,
            ),
        ),
        issued_by=ACTOR,
        page_count=1,
        expected_state_revision=setup.state_revision,
        authority_gate=StaticCurationAuthorityGate(),
        clock=fixed_clock,
        id_factory=setup.ids,
    )
    issuance = next(
        item
        for item in issued.records
        if isinstance(item, ReflectionPromptIssuance)
    )
    page = next(
        item for item in issued.records if isinstance(item, ReflectionResponsePage)
    )
    plan = prepare_reflection_print_plan(
        setup.workspace,
        issuance_id=issuance.issuance_id,
        expected_state_revision=issued.state_revision,
    )
    persist_reflection_print_route_registrations(plan)
    resolution = resolve_route_registration(
        setup.workspace,
        plan.routes[0].locator,
    )
    return setup, issuance, page, resolution


def _retained(
    workspace: Path,
    source_dir: Path,
    *,
    content: bytes,
    timestamp: datetime,
):
    source_dir.mkdir(parents=True, exist_ok=True)
    source = source_dir / "student-reflection.png"
    source.write_bytes(content)
    return retain_source_scan(
        workspace,
        source,
        intake_timestamp=timestamp,
    )


def test_returned_paper_evidence_round_trips_exact_core_provenance(
    tmp_path: Path,
) -> None:
    setup, issuance, page, resolution = _routed_page(tmp_path)
    retained = _retained(
        setup.workspace,
        tmp_path / "incoming",
        content=b"original handwritten paper bytes",
        timestamp=INTAKE,
    )

    evidence = handle_vitrine_reflection_response_page_route(
        resolution,
        retained,
        1,
    )

    assert record_from_json_bytes(
        record_to_canonical_json_bytes(evidence)
    ) == evidence
    assert evidence.issuance_id == issuance.issuance_id
    assert evidence.response_page_id == page.response_page_id
    assert evidence.route_id == page.route_id
    assert evidence.class_id == page.class_id
    assert evidence.work_id == page.work_id
    assert evidence.source_scan_id == retained.source_scan_id
    assert evidence.source_page_number == 1
    assert evidence.retained_source_relative_path == (
        retained.retained_source_relative_path
    )
    assert evidence.source_sha256 == retained.source_sha256
    assert evidence.intake_timestamp == retained.intake_timestamp
    assert evidence.intake_date == retained.intake_date

    records = load_current_records(setup.workspace)
    assert evidence in records
    assert not any(isinstance(item, PortfolioReflection) for item in records)


def test_exact_dispatch_replay_is_idempotent_without_new_state_revision(
    tmp_path: Path,
) -> None:
    setup, _issuance, _page, resolution = _routed_page(tmp_path)
    retained = _retained(
        setup.workspace,
        tmp_path / "incoming",
        content=b"same retained source",
        timestamp=INTAKE,
    )

    first = handle_vitrine_reflection_response_page_route(
        resolution,
        retained,
        1,
    )
    after_first = load_current_state(setup.workspace).state_revision
    second = handle_vitrine_reflection_response_page_route(
        resolution,
        retained,
        1,
    )
    after_second = load_current_state(setup.workspace).state_revision

    assert second == first
    assert after_second == after_first
    evidences = tuple(
        item
        for item in load_current_records(setup.workspace)
        if isinstance(item, ReflectionReturnedPaperEvidence)
    )
    assert evidences == (first,)


def test_rescan_is_preserved_as_distinct_immutable_evidence(
    tmp_path: Path,
) -> None:
    setup, _issuance, _page, resolution = _routed_page(tmp_path)
    first_retained = _retained(
        setup.workspace,
        tmp_path / "incoming-a",
        content=b"first scan bytes",
        timestamp=INTAKE,
    )
    second_retained = _retained(
        setup.workspace,
        tmp_path / "incoming-b",
        content=b"second scan bytes",
        timestamp=INTAKE + timedelta(minutes=1),
    )

    first = handle_vitrine_reflection_response_page_route(
        resolution,
        first_retained,
        1,
    )
    second = handle_vitrine_reflection_response_page_route(
        resolution,
        second_retained,
        1,
    )

    assert first.returned_paper_evidence_id != (
        second.returned_paper_evidence_id
    )
    assert first.source_scan_id != second.source_scan_id
    evidences = tuple(
        item
        for item in load_current_records(setup.workspace)
        if isinstance(item, ReflectionReturnedPaperEvidence)
    )
    assert set(evidences) == {first, second}


def test_tampered_retained_bytes_are_rejected_before_evidence_mutation(
    tmp_path: Path,
) -> None:
    setup, _issuance, _page, resolution = _routed_page(tmp_path)
    retained = _retained(
        setup.workspace,
        tmp_path / "incoming",
        content=b"original scan bytes",
        timestamp=INTAKE,
    )
    before = load_current_state(setup.workspace).state_revision
    retained.retained_source_path.write_bytes(b"tampered after retention")

    with pytest.raises(
        PaperReflectionRetainedSourceError,
        match="SHA-256",
    ):
        handle_vitrine_reflection_response_page_route(
            resolution,
            retained,
            1,
        )

    assert load_current_state(setup.workspace).state_revision == before
    assert not any(
        isinstance(item, ReflectionReturnedPaperEvidence)
        for item in load_current_records(setup.workspace)
    )


def test_image_retained_source_rejects_nonexistent_second_source_page(
    tmp_path: Path,
) -> None:
    setup, _issuance, _page, resolution = _routed_page(tmp_path)
    retained = _retained(
        setup.workspace,
        tmp_path / "incoming",
        content=b"single image source",
        timestamp=INTAKE,
    )
    before = load_current_state(setup.workspace).state_revision

    with pytest.raises(
        PaperReflectionRetainedSourceError,
        match="only source page 1",
    ):
        handle_vitrine_reflection_response_page_route(
            resolution,
            retained,
            2,
        )

    assert load_current_state(setup.workspace).state_revision == before
