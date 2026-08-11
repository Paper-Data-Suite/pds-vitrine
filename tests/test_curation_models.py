from __future__ import annotations

from datetime import datetime, timezone

import pytest

from vitrine.models import (
    ActorAttribution,
    CurationTargetRef,
    PortfolioReflection,
    ProfileRevisionRef,
    SelectionDecision,
    SelectionProposal,
    record_from_json_bytes,
    record_to_canonical_json_bytes,
)
from vitrine.models.errors import VitrineModelValidationError

NOW = datetime(2026, 8, 10, 20, 0, tzinfo=timezone.utc)
ACTOR = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="teacher_fixture",
    owning_system="vitrine",
    role_snapshot="teacher",
)
PROFILE = ProfileRevisionRef(
    portfolio_profile_id="profile_fixture",
    profile_revision=1,
)


def test_selection_proposal_exact_json_round_trip() -> None:
    proposal = SelectionProposal(
        selection_proposal_id="proposal_fixture",
        portfolio_id="portfolio_fixture",
        portfolio_subject_id="subject_fixture",
        profile_binding_id="binding_fixture",
        profile_revision=PROFILE,
        candidate_id="candidate_fixture",
        candidate_evaluation_id="evaluation_fixture",
        proposer=ACTOR,
        proposal_origin="teacher",
        proposed_section_ids=("section_fixture",),
        intended_profile_requirement_ids=("requirement_fixture",),
        candidate_condition_state_snapshot="ready_for_consideration",
        proposed_at=NOW,
    )
    payload = record_to_canonical_json_bytes(proposal)
    assert record_from_json_bytes(payload) == proposal
    assert record_to_canonical_json_bytes(record_from_json_bytes(payload)) == payload


def test_reflection_preserves_prompt_and_ordered_comparison_roles() -> None:
    reflection = PortfolioReflection(
        reflection_id="reflection_fixture",
        reflection_revision=1,
        portfolio_id="portfolio_fixture",
        portfolio_subject_id="subject_fixture",
        profile_binding_id="binding_fixture",
        profile_revision=PROFILE,
        reflection_requirement_id="reflection_requirement_fixture",
        prompt_id="prompt_fixture",
        prompt_version="1",
        prompt_snapshot="Compare the exact selected works.",
        author=ACTOR,
        target_scope="comparison_set",
        target_references=(
            CurationTargetRef(
                target_kind="selection",
                target_id="selection_baseline",
                semantic_role="baseline",
            ),
            CurationTargetRef(
                target_kind="selection",
                target_id="selection_later",
                semantic_role="later",
            ),
        ),
        content_mode="inline_text",
        language="en",
        content_format="plain_text",
        content="Actor-authored interpretation only.",
        created_at=NOW,
    )
    assert tuple(item.semantic_role for item in reflection.target_references) == (
        "baseline",
        "later",
    )
    assert record_from_json_bytes(record_to_canonical_json_bytes(reflection)) == reflection


def test_accepted_decision_requires_resulting_selection() -> None:
    with pytest.raises(VitrineModelValidationError):
        SelectionDecision(
            selection_decision_id="decision_fixture",
            selection_proposal_id="proposal_fixture",
            decision="accepted",
            decided_at=NOW,
            decided_by=ACTOR,
            authority_reference="fixture_authority",
        )
