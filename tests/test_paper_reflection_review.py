from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts.curation_fixture_support import (
    ACTOR,
    REFLECTION_REQUIREMENT_ID,
    StaticCurationAuthorityGate,
    build_curation_fixture_workspace,
    fixed_clock,
)
from vitrine.models import (
    CurationTargetRef,
    ReflectionPromptIssuance,
    ReflectionResponsePage,
    ReflectionReturnedPaperEvidence,
)
from vitrine.paper_reflection_review import (
    PaperReflectionReviewError,
    acquire_paper_reflection_evidence_preview,
    prepare_paper_reflection_review_context,
    selected_occurrence_ids,
)
from vitrine.paper_reflection_services import prepare_reflection_issuance
from vitrine.storage import commit_record_batch

BASE = datetime(2026, 9, 26, 14, 0, tzinfo=timezone.utc)


def _issue(setup, *, page_count: int):
    issued = prepare_reflection_issuance(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        reflection_requirement_id=REFLECTION_REQUIREMENT_ID,
        prompt_id="growth_compare",
        prompt_version="1",
        prompt_snapshot="Compare the curated Portfolio evidence.",
        issued_by=ACTOR,
        target_scope="portfolio",
        target_references=(
            CurationTargetRef(
                target_kind="portfolio",
                target_id=setup.portfolio_id,
            ),
        ),
        page_count=page_count,
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
    pages = tuple(
        item
        for item in issued.records
        if isinstance(item, ReflectionResponsePage)
    )
    return issued, issuance, pages


def _evidence(
    setup,
    *,
    issuance: ReflectionPromptIssuance,
    page: ReflectionResponsePage,
    suffix: str,
    payload: bytes,
    minute: int,
) -> ReflectionReturnedPaperEvidence:
    relative = f"scans/source/2026-09-26/{suffix}.png"
    path = setup.workspace.joinpath(*relative.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return ReflectionReturnedPaperEvidence(
        returned_paper_evidence_id=f"paper_evidence_{suffix}",
        issuance_id=issuance.issuance_id,
        response_page_id=page.response_page_id,
        route_id=page.route_id,
        class_id=page.class_id,
        work_id=page.work_id,
        source_scan_id=f"scan_{suffix}",
        source_filename=f"{suffix}.png",
        source_page_number=1,
        retained_source_relative_path=relative,
        source_sha256=hashlib.sha256(payload).hexdigest(),
        intake_timestamp=BASE + timedelta(minutes=minute),
        intake_date=BASE.date(),
    )


def test_review_context_preserves_page_order_and_all_rescans(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    issued, issuance, pages = _issue(setup, page_count=2)
    first_old = _evidence(
        setup,
        issuance=issuance,
        page=pages[0],
        suffix="page1_old",
        payload=b"page one old scan",
        minute=1,
    )
    first_new = _evidence(
        setup,
        issuance=issuance,
        page=pages[0],
        suffix="page1_new",
        payload=b"page one new scan",
        minute=2,
    )
    second = _evidence(
        setup,
        issuance=issuance,
        page=pages[1],
        suffix="page2",
        payload=b"page two scan",
        minute=3,
    )
    returned = commit_record_batch(
        setup.workspace,
        (first_old, first_new, second),
        expected_state_revision=issued.state_revision,
    )

    context = prepare_paper_reflection_review_context(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        issuance_id=issuance.issuance_id,
        expected_state_revision=returned.state_revision,
    )

    assert tuple(page.logical_page_number for page in context.pages) == (1, 2)
    assert tuple(
        item.returned_paper_evidence_id
        for item in context.pages[0].occurrences
    ) == (
        first_old.returned_paper_evidence_id,
        first_new.returned_paper_evidence_id,
    )
    assert tuple(
        item.returned_paper_evidence_id
        for item in context.pages[1].occurrences
    ) == (second.returned_paper_evidence_id,)

    chosen = selected_occurrence_ids(
        context,
        (
            first_new.returned_paper_evidence_id,
            second.returned_paper_evidence_id,
        ),
    )
    assert chosen == (
        first_new.returned_paper_evidence_id,
        second.returned_paper_evidence_id,
    )

    with pytest.raises(PaperReflectionReviewError):
        selected_occurrence_ids(
            context,
            (
                second.returned_paper_evidence_id,
                first_new.returned_paper_evidence_id,
            ),
        )


def test_review_preview_uses_digest_verified_retained_bytes(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
    issued, issuance, pages = _issue(setup, page_count=1)
    evidence = _evidence(
        setup,
        issuance=issuance,
        page=pages[0],
        suffix="page1",
        payload=b"exact returned handwritten bytes",
        minute=1,
    )
    returned = commit_record_batch(
        setup.workspace,
        (evidence,),
        expected_state_revision=issued.state_revision,
    )
    context = prepare_paper_reflection_review_context(
        setup.workspace,
        portfolio_id=setup.portfolio_id,
        issuance_id=issuance.issuance_id,
        expected_state_revision=returned.state_revision,
    )

    preview = acquire_paper_reflection_evidence_preview(
        context,
        evidence.returned_paper_evidence_id,
    )
    assert preview.content == b"exact returned handwritten bytes"
    assert preview.suffix == ".png"

    source = setup.workspace.joinpath(
        *evidence.retained_source_relative_path.split("/")
    )
    source.write_bytes(b"tampered after review projection")
    with pytest.raises(PaperReflectionReviewError):
        acquire_paper_reflection_evidence_preview(
            context,
            evidence.returned_paper_evidence_id,
        )
