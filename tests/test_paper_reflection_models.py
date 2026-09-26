from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone

import pytest

from vitrine.models import (
    ActorAttribution,
    ClassQualifiedStudentRef,
    CurationTargetRef,
    ProfileRevisionRef,
    ReflectionPromptIssuance,
    ReflectionResponsePage,
    record_from_json_bytes,
    record_to_canonical_json_bytes,
)
from vitrine.models.errors import VitrineModelValidationError

NOW = datetime(2026, 9, 25, 20, 0, tzinfo=timezone.utc)

TEACHER = ActorAttribution(
    actor_kind="authorized_adult",
    actor_id="teacher_fixture",
    owning_system="local",
    role_snapshot="teacher",
)

STUDENT = ClassQualifiedStudentRef(
    class_id="english11_p2",
    student_id="student_421",
    school_year="2026-2027",
)

PROFILE = ProfileRevisionRef(
    portfolio_profile_id="improvement",
    profile_revision=1,
)


def _issuance() -> ReflectionPromptIssuance:
    return ReflectionPromptIssuance(
        issuance_id="issuance_fixture",
        portfolio_id="portfolio_fixture",
        portfolio_subject_id="subject_fixture",
        profile_binding_id="binding_fixture",
        profile_revision=PROFILE,
        reflection_requirement_id="reflection_requirement_fixture",
        prompt_id="prompt_fixture",
        prompt_version="1",
        prompt_snapshot="Compare the exact baseline and later selections.",
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
        subject_link_id="subject_link_fixture",
        student_reference=STUDENT,
        response_page_ids=("response_page_1", "response_page_2"),
        issued_at=NOW,
        issued_by=TEACHER,
    )


def test_reflection_prompt_issuance_round_trips_exact_frozen_context() -> None:
    issuance = _issuance()

    payload = record_to_canonical_json_bytes(issuance)
    restored = record_from_json_bytes(payload)

    assert restored == issuance
    assert restored.student_reference == STUDENT
    assert tuple(item.semantic_role for item in restored.target_references) == (
        "baseline",
        "later",
    )
    assert restored.response_page_ids == ("response_page_1", "response_page_2")


def test_reflection_prompt_issuance_is_immutable() -> None:
    issuance = _issuance()

    with pytest.raises(FrozenInstanceError):
        issuance.prompt_snapshot = "Changed later."  # type: ignore[misc]


def test_reflection_prompt_issuance_rejects_duplicate_response_page_ids() -> None:
    with pytest.raises(
        VitrineModelValidationError,
        match="response_page_ids must not contain duplicates",
    ):
        replace(
            _issuance(),
            response_page_ids=("response_page_1", "response_page_1"),
        )


def test_reflection_response_page_round_trips_exact_route_identity() -> None:
    page = ReflectionResponsePage(
        response_page_id="response_page_2",
        issuance_id="issuance_fixture",
        class_id="english11_p2",
        work_id="reflection_issuance_fixture",
        route_id="reflection_route_2",
        logical_page_number=2,
        total_pages=2,
        created_at=NOW,
        created_by=TEACHER,
    )

    assert record_from_json_bytes(record_to_canonical_json_bytes(page)) == page


def test_reflection_response_page_rejects_invalid_logical_page_number() -> None:
    with pytest.raises(
        VitrineModelValidationError,
        match="logical_page_number must not exceed total_pages",
    ):
        ReflectionResponsePage(
            response_page_id="response_page_3",
            issuance_id="issuance_fixture",
            class_id="english11_p2",
            work_id="reflection_issuance_fixture",
            route_id="reflection_route_3",
            logical_page_number=3,
            total_pages=2,
            created_at=NOW,
            created_by=TEACHER,
        )
