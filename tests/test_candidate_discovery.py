from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from pds_core.academic_catalog import PublicationCatalogQuery, rebuild_academic_catalog
from pds_core.academic_work_registration_storage import (
    load_academic_work_registration_revision,
)
from pds_core.publication_compatibility import (
    PublicationContractSupport,
    PublicationProducerProfile,
    PublicationProducerRegistry,
)
from pds_core.registry_paths import academic_catalog_path
from pds_core.registry_services import (
    AcademicWorkRegistrationRequest,
    PublicationManifestRequest,
    PublicationWithdrawalRequest,
    get_canonical_publication_record,
    supersede_manifest_revision,
    update_academic_work_registration,
    withdraw_publication,
)

import vitrine.candidate_services as candidate_services
from scripts.candidate_fixture_support import (
    ACTOR,
    DeterministicIds,
    StaticAuthorizationGate,
    build_candidate_fixture_workspace,
    fixed_clock,
)
from vitrine.candidate_services import (
    CandidateDiscoveryRequest,
    CandidateWorkflowError,
    discover_and_evaluate_candidates,
)
from vitrine.development_adapters import build_development_fixture_adapter_registry
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)
from vitrine.models import CandidateEvaluation, PortfolioCandidate, PortfolioSelection
from vitrine.producer_adapters import (
    ProducerProjectionAdapterRegistry,
    build_adapter_registry,
)
from vitrine.storage import (
    VitrineStorageConflictError,
    load_current_records,
    load_current_state,
)


def _request(setup: object, module_id: str) -> CandidateDiscoveryRequest:
    return CandidateDiscoveryRequest(
        portfolio_id=getattr(setup, "portfolio_id"),
        requesting_actor=ACTOR,
        requested_purpose="improvement",
        catalog_query=PublicationCatalogQuery(module_id=module_id, state="current", limit=20),
        expected_state_revision=getattr(setup, "state_revision"),
    )


def _run(setup: object, module_id: str, *, gate: StaticAuthorizationGate | None = None):
    return discover_and_evaluate_candidates(
        getattr(setup, "workspace"),
        _request(setup, module_id),
        producer_registry=build_development_fixture_producer_registry(),
        adapter_registry=build_development_fixture_adapter_registry(),
        authorization_gate=gate or StaticAuthorizationGate("allowed"),
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )


def _field_map(result: object) -> dict[str, object]:
    source = getattr(result, "projected_source")
    return {field.key: field.value for field in source.display_snapshot.fields}


def test_scoreform_discovery_preserves_attempt_and_response_state(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    result = _run(setup, "vitrine_scoreform_fixture")
    assert result.findings == ()
    assert len(result.evaluation_results) == 2
    assert all(item.candidate is not None for item in result.evaluation_results)
    assert [item.projected_source.producer_source.native_revision for item in result.evaluation_results] == [1, 2]

    first = _field_map(result.evaluation_results[0])
    second = _field_map(result.evaluation_results[1])
    assert first["attempt_origin"] == "pds2_scan"
    assert first["response_states"] == ("1:selected", "2:blank", "3:ambiguous")
    assert second["attempt_origin"] == "scan_review_manual"
    assert second["response_states"] == ("1:selected", "2:selected", "3:selected")
    assert first["standard_alignments"] == (
        "1:RL.CR.9-10.1",
        "2:RL.CI.9-10.2",
        "3:RL.IT.9-10.3",
    )
    assert first["points_earned"] == 7
    assert second["points_earned"] == 9

    rendered = repr(result.evaluation_results)
    for prohibited in (
        "PRIVATE_ANSWER_KEY",
        "PRIVATE_DETECTOR",
        "PRIVATE_ROUTE",
        "PRIVATE_SCAN_REVIEW_NOTE",
        "proficiency",
        "mastery",
        "Grade",
        "official",
    ):
        assert prohibited not in rendered

    records = load_current_records(setup.workspace)
    assert len([item for item in records if isinstance(item, CandidateEvaluation)]) == 2
    assert len([item for item in records if isinstance(item, PortfolioCandidate)]) == 2
    assert not any(isinstance(item, PortfolioSelection) for item in records)


def test_historical_registration_revision_remains_publication_authority(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    publication = get_canonical_publication_record(
        setup.workspace, setup.scoreform_publication_id
    )
    assert publication.academic_work_registration_revision == 1
    original = load_academic_work_registration_revision(
        setup.workspace, publication.work, 1
    )
    updated = update_academic_work_registration(
        setup.workspace,
        AcademicWorkRegistrationRequest(
            work=original.work,
            producer_contract_version="vitrine_fixture_scoreform_academic_work_v2",
            title=f"{original.title} updated",
            work_kind=original.work_kind,
            academic_intent=original.academic_intent,
            lifecycle=original.lifecycle,
            source_records=original.source_records,
        ),
        expected_current_revision=1,
    ).registration
    assert updated.registration_revision == 2
    assert updated.producer_contract_version.endswith("_v2")
    rebuild_academic_catalog(setup.workspace)

    result = _run(setup, "vitrine_scoreform_fixture")
    assert result.findings == ()
    assert len(result.evaluation_results) == 2
    for item in result.evaluation_results:
        endpoint = item.evaluation.source_endpoint
        assert endpoint is not None
        snapshot = endpoint.core_publication.registration_snapshot
        assert snapshot is not None
        assert snapshot.registration_revision == 1
        assert (
            snapshot.producer_contract_version
            == "vitrine_fixture_scoreform_academic_work_v1"
        )
        assert (
            item.projected_source.producer_source.producer_contract_version
            == "vitrine_fixture_scoreform_academic_work_v1"
        )


def test_profile_ineligible_source_persists_evaluation_without_candidate(
    tmp_path: Path,
) -> None:
    setup = build_candidate_fixture_workspace(
        tmp_path, allow_assessment_summary=False
    )
    result = _run(setup, "vitrine_scoreform_fixture")
    assert result.findings == ()
    assert len(result.evaluation_results) == 2
    assert all(item.evaluation.outcome == "ineligible" for item in result.evaluation_results)
    assert all(item.candidate is None for item in result.evaluation_results)
    assert all(
        item.evaluation.eligible_section_ids == ()
        for item in result.evaluation_results
    )
    records = load_current_records(setup.workspace)
    evaluations = tuple(item for item in records if isinstance(item, CandidateEvaluation))
    candidates = tuple(item for item in records if isinstance(item, PortfolioCandidate))
    assert len(evaluations) == 2
    assert candidates == ()


def test_quillan_discovery_projects_only_approved_work_and_student_feedback(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    result = _run(setup, "vitrine_quillan_fixture")
    assert result.findings == ()
    assert len(result.evaluation_results) == 3
    ids = tuple(item.projected_source.producer_source.source_record_id for item in result.evaluation_results)
    assert ids == ("feedback_student", "evidence_approved", "evidence_selected")
    assert all(item.candidate is not None for item in result.evaluation_results)
    rendered = repr(result.evaluation_results)
    assert "evidence_candidate" not in rendered
    assert "evidence_duplicate" not in rendered
    assert "evidence_excluded" not in rendered
    assert "evidence_replacement" not in rendered
    assert "feedback_private" not in rendered
    assert "PRIVATE_TEACHER_NOTE" not in rendered
    assert "PRIVATE_FEEDBACK_SUMMARY" not in rendered
    assert "private/quillan" not in rendered


def test_concord_preserves_membership_authorship_contribution_and_group_score(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    result = _run(setup, "vitrine_concord_fixture")
    assert result.findings == ()
    assert len(result.evaluation_results) == 3
    artifact = next(
        item
        for item in result.evaluation_results
        if item.projected_source.projection_kind == "concord_fixture:artifact"
    )
    assert artifact.candidate is not None
    assert artifact.evaluation.outcome == "conditionally_eligible"
    assert artifact.candidate.condition_state == "collaborator_review_required"
    assert "contribution_work" in artifact.candidate.eligible_section_ids
    assert "authored_work" not in artifact.candidate.eligible_section_ids
    endpoint = artifact.evaluation.source_endpoint
    assert endpoint is not None
    relationship_kinds = {
        item.relationship_kind for item in endpoint.subject_relationship_assertions
    }
    assert {"group_member", "artifact_subject", "documented_contributor"} <= relationship_kinds
    assert "artifact_author" not in relationship_kinds

    score_results = tuple(
        item
        for item in result.evaluation_results
        if item.projected_source.projection_kind == "concord_fixture:score_summary"
    )
    assert len(score_results) == 2
    assert all(item.candidate is None for item in score_results)
    assert all(item.evaluation.outcome == "unresolved" for item in score_results)
    for item in score_results:
        fields = _field_map(item)
        assert fields["target_kind"] == "concord_group"
        assert item.projected_source.source_relationships[0].relationship_kind == "group_score_target"
        assert item.projected_source.source_relationships[0].relationship_kind != "individual_score_target"
    deferred = next(item for item in score_results if _field_map(item)["disposition"] == "deferred")
    assert "native_value" not in _field_map(deferred)


def test_authorization_denied_prevents_manifest_byte_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    calls = 0

    def forbidden_read(*_args: object, **_kwargs: object) -> bytes:
        nonlocal calls
        calls += 1
        raise AssertionError("manifest bytes must not be read")

    monkeypatch.setattr(candidate_services, "_read_verified_manifest_bytes", forbidden_read)
    gate = StaticAuthorizationGate("denied")
    result = _run(setup, "vitrine_scoreform_fixture", gate=gate)
    assert calls == 0
    assert len(gate.requests) == 1
    assert result.evaluation_results == ()
    assert tuple(item.code for item in result.findings) == ("candidate.authorization_denied",)


def test_authorization_unresolved_prevents_manifest_byte_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    calls = 0

    def forbidden_read(*_args: object, **_kwargs: object) -> bytes:
        nonlocal calls
        calls += 1
        raise AssertionError("manifest bytes must not be read")

    monkeypatch.setattr(candidate_services, "_read_verified_manifest_bytes", forbidden_read)
    result = _run(setup, "vitrine_scoreform_fixture", gate=StaticAuthorizationGate("unresolved"))
    assert calls == 0
    assert result.evaluation_results == ()
    assert tuple(item.code for item in result.findings) == ("candidate.authorization_unresolved",)


def test_digest_mismatch_fails_before_reader_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    setup.manifest_paths["vitrine_scoreform_fixture"].write_bytes(b"{}\n")
    calls = 0

    def forbidden_project(*_args: object, **_kwargs: object) -> tuple[object, ...]:
        nonlocal calls
        calls += 1
        raise AssertionError("producer projection must not run after digest failure")

    monkeypatch.setattr(candidate_services, "_project", forbidden_project)
    result = _run(setup, "vitrine_scoreform_fixture")
    assert calls == 0
    assert result.evaluation_results == ()
    assert tuple(item.code for item in result.findings) == (
        "candidate.manifest_integrity_failed",
    )


def test_missing_manifest_fails_before_reader_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    setup.manifest_paths["vitrine_scoreform_fixture"].unlink()
    calls = 0

    def forbidden_project(*_args: object, **_kwargs: object) -> tuple[object, ...]:
        nonlocal calls
        calls += 1
        raise AssertionError("producer projection must not run without a manifest")

    monkeypatch.setattr(candidate_services, "_project", forbidden_project)
    result = _run(setup, "vitrine_scoreform_fixture")
    assert calls == 0
    assert result.evaluation_results == ()
    assert tuple(item.code for item in result.findings) == ("candidate.manifest_missing",)


def test_missing_catalog_is_structured_and_not_rebuilt(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    path = academic_catalog_path(setup.workspace)
    path.unlink()
    result = _run(setup, "vitrine_scoreform_fixture")
    assert result.evaluation_results == ()
    assert tuple(item.code for item in result.findings) == ("candidate.catalog_unavailable",)
    assert not path.exists()


def test_missing_producer_profile_and_ordinary_adapter_fail_closed(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    request = _request(setup, "vitrine_scoreform_fixture")
    missing_profile = discover_and_evaluate_candidates(
        setup.workspace,
        request,
        producer_registry=PublicationProducerRegistry(profiles=()),
        adapter_registry=build_development_fixture_adapter_registry(),
        authorization_gate=StaticAuthorizationGate("allowed"),
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )
    assert tuple(item.code for item in missing_profile.findings) == (
        "candidate.producer_profile_missing",
    )

    ordinary_adapter = discover_and_evaluate_candidates(
        setup.workspace,
        request,
        producer_registry=build_development_fixture_producer_registry(),
        adapter_registry=build_adapter_registry(),
        authorization_gate=StaticAuthorizationGate("allowed"),
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )
    assert tuple(item.code for item in ordinary_adapter.findings) == (
        "candidate.adapter_unsupported",
    )


def test_incompatible_producer_profile_fails_closed(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    profile = PublicationProducerProfile(
        module_id="vitrine_scoreform_fixture",
        display_name="Intentionally incompatible fixture profile",
        supported_core_publication_schema_versions=frozenset({"1"}),
        supported_academic_work_contract_versions=frozenset(
            {"vitrine_fixture_scoreform_academic_work_v1"}
        ),
        publication_contracts=(
            PublicationContractSupport(
                publication_kind="academic_result_set",
                manifest_contract_versions=frozenset(
                    {"vitrine_fixture_scoreform_manifest_v1"}
                ),
                supported_capabilities=frozenset({"points"}),
                source_record_contracts=(),
                allows_missing_source_record=True,
            ),
        ),
    )
    result = discover_and_evaluate_candidates(
        setup.workspace,
        _request(setup, "vitrine_scoreform_fixture"),
        producer_registry=PublicationProducerRegistry(profiles=(profile,)),
        adapter_registry=build_development_fixture_adapter_registry(),
        authorization_gate=StaticAuthorizationGate("allowed"),
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )
    assert result.evaluation_results == ()
    assert tuple(item.code for item in result.findings) == (
        "candidate.producer_incompatible",
    )
    assert "contracts.capability_incompatible" in result.findings[0].diagnostic_codes


def test_conflicting_vitrine_adapters_fail_closed(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    fixtures = build_development_fixture_adapter_registry()
    original = next(
        item
        for item in fixtures.adapters
        if item.declaration.adapter_id == "vitrine_scoreform_fixture_adapter"
    )

    class ConflictingAdapter:
        @property
        def declaration(self):
            return replace(
                original.declaration,
                adapter_id="vitrine_scoreform_fixture_adapter_conflict",
            )

        @property
        def reader(self):
            return original.reader

        def project(self, public_model: object):
            return original.project(public_model)

    conflict_registry = ProducerProjectionAdapterRegistry(
        adapters=(*fixtures.adapters, ConflictingAdapter())
    )
    result = discover_and_evaluate_candidates(
        setup.workspace,
        _request(setup, "vitrine_scoreform_fixture"),
        producer_registry=build_development_fixture_producer_registry(),
        adapter_registry=conflict_registry,
        authorization_gate=StaticAuthorizationGate("allowed"),
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )
    assert result.evaluation_results == ()
    assert tuple(item.code for item in result.findings) == ("candidate.adapter_conflict",)


def test_unlinked_exact_student_creates_unresolved_evaluations_not_candidates(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path, link_student=False)
    result = _run(setup, "vitrine_scoreform_fixture")
    assert result.findings == ()
    assert len(result.evaluation_results) == 2
    assert all(item.evaluation.outcome == "unresolved" for item in result.evaluation_results)
    assert all(item.candidate is None for item in result.evaluation_results)


def test_stale_vitrine_state_revision_is_rejected_before_discovery(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    request = replace(
        _request(setup, "vitrine_scoreform_fixture"),
        expected_state_revision=setup.state_revision + 1,
    )
    with pytest.raises(CandidateWorkflowError) as caught:
        discover_and_evaluate_candidates(
            setup.workspace,
            request,
            producer_registry=build_development_fixture_producer_registry(),
            adapter_registry=build_development_fixture_adapter_registry(),
            authorization_gate=StaticAuthorizationGate("allowed"),
            clock=fixed_clock,
            id_factory=DeterministicIds(),
        )
    assert caught.value.code == "candidate.state_conflict"


def test_commit_conflict_preserves_guarded_persistence_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)

    def conflict(*_args: object, **_kwargs: object) -> None:
        raise VitrineStorageConflictError("synthetic state conflict")

    monkeypatch.setattr(candidate_services, "commit_record_batch", conflict)
    with pytest.raises(CandidateWorkflowError) as caught:
        _run(setup, "vitrine_scoreform_fixture")
    assert caught.value.code == "candidate.state_conflict"


def test_exact_positive_replay_reuses_existing_candidates(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    first = _run(setup, "vitrine_scoreform_fixture")
    assert len(first.evaluation_results) == 2
    after_first = load_current_state(setup.workspace).state_revision
    second_request = CandidateDiscoveryRequest(
        portfolio_id=setup.portfolio_id,
        requesting_actor=ACTOR,
        requested_purpose="improvement",
        catalog_query=PublicationCatalogQuery(
            module_id="vitrine_scoreform_fixture", state="current", limit=20
        ),
        expected_state_revision=after_first,
    )
    second = discover_and_evaluate_candidates(
        setup.workspace,
        second_request,
        producer_registry=build_development_fixture_producer_registry(),
        adapter_registry=build_development_fixture_adapter_registry(),
        authorization_gate=StaticAuthorizationGate("allowed"),
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )
    assert tuple(item.disposition for item in second.evaluation_results) == (
        "existing",
        "existing",
    )
    assert second.committed_state_revision is None
    assert load_current_state(setup.workspace).state_revision == after_first


def test_same_student_id_in_another_class_does_not_resolve(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(
        tmp_path, link_student=True, link_class_id="english10_p3"
    )
    result = _run(setup, "vitrine_scoreform_fixture")
    assert result.findings == ()
    assert all(item.evaluation.outcome == "unresolved" for item in result.evaluation_results)
    assert all(item.candidate is None for item in result.evaluation_results)


def test_conflicting_subject_links_fail_source_resolution_closed(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path, conflicting_student_link=True)
    result = _run(setup, "vitrine_scoreform_fixture")
    assert result.findings == ()
    assert all(item.evaluation.outcome == "unresolved" for item in result.evaluation_results)
    assert all(
        "candidate:subject_conflict" in item.evaluation.reason_codes
        for item in result.evaluation_results
    )
    assert all(item.candidate is None for item in result.evaluation_results)


def test_withdrawn_series_head_cannot_create_new_candidate(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    withdraw_publication(
        setup.workspace,
        PublicationWithdrawalRequest(
            publication_id=setup.scoreform_publication_id,
            reason="Synthetic withdrawal for Candidate validation.",
        ),
    )
    rebuild_academic_catalog(setup.workspace)
    request = CandidateDiscoveryRequest(
        portfolio_id=setup.portfolio_id,
        requesting_actor=ACTOR,
        requested_purpose="improvement",
        catalog_query=PublicationCatalogQuery(
            module_id="vitrine_scoreform_fixture", state="series_heads", limit=20
        ),
        expected_state_revision=setup.state_revision,
    )
    result = discover_and_evaluate_candidates(
        setup.workspace,
        request,
        producer_registry=build_development_fixture_producer_registry(),
        adapter_registry=build_development_fixture_adapter_registry(),
        authorization_gate=StaticAuthorizationGate("allowed"),
        clock=fixed_clock,
        id_factory=DeterministicIds(),
    )
    assert result.evaluation_results == ()
    assert tuple(item.code for item in result.findings) == (
        "candidate.publication_not_selectable",
    )


def test_canonically_published_malformed_manifest_fails_in_exact_reader(tmp_path: Path) -> None:
    setup = build_candidate_fixture_workspace(tmp_path)
    previous = get_canonical_publication_record(
        setup.workspace, setup.scoreform_publication_id
    )
    malformed = setup.manifest_paths["vitrine_scoreform_fixture"].with_name("2.json")
    malformed.write_bytes(b"{}\n")
    supersede_manifest_revision(
        setup.workspace,
        PublicationManifestRequest(
            work=previous.work,
            source_record=previous.source_record,
            publication_kind=previous.publication_kind,
            capabilities=previous.capabilities,
            record_set_id=previous.record_set_id,
            record_set_revision=2,
            manifest_contract_version=previous.manifest_contract_version,
            manifest_path=malformed.relative_to(setup.workspace).as_posix(),
            academic_work_registration_revision=(
                previous.academic_work_registration_revision
            ),
        ),
        expected_current_publication_id=previous.publication_id,
    )
    rebuild_academic_catalog(setup.workspace)
    result = _run(setup, "vitrine_scoreform_fixture")
    assert result.evaluation_results == ()
    assert tuple(item.code for item in result.findings) == (
        "candidate.reader_failed",
    )
