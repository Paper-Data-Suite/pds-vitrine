from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from pds_core.academic_catalog import PublicationCatalogQuery

from scripts.candidate_fixture_support import (
    ACTOR,
    DeterministicIds,
    StaticAuthorizationGate,
    build_candidate_fixture_workspace,
    fixed_clock,
)
from vitrine.candidate_evidence_presentation import (
    CANDIDATE_EVIDENCE_PRESENTATION_CONTRACT_VERSION,
    build_candidate_evidence_presentation,
)
from vitrine.candidate_inbox import (
    CandidateInboxQuery,
    get_candidate_inbox_detail,
    list_candidate_inbox,
)
from vitrine.candidate_services import (
    CandidateDiscoveryRequest,
    discover_and_evaluate_candidates,
)
from vitrine.development_adapters import (
    build_development_fixture_adapter_registry,
)
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)


def _discover(setup: object, module_id: str) -> None:
    result = discover_and_evaluate_candidates(
        getattr(setup, "workspace"),
        CandidateDiscoveryRequest(
            portfolio_id=getattr(setup, "portfolio_id"),
            requesting_actor=ACTOR,
            requested_purpose="improvement",
            catalog_query=PublicationCatalogQuery(
                module_id=module_id,
                state="current",
                limit=20,
            ),
            expected_state_revision=getattr(setup, "state_revision"),
        ),
        producer_registry=build_development_fixture_producer_registry(),
        adapter_registry=build_development_fixture_adapter_registry(),
        authorization_gate=StaticAuthorizationGate("allowed"),
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )
    assert result.findings == ()


def _details(setup: object, module_id: str):
    inbox = list_candidate_inbox(
        getattr(setup, "workspace"),
        CandidateInboxQuery(
            producer_module_id=module_id,
            limit=100,
        ),
    )
    return tuple(
        get_candidate_inbox_detail(
            getattr(setup, "workspace"),
            item.entry_id,
        )
        for item in inbox.items
    )


def test_scoreform_presentation_uses_work_title_and_attempt_number(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, "vitrine_scoreform_fixture")

    presentations = tuple(
        build_candidate_evidence_presentation(detail)
        for detail in _details(setup, "vitrine_scoreform_fixture")
    )

    assert tuple(item.primary_label for item in presentations) == (
        "Assessment Attempt — Synthetic argument_assessment — Attempt 1",
        "Assessment Attempt — Synthetic argument_assessment — Attempt 2",
    )
    assert all(
        item.contract_version
        == CANDIDATE_EVIDENCE_PRESENTATION_CONTRACT_VERSION
        for item in presentations
    )
    assert all(item.evidence_kind == "Assessment Attempt" for item in presentations)
    assert all(item.work_title == "Synthetic argument_assessment" for item in presentations)
    assert all(item.representation_label is None for item in presentations)
    assert all(
        tuple(role.label for role in item.profile_fit) == ("Assessment Context",)
        for item in presentations
    )
    assert all(
        "scoreform_fixture" not in item.primary_label for item in presentations
    )


def test_quillan_presentation_uses_instructional_evidence_vocabulary(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, "vitrine_quillan_fixture")

    presentations = tuple(
        build_candidate_evidence_presentation(detail)
        for detail in _details(setup, "vitrine_quillan_fixture")
    )

    labels = {item.primary_label for item in presentations}
    assert "Feedback — Synthetic literary_analysis (Markdown)" in labels
    assert "Student Work — Synthetic literary_analysis" in labels
    assert all("Artifact capability" not in item.primary_label for item in presentations)
    assert all(
        "vitrine_quillan_fixture" not in item.primary_label
        for item in presentations
    )

    feedback = next(item for item in presentations if item.evidence_kind == "Feedback")
    assert tuple(role.label for role in feedback.profile_fit) == ("Feedback Context",)


def test_concord_presentation_uses_collaborative_work_language(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, "vitrine_concord_fixture")

    presentations = tuple(
        build_candidate_evidence_presentation(detail)
        for detail in _details(setup, "vitrine_concord_fixture")
        if detail.item.candidate_id is not None
    )

    collaborative = next(
        item for item in presentations if item.evidence_kind == "Collaborative Work"
    )
    assert (
        collaborative.primary_label
        == "Collaborative Work — Synthetic water_quality_activity"
    )
    assert "concord_fixture" not in collaborative.primary_label
    assert "Documented Contribution" in tuple(
        role.label for role in collaborative.profile_fit
    )


def test_quillan_feedback_representations_share_family_without_merging_identity(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, "vitrine_quillan_fixture")
    feedback_detail = next(
        detail
        for detail in _details(setup, "vitrine_quillan_fixture")
        if detail.candidate is not None
        and detail.candidate.source_endpoint.source_artifact is not None
        and detail.candidate.source_endpoint.source_artifact.artifact_kind
        == "rendered_feedback"
    )
    assert feedback_detail.candidate is not None
    assert feedback_detail.evaluation is not None

    original_endpoint = feedback_detail.candidate.source_endpoint
    assert original_endpoint.source_artifact is not None
    lineage = original_endpoint.producer_source.lineage_reference
    assert lineage is not None

    pdf_endpoint = replace(
        original_endpoint,
        producer_source=replace(
            original_endpoint.producer_source,
            source_record_id="feedback_pdf_exact",
            native_disposition="feedback_pdf",
        ),
        source_artifact=replace(
            original_endpoint.source_artifact,
            artifact_id="feedback_pdf_artifact",
            representation_kind="quillan:feedback_pdf",
            media_type="application/pdf",
        ),
    )
    markdown_endpoint = replace(
        original_endpoint,
        producer_source=replace(
            original_endpoint.producer_source,
            source_record_id="feedback_markdown_exact",
            native_disposition="feedback_markdown",
        ),
        source_artifact=replace(
            original_endpoint.source_artifact,
            artifact_id="feedback_markdown_artifact",
            representation_kind="quillan:feedback_markdown",
            media_type="text/markdown; charset=utf-8",
        ),
    )

    pdf_detail = replace(
        feedback_detail,
        evaluation=replace(
            feedback_detail.evaluation,
            source_endpoint=pdf_endpoint,
        ),
        candidate=replace(
            feedback_detail.candidate,
            source_endpoint=pdf_endpoint,
        ),
    )
    markdown_detail = replace(
        feedback_detail,
        evaluation=replace(
            feedback_detail.evaluation,
            source_endpoint=markdown_endpoint,
        ),
        candidate=replace(
            feedback_detail.candidate,
            source_endpoint=markdown_endpoint,
        ),
    )

    pdf = build_candidate_evidence_presentation(pdf_detail)
    markdown = build_candidate_evidence_presentation(markdown_detail)

    assert pdf.primary_label == "Feedback — Synthetic literary_analysis (PDF)"
    assert (
        markdown.primary_label
        == "Feedback — Synthetic literary_analysis (Markdown)"
    )
    assert pdf.representation_family_key == f"quillan:feedback:{lineage}"
    assert markdown.representation_family_key == pdf.representation_family_key
    assert pdf.source_record_id != markdown.source_record_id
    assert pdf.source_artifact_id != markdown.source_artifact_id
    assert pdf.representation_kind == "quillan:feedback_pdf"
    assert markdown.representation_kind == "quillan:feedback_markdown"


def test_presentation_projection_is_read_only(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    _discover(setup, "vitrine_scoreform_fixture")
    detail = _details(setup, "vitrine_scoreform_fixture")[0]
    before = setup.state_revision

    first = build_candidate_evidence_presentation(detail)
    second = build_candidate_evidence_presentation(detail)

    assert first == second
    assert setup.state_revision == before
