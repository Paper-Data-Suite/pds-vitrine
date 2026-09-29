from __future__ import annotations

import hashlib
import io
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

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
from vitrine.paper_reflection_menu import run_paper_reflection_menu
from vitrine.paper_reflection_services import prepare_reflection_issuance
from vitrine.paper_reflection_workflow import build_paper_reflection_workflow_view
from vitrine.storage import commit_record_batch
from vitrine.workflow_context import default_workflow_dependencies

INTAKE = datetime(2026, 9, 26, 15, 0, tzinfo=timezone.utc)


def _inputs(values: list[str]):
    iterator = iter(values)
    return lambda _prompt: next(iterator)


def test_returned_paper_menu_previews_confirms_and_finalizes_student_author(
    tmp_path: Path,
) -> None:
    setup = build_curation_fixture_workspace(tmp_path)
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
        item
        for item in issued.records
        if isinstance(item, ReflectionResponsePage)
    )
    payload = b"returned student handwriting"
    relative = "scans/source/2026-09-26/reflection-menu.png"
    source = setup.workspace.joinpath(*relative.split("/"))
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(payload)
    evidence = ReflectionReturnedPaperEvidence(
        returned_paper_evidence_id="paper_evidence_menu_review",
        issuance_id=issuance.issuance_id,
        response_page_id=page.response_page_id,
        route_id=page.route_id,
        class_id=page.class_id,
        work_id=page.work_id,
        source_scan_id="scan_menu_review",
        source_filename="reflection-menu.png",
        source_page_number=1,
        retained_source_relative_path=relative,
        source_sha256=hashlib.sha256(payload).hexdigest(),
        intake_timestamp=INTAKE,
        intake_date=INTAKE.date(),
    )
    commit_record_batch(
        setup.workspace,
        (evidence,),
        expected_state_revision=issued.state_revision,
    )

    dependencies = replace(
        default_workflow_dependencies(),
        curation_authority_gate=StaticCurationAuthorityGate(),
    )
    opened: list[bytes] = []

    def launcher(path: Path) -> bool:
        opened.append(path.read_bytes())
        return True

    output = io.StringIO()
    run_paper_reflection_menu(
        portfolio_id=setup.portfolio_id,
        input_fn=_inputs(
            [
                "3",
                "",
                "CONFIRM STUDENT AUTHOR",
                "",
                "B",
            ]
        ),
        output=output,
        clear_fn=lambda: None,
        dependencies=dependencies,
        workspace_root=setup.workspace,
        actor=ACTOR,
        launcher=launcher,
    )

    assert opened == [payload]
    rendered = output.getvalue()
    assert "Review returned paper / confirm student author" in rendered
    assert "you are recording the association, not as the author" not in rendered
    assert "not as the author" in rendered
    assert "Student Reflection recorded." in rendered
    assert "Original returned paper evidence remains preserved." in rendered

    view = build_paper_reflection_workflow_view(
        setup.workspace,
        setup.portfolio_id,
    )
    item = view.requirements[0]
    assert item.status == "recorded"
    assert item.reflection_id is not None
    assert item.paper_finalization_id is not None
