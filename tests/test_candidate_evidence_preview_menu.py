from __future__ import annotations

import hashlib
import io
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from pds_core.academic_catalog import PublicationCatalogQuery

from scripts.candidate_fixture_support import (
    ACTOR,
    DeterministicIds,
    StaticAuthorizationGate,
    build_candidate_fixture_workspace,
    fixed_clock,
)
from vitrine import candidate_evidence_preview_menu
from vitrine.candidate_evidence_artifact_preview import (
    CANDIDATE_EVIDENCE_ARTIFACT_PREVIEW_CONTRACT_VERSION,
    CandidateEvidenceArtifactPreview,
)
from vitrine.candidate_evidence_preview_menu import run_candidate_evidence_preview
from vitrine.candidate_inbox import (
    CandidateInboxQuery,
    get_candidate_inbox_detail,
    list_candidate_inbox,
)
from vitrine.candidate_services import (
    CandidateDiscoveryRequest,
    discover_and_evaluate_candidates,
)
from vitrine.development_adapters import build_development_fixture_adapter_registry
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)
from vitrine.storage import load_current_state
from vitrine.workflow_context import default_workflow_dependencies


def _inputs(values: list[str]):
    iterator = iter(values)
    return lambda _prompt: next(iterator)


def _scoreform_detail(tmp_path: Path):
    setup = build_candidate_fixture_workspace(tmp_path)
    result = discover_and_evaluate_candidates(
        setup.workspace,
        CandidateDiscoveryRequest(
            portfolio_id=setup.portfolio_id,
            requesting_actor=ACTOR,
            requested_purpose="improvement",
            catalog_query=PublicationCatalogQuery(
                module_id="vitrine_scoreform_fixture",
                state="current",
                limit=20,
            ),
            expected_state_revision=setup.state_revision,
        ),
        producer_registry=build_development_fixture_producer_registry(),
        adapter_registry=build_development_fixture_adapter_registry(),
        authorization_gate=StaticAuthorizationGate("allowed"),
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )
    assert result.findings == ()
    item = list_candidate_inbox(
        setup.workspace,
        CandidateInboxQuery(
            portfolio_id=setup.portfolio_id,
            producer_module_id="vitrine_scoreform_fixture",
            limit=20,
        ),
    ).items[0]
    return setup, get_candidate_inbox_detail(setup.workspace, item.entry_id)


def test_structured_preview_is_explicit_read_only_and_teacher_facing(
    tmp_path: Path,
) -> None:
    setup, detail = _scoreform_detail(tmp_path)
    before = load_current_state(setup.workspace).state_revision
    dependencies = replace(
        default_workflow_dependencies(),
        adapter_registry=build_development_fixture_adapter_registry(),
        source_read_authorization_gate=StaticAuthorizationGate("allowed"),
    )
    output = io.StringIO()

    run_candidate_evidence_preview(
        workspace_root=setup.workspace,
        detail=detail,
        dependencies=dependencies,
        input_fn=_inputs([""]),
        output=output,
        clear_fn=lambda: None,
        actor=ACTOR,
    )

    rendered = output.getvalue()
    assert "Preparing evidence preview..." in rendered
    assert "Evidence Preview" in rendered
    assert "Synthetic argument_assessment" in rendered
    assert "Assessment Attempt" in rendered
    assert "Attempt:" in rendered
    assert "Points earned:" in rendered
    assert "Nothing was selected or placed" in rendered
    assert "manifest_digest" not in rendered
    assert load_current_state(setup.workspace).state_revision == before


def test_artifact_preview_file_exists_only_for_launch_lifetime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup, detail = _scoreform_detail(tmp_path)
    fake_result = SimpleNamespace(
        preview_kind="artifact_preview",
        structured_preview=None,
        unavailable_reason=None,
    )
    fake_context = SimpleNamespace(result=fake_result)
    monkeypatch.setattr(
        candidate_evidence_preview_menu,
        "prepare_candidate_evidence_preview_context",
        lambda *_args, **_kwargs: fake_context,
    )
    content = b"%PDF-1.4\npreview\n%%EOF\n"
    digest = hashlib.sha256(content).hexdigest()
    artifact = CandidateEvidenceArtifactPreview(
        contract_version=CANDIDATE_EVIDENCE_ARTIFACT_PREVIEW_CONTRACT_VERSION,
        source_publication_id="publication_alpha",
        source_artifact_id="artifact_alpha",
        producer_module_id="concord",
        artifact_kind="collaborative_artifact",
        representation_kind="concord:returned_artifact_pdf",
        media_type="application/pdf",
        sha256=digest,
        byte_size=len(content),
        content=content,
    )
    monkeypatch.setattr(
        candidate_evidence_preview_menu,
        "acquire_candidate_evidence_artifact_preview",
        lambda *_args, **_kwargs: artifact,
    )

    launched: list[Path] = []
    observed: list[bytes] = []

    def launcher(path: Path) -> bool:
        launched.append(path)
        assert path.exists()
        observed.append(path.read_bytes())
        assert path.suffix == ".pdf"
        return True

    output = io.StringIO()
    run_candidate_evidence_preview(
        workspace_root=setup.workspace,
        detail=detail,
        dependencies=default_workflow_dependencies(),
        input_fn=_inputs([""]),
        output=output,
        clear_fn=lambda: None,
        actor=ACTOR,
        launcher=launcher,
    )

    assert observed == [content]
    assert len(launched) == 1
    assert not launched[0].exists()
    assert "exact authorized evidence opened" in output.getvalue()


def test_inbox_opening_detail_does_not_trigger_preview(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from vitrine import candidate_inbox_menu

    setup, _detail = _scoreform_detail(tmp_path)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(setup.workspace))
    calls = 0

    def preview(**_kwargs: object) -> None:
        nonlocal calls
        calls += 1

    monkeypatch.setattr(candidate_inbox_menu, "run_candidate_evidence_preview", preview)
    candidate_inbox_menu.run_candidate_inbox_menu(
        input_fn=_inputs(["1", "", "b"]),
        output=io.StringIO(),
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
    )

    assert calls == 0


def test_inbox_v_action_invokes_explicit_preview(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from vitrine import candidate_inbox_menu

    setup, _detail = _scoreform_detail(tmp_path)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(setup.workspace))
    calls: list[str] = []

    def preview(**kwargs: object) -> None:
        detail = kwargs["detail"]
        calls.append(detail.item.entry_id)  # type: ignore[attr-defined]

    monkeypatch.setattr(candidate_inbox_menu, "run_candidate_evidence_preview", preview)
    candidate_inbox_menu.run_candidate_inbox_menu(
        input_fn=_inputs(["1", "v", "", "b"]),
        output=io.StringIO(),
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
    )

    assert len(calls) == 1


def test_guided_review_v_action_precedes_selection_decision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from vitrine import candidate_review_menu

    item = SimpleNamespace(
        entry_id="entry_exact",
        candidate_id="candidate_exact",
        current_evaluation_id="evaluation_exact",
        portfolio_id="portfolio_exact",
        portfolio_label="Portfolio",
        portfolio_subject_id="subject_exact",
        subject_label="Student",
        profile_binding_id="binding_exact",
        portfolio_profile_id="profile_exact",
        profile_revision=1,
        profile_label="Improvement",
        profile_purpose="improvement",
        source_display_label="Synthetic evidence",
        evaluation_outcome="eligible",
        candidate_condition="ready_for_consideration",
        stale_state="current",
        stale_reason_codes=(),
        attention_needed=False,
        attention_reason_codes=(),
        selected_state="unselected",
        eligible_section_ids=(),
    )
    inbox_detail = SimpleNamespace(
        item=item,
        observed_state_revision=11,
        profile_revision=SimpleNamespace(sections=()),
    )
    detail = SimpleNamespace(
        inbox_detail=inbox_detail,
        selectable=True,
        current_review_evaluation_id="evaluation_exact",
        curation_provenance_evaluation_id="evaluation_exact",
        current_evaluation_differs_from_curation_provenance=False,
        source=None,
        sections=(),
        proposals=(),
        selections=(),
        placements=(),
        annotations=(),
        reflections=(),
        reviews=(),
        profile_requirements=(),
    )
    monkeypatch.setattr(
        candidate_review_menu,
        "get_candidate_review_detail",
        lambda *_args, **_kwargs: detail,
    )
    preview_calls = 0

    def preview(**_kwargs: object) -> None:
        nonlocal preview_calls
        preview_calls += 1

    monkeypatch.setattr(candidate_review_menu, "run_candidate_evidence_preview", preview)
    candidate_review_menu._review_entry(
        root=tmp_path,
        entry_id="entry_exact",
        input_fn=_inputs(["v", "b"]),
        output=io.StringIO(),
        clear_fn=lambda: None,
        dependencies=default_workflow_dependencies(),
        actor=ACTOR,
    )

    assert preview_calls == 1
