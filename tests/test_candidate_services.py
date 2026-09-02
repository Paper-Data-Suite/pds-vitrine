from __future__ import annotations

import pytest
from pds_core.academic_catalog import PublicationCatalogQuery

from scripts.candidate_fixture_support import ACTOR
from vitrine.candidate_services import (
    CANDIDATE_KIND_BY_ARTIFACT_KIND,
    CandidateDiscoveryRequest,
    CandidateWorkflowError,
    SourceReadAuthorizationDecision,
)
from vitrine.development_candidate_fixtures import (
    build_development_fixture_producer_registry,
)
from vitrine.producer_adapters import build_adapter_registry


def test_candidate_kind_mapping_is_explicit() -> None:
    assert CANDIDATE_KIND_BY_ARTIFACT_KIND == {
        "assessment_summary": "assessment_summary",
        "collaborative_artifact": "student_work",
        "original_student_work": "student_work",
        "rendered_feedback": "feedback",
    }


def test_candidate_request_requires_bounded_catalog_query() -> None:
    with pytest.raises(CandidateWorkflowError) as caught:
        CandidateDiscoveryRequest(
            portfolio_id="portfolio_fixture",
            requesting_actor=ACTOR,
            requested_purpose="improvement",
            catalog_query=PublicationCatalogQuery(module_id="vitrine_scoreform_fixture"),
            expected_state_revision=1,
        )
    assert caught.value.code == "candidate.invalid_request"


def test_authorization_decision_is_explicit() -> None:
    assert SourceReadAuthorizationDecision(outcome="allowed").outcome == "allowed"
    assert SourceReadAuthorizationDecision(outcome="denied").outcome == "denied"
    assert SourceReadAuthorizationDecision(outcome="unresolved").outcome == "unresolved"
    with pytest.raises(CandidateWorkflowError):
        SourceReadAuthorizationDecision(outcome="implicit")


def test_fixture_profiles_are_explicit_and_not_live_producer_identities() -> None:
    registry = build_development_fixture_producer_registry()
    assert tuple(profile.module_id for profile in registry.profiles) == (
        "vitrine_concord_fixture",
        "vitrine_quillan_fixture",
        "vitrine_scoreform_fixture",
    )
    assert registry.get("scoreform") is None
    assert registry.get("quillan") is None
    assert registry.get("concord") is None

    ordinary = build_adapter_registry()
    assert tuple(
        adapter.declaration.adapter_id for adapter in ordinary.adapters
    ) == ("vitrine_scoreform_live_adapter",)
    assert (
        ordinary.adapters[0].declaration.support_key.producer_module_id
        == "scoreform"
    )
