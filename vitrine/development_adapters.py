"""Explicit development-only producer-shaped readers and projection adapters.

These adapters model reviewed ScoreForm, Quillan, and Concord semantics for issue
#32. They are Vitrine fixtures, not installed producer integrations. They accept
only immutable bytes supplied by the caller and never resolve paths or workspaces.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Final, cast

from pds_core.identifiers import IdentifierValidationError, validate_identifier

from vitrine.models.sources import (
    ProducerSourceReference,
    SourceArtifactReference,
    SourcePrivacyMetadata,
)
from vitrine.producer_adapters import (
    ProducerAdapterSupportKey,
    ProducerAdapterSupportRequest,
    ProducerManifestReader,
    ProducerProjectionAdapter,
    ProducerProjectionAdapterDeclaration,
    ProducerProjectionAdapterRegistry,
    ProducerProjectionBatch,
    ProducerProjectionError,
    ProducerReaderDescriptor,
    ProducerReaderError,
    ProjectedProducerRelationship,
    ProjectedProducerSource,
    ProjectionDisplaySnapshot,
    ProjectionField,
)

FIXTURE_ADAPTER_CONTRACT_VERSION: Final[str] = "vitrine_fixture_adapter_v1"
FIXTURE_PROJECTION_CONTRACT_VERSION: Final[str] = "vitrine_candidate_projection_v1"
FIXTURE_DIAGNOSTIC_CONTRACT_VERSION: Final[str] = "vitrine_adapter_diagnostic_v1"
FIXTURE_MEDIA_TYPE: Final[str] = "application/vnd.pds.vitrine.fixture+json"

SCOREFORM_FIXTURE_MANIFEST_CONTRACT: Final[str] = (
    "vitrine_fixture_scoreform_manifest_v1"
)
QUILLAN_FIXTURE_MANIFEST_CONTRACT: Final[str] = "vitrine_fixture_quillan_manifest_v1"
CONCORD_FIXTURE_MANIFEST_CONTRACT: Final[str] = "vitrine_fixture_concord_manifest_v1"


class _DuplicateObjectKey(ValueError):
    pass


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant {value}")


def _object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateObjectKey("duplicate JSON object key")
        result[key] = value
    return result


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def _decode_fixture_bytes(value: bytes, *, adapter_id: str) -> dict[str, object]:
    if type(value) is not bytes:
        raise ProducerReaderError(
            "reader.validation_failed",
            "reader",
            "Fixture reader input must be immutable bytes.",
            adapter_id=adapter_id,
        )
    try:
        text = value.decode("utf-8")
        decoded = json.loads(
            text,
            object_pairs_hook=_object_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, _DuplicateObjectKey, ValueError) as error:
        raise ProducerReaderError(
            "reader.decode_failed",
            "reader",
            "Fixture manifest bytes could not be decoded strictly.",
            adapter_id=adapter_id,
        ) from error
    if not isinstance(decoded, dict) or any(not isinstance(key, str) for key in decoded):
        raise ProducerReaderError(
            "reader.validation_failed",
            "reader",
            "Fixture manifest must be one JSON object.",
            adapter_id=adapter_id,
        )
    if _canonical_bytes(decoded) != value:
        raise ProducerReaderError(
            "reader.validation_failed",
            "reader",
            "Fixture manifest bytes are not canonical.",
            adapter_id=adapter_id,
        )
    return cast(dict[str, object], decoded)


def _exact_object(
    value: object,
    keys: frozenset[str],
    label: str,
    *,
    adapter_id: str,
) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ProducerReaderError(
            "reader.validation_failed",
            "reader",
            f"{label} must be an exact JSON object.",
            adapter_id=adapter_id,
        )
    actual = set(value)
    if actual != keys:
        raise ProducerReaderError(
            "reader.validation_failed",
            "reader",
            f"{label} has missing or unknown fields.",
            adapter_id=adapter_id,
        )
    return cast(dict[str, object], value)


def _string(value: object, field_name: str, *, adapter_id: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ProducerReaderError(
            "reader.validation_failed",
            "reader",
            f"{field_name} must be a nonempty trimmed string.",
            adapter_id=adapter_id,
        )
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ProducerReaderError(
            "reader.validation_failed",
            "reader",
            f"{field_name} contains disallowed control characters.",
            adapter_id=adapter_id,
        )
    return value


def _optional_string(value: object, field_name: str, *, adapter_id: str) -> str | None:
    if value is None:
        return None
    return _string(value, field_name, adapter_id=adapter_id)


def _identifier(value: object, field_name: str, *, adapter_id: str) -> str:
    text = _string(value, field_name, adapter_id=adapter_id)
    try:
        return validate_identifier(text, field_name)
    except IdentifierValidationError as error:
        raise ProducerReaderError(
            "reader.validation_failed",
            "reader",
            f"{field_name} must be a safe identifier.",
            adapter_id=adapter_id,
        ) from error


def _positive_int(value: object, field_name: str, *, adapter_id: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ProducerReaderError(
            "reader.validation_failed",
            "reader",
            f"{field_name} must be a positive integer.",
            adapter_id=adapter_id,
        )
    return value


def _number(
    value: object,
    field_name: str,
    *,
    adapter_id: str,
    minimum: float | None = None,
    strictly_positive: bool = False,
) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProducerReaderError(
            "reader.validation_failed",
            "reader",
            f"{field_name} must be numeric.",
            adapter_id=adapter_id,
        )
    if isinstance(value, float) and not math.isfinite(value):
        raise ProducerReaderError(
            "reader.validation_failed",
            "reader",
            f"{field_name} must be finite.",
            adapter_id=adapter_id,
        )
    if minimum is not None and value < minimum:
        raise ProducerReaderError(
            "reader.validation_failed",
            "reader",
            f"{field_name} is below its permitted minimum.",
            adapter_id=adapter_id,
        )
    if strictly_positive and value <= 0:
        raise ProducerReaderError(
            "reader.validation_failed",
            "reader",
            f"{field_name} must be positive.",
            adapter_id=adapter_id,
        )
    return value


def _boolean(value: object, field_name: str, *, adapter_id: str) -> bool:
    if type(value) is not bool:
        raise ProducerReaderError(
            "reader.validation_failed",
            "reader",
            f"{field_name} must be boolean.",
            adapter_id=adapter_id,
        )
    return value


def _array(value: object, field_name: str, *, adapter_id: str) -> list[object]:
    if not isinstance(value, list):
        raise ProducerReaderError(
            "reader.validation_failed",
            "reader",
            f"{field_name} must be a JSON array.",
            adapter_id=adapter_id,
        )
    return cast(list[object], value)


def _timestamp(value: object, field_name: str, *, adapter_id: str) -> str:
    text = _string(value, field_name, adapter_id=adapter_id)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise ProducerReaderError(
            "reader.validation_failed",
            "reader",
            f"{field_name} must be an ISO-8601 timestamp.",
            adapter_id=adapter_id,
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ProducerReaderError(
            "reader.validation_failed",
            "reader",
            f"{field_name} must include a timezone.",
            adapter_id=adapter_id,
        )
    return text


def _string_tuple(value: object, field_name: str, *, adapter_id: str) -> tuple[str, ...]:
    items = _array(value, field_name, adapter_id=adapter_id)
    result = tuple(_string(item, field_name, adapter_id=adapter_id) for item in items)
    if len(set(result)) != len(result):
        raise ProducerReaderError(
            "reader.validation_failed",
            "reader",
            f"{field_name} must not contain duplicates.",
            adapter_id=adapter_id,
        )
    return result



@dataclass(frozen=True, slots=True)
class _ScoreFormResponse:
    question_number: int
    state: str
    selected_answer: str | None
    correct: bool | None
    standard_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _ScoreFormAttempt:
    attempt_number: int
    attempt_origin: str
    recorded_at: str
    points_earned: int | float
    points_possible: int | float
    responses: tuple[_ScoreFormResponse, ...]
    provenance_kind: str
    provenance_source_revision: int
    retained_source_path: str | None
    scan_review_note: str | None


@dataclass(frozen=True, slots=True)
class _ScoreFormFixtureManifest:
    class_id: str
    assignment_id: str
    assignment_title: str
    student_id: str
    attempts: tuple[_ScoreFormAttempt, ...]
    answer_key_marker: str
    detector_marker: str
    route_marker: str


@dataclass(frozen=True, slots=True)
class _QuillanEvidence:
    evidence_id: str
    state: str
    revision: int
    approved_locator: str | None
    title: str
    summary: str


@dataclass(frozen=True, slots=True)
class _QuillanFeedback:
    feedback_id: str
    visibility: str
    revision: int
    approved_locator: str | None
    title: str
    summary: str


@dataclass(frozen=True, slots=True)
class _QuillanPrivateNote:
    note_id: str
    text: str
    native_path: str


@dataclass(frozen=True, slots=True)
class _QuillanFixtureManifest:
    assignment_id: str
    submission_id: str
    submission_revision: int
    student_id: str
    evidence: tuple[_QuillanEvidence, ...]
    feedback: tuple[_QuillanFeedback, ...]
    private_teacher_notes: tuple[_QuillanPrivateNote, ...]
    private_route_metadata: str


@dataclass(frozen=True, slots=True)
class _ConcordAuthor:
    author_kind: str
    author_id: str
    authorship_mode: str
    representation_status: str


@dataclass(frozen=True, slots=True)
class _ConcordSubject:
    subject_kind: str
    subject_id: str


@dataclass(frozen=True, slots=True)
class _ConcordContribution:
    contributor_id: str
    contribution_id: str
    description: str


@dataclass(frozen=True, slots=True)
class _ConcordScore:
    score_id: str
    target_kind: str
    target_id: str
    disposition: str
    scale_id: str
    value: str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class _ConcordFixtureManifest:
    activity_id: str
    artifact_id: str
    artifact_revision: int
    artifact_title: str
    artifact_locator: str
    group_id: str
    representation_status: str
    privacy_classification: str
    group_members: tuple[str, ...]
    authors: tuple[_ConcordAuthor, ...]
    subjects: tuple[_ConcordSubject, ...]
    contributions: tuple[_ConcordContribution, ...]
    scores: tuple[_ConcordScore, ...]


class _FixtureReaderBase:
    descriptor: ProducerReaderDescriptor
    adapter_id: str

    def read(self, value: bytes) -> object:
        raise NotImplementedError


class ScoreFormFixtureReader(_FixtureReaderBase):
    adapter_id = "vitrine_scoreform_fixture_adapter"
    descriptor = ProducerReaderDescriptor(
        public_reader_id="vitrine_fixture_scoreform_reader",
        reader_contract_version="vitrine_fixture_scoreform_reader_v1",
        package_identity="pds-vitrine development fixture reader",
        integration_kind="development_fixture",
    )

    def read(self, value: bytes) -> _ScoreFormFixtureManifest:
        data = _decode_fixture_bytes(value, adapter_id=self.adapter_id)
        expected = frozenset(
            {
                "assignment",
                "attempts",
                "fixture_contract",
                "fixture_version",
                "integration_kind",
                "producer_module_id",
                "producer_shape",
                "prohibited",
            }
        )
        mapping = _exact_object(data, expected, "ScoreForm fixture", adapter_id=self.adapter_id)
        _require_fixture_header(
            mapping,
            adapter_id=self.adapter_id,
            fixture_contract=SCOREFORM_FIXTURE_MANIFEST_CONTRACT,
            producer_module_id="vitrine_scoreform_fixture",
            producer_shape="scoreform_academic_result_manifest_v1",
        )
        assignment = _exact_object(
            mapping["assignment"],
            frozenset({"assignment_id", "class_id", "student_id", "title"}),
            "ScoreForm assignment",
            adapter_id=self.adapter_id,
        )
        class_id = _identifier(
            assignment["class_id"], "class_id", adapter_id=self.adapter_id
        )
        assignment_id = _identifier(
            assignment["assignment_id"], "assignment_id", adapter_id=self.adapter_id
        )
        assignment_title = _string(
            assignment["title"], "assignment title", adapter_id=self.adapter_id
        )
        student_id = _identifier(
            assignment["student_id"], "student_id", adapter_id=self.adapter_id
        )
        attempts: list[_ScoreFormAttempt] = []
        for raw_attempt in _array(mapping["attempts"], "attempts", adapter_id=self.adapter_id):
            attempt = _exact_object(
                raw_attempt,
                frozenset(
                    {
                        "attempt_number",
                        "attempt_origin",
                        "points_earned",
                        "points_possible",
                        "provenance",
                        "recorded_at",
                        "responses",
                    }
                ),
                "ScoreForm attempt",
                adapter_id=self.adapter_id,
            )
            attempt_number = _positive_int(
                attempt["attempt_number"], "attempt_number", adapter_id=self.adapter_id
            )
            origin = _string(
                attempt["attempt_origin"], "attempt_origin", adapter_id=self.adapter_id
            )
            if origin not in {"pds2_scan", "plain_paper_manual", "scan_review_manual"}:
                raise ProducerReaderError(
                    "reader.validation_failed",
                    "reader",
                    "ScoreForm fixture attempt_origin is invalid.",
                    adapter_id=self.adapter_id,
                )
            points_earned = _number(
                attempt["points_earned"],
                "points_earned",
                adapter_id=self.adapter_id,
                minimum=0,
            )
            points_possible = _number(
                attempt["points_possible"],
                "points_possible",
                adapter_id=self.adapter_id,
                strictly_positive=True,
            )
            if points_earned > points_possible:
                raise ProducerReaderError(
                    "reader.validation_failed",
                    "reader",
                    "points_earned must not exceed points_possible.",
                    adapter_id=self.adapter_id,
                )
            responses: list[_ScoreFormResponse] = []
            for raw_response in _array(
                attempt["responses"], "responses", adapter_id=self.adapter_id
            ):
                response = _exact_object(
                    raw_response,
                    frozenset(
                        {
                            "correct",
                            "question_number",
                            "selected_answer",
                            "standard_ids",
                            "state",
                        }
                    ),
                    "ScoreForm response",
                    adapter_id=self.adapter_id,
                )
                state = _string(response["state"], "response state", adapter_id=self.adapter_id)
                if state not in {"selected", "blank", "ambiguous"}:
                    raise ProducerReaderError(
                        "reader.validation_failed",
                        "reader",
                        "ScoreForm fixture response state is invalid.",
                        adapter_id=self.adapter_id,
                    )
                selected_answer = _optional_string(
                    response["selected_answer"],
                    "selected_answer",
                    adapter_id=self.adapter_id,
                )
                correct_value = response["correct"]
                correct = (
                    None
                    if correct_value is None
                    else _boolean(correct_value, "correct", adapter_id=self.adapter_id)
                )
                if state == "selected" and selected_answer is None:
                    raise ProducerReaderError(
                        "reader.validation_failed",
                        "reader",
                        "selected response requires selected_answer.",
                        adapter_id=self.adapter_id,
                    )
                if state != "selected" and selected_answer is not None:
                    raise ProducerReaderError(
                        "reader.validation_failed",
                        "reader",
                        "non-selected response must not carry selected_answer.",
                        adapter_id=self.adapter_id,
                    )
                responses.append(
                    _ScoreFormResponse(
                        question_number=_positive_int(
                            response["question_number"],
                            "question_number",
                            adapter_id=self.adapter_id,
                        ),
                        state=state,
                        selected_answer=selected_answer,
                        correct=correct,
                        standard_ids=_string_tuple(
                            response["standard_ids"],
                            "standard_ids",
                            adapter_id=self.adapter_id,
                        ),
                    )
                )
            if len({item.question_number for item in responses}) != len(responses):
                raise ProducerReaderError(
                    "reader.validation_failed",
                    "reader",
                    "ScoreForm fixture attempt contains duplicate question numbers.",
                    adapter_id=self.adapter_id,
                )
            provenance = _exact_object(
                attempt["provenance"],
                frozenset(
                    {
                        "kind",
                        "retained_source_path",
                        "scan_review_note",
                        "source_revision",
                    }
                ),
                "ScoreForm provenance",
                adapter_id=self.adapter_id,
            )
            attempts.append(
                _ScoreFormAttempt(
                    attempt_number=attempt_number,
                    attempt_origin=origin,
                    recorded_at=_timestamp(
                        attempt["recorded_at"], "recorded_at", adapter_id=self.adapter_id
                    ),
                    points_earned=points_earned,
                    points_possible=points_possible,
                    responses=tuple(sorted(responses, key=lambda item: item.question_number)),
                    provenance_kind=_string(
                        provenance["kind"], "provenance kind", adapter_id=self.adapter_id
                    ),
                    provenance_source_revision=_positive_int(
                        provenance["source_revision"],
                        "source_revision",
                        adapter_id=self.adapter_id,
                    ),
                    retained_source_path=_optional_string(
                        provenance["retained_source_path"],
                        "retained_source_path",
                        adapter_id=self.adapter_id,
                    ),
                    scan_review_note=_optional_string(
                        provenance["scan_review_note"],
                        "scan_review_note",
                        adapter_id=self.adapter_id,
                    ),
                )
            )
        if not attempts or len({item.attempt_number for item in attempts}) != len(attempts):
            raise ProducerReaderError(
                "reader.validation_failed",
                "reader",
                "ScoreForm fixture attempts must be nonempty with unique attempt numbers.",
                adapter_id=self.adapter_id,
            )
        prohibited = _exact_object(
            mapping["prohibited"],
            frozenset({"answer_key_marker", "detector_marker", "route_marker"}),
            "ScoreForm prohibited fixture data",
            adapter_id=self.adapter_id,
        )
        return _ScoreFormFixtureManifest(
            class_id=class_id,
            assignment_id=assignment_id,
            assignment_title=assignment_title,
            student_id=student_id,
            attempts=tuple(sorted(attempts, key=lambda item: item.attempt_number)),
            answer_key_marker=_string(
                prohibited["answer_key_marker"],
                "answer_key_marker",
                adapter_id=self.adapter_id,
            ),
            detector_marker=_string(
                prohibited["detector_marker"],
                "detector_marker",
                adapter_id=self.adapter_id,
            ),
            route_marker=_string(
                prohibited["route_marker"], "route_marker", adapter_id=self.adapter_id
            ),
        )


class QuillanFixtureReader(_FixtureReaderBase):
    adapter_id = "vitrine_quillan_fixture_adapter"
    descriptor = ProducerReaderDescriptor(
        public_reader_id="vitrine_fixture_quillan_reader",
        reader_contract_version="vitrine_fixture_quillan_reader_v1",
        package_identity="pds-vitrine development fixture reader",
        integration_kind="development_fixture",
    )

    def read(self, value: bytes) -> _QuillanFixtureManifest:
        data = _decode_fixture_bytes(value, adapter_id=self.adapter_id)
        mapping = _exact_object(
            data,
            frozenset(
                {
                    "assignment_id",
                    "evidence",
                    "feedback",
                    "fixture_contract",
                    "fixture_version",
                    "integration_kind",
                    "private_route_metadata",
                    "private_teacher_notes",
                    "producer_module_id",
                    "producer_shape",
                    "student_id",
                    "submission_id",
                    "submission_revision",
                }
            ),
            "Quillan fixture",
            adapter_id=self.adapter_id,
        )
        _require_fixture_header(
            mapping,
            adapter_id=self.adapter_id,
            fixture_contract=QUILLAN_FIXTURE_MANIFEST_CONTRACT,
            producer_module_id="vitrine_quillan_fixture",
            producer_shape="quillan_submission_review_export_shape",
        )
        evidence: list[_QuillanEvidence] = []
        allowed_evidence_states = {
            "selected",
            "approved",
            "candidate",
            "duplicate",
            "excluded",
            "unrelated_replacement",
        }
        for raw in _array(mapping["evidence"], "evidence", adapter_id=self.adapter_id):
            row = _exact_object(
                raw,
                frozenset(
                    {"approved_locator", "evidence_id", "revision", "state", "summary", "title"}
                ),
                "Quillan evidence",
                adapter_id=self.adapter_id,
            )
            state = _string(row["state"], "evidence state", adapter_id=self.adapter_id)
            if state not in allowed_evidence_states:
                raise ProducerReaderError(
                    "reader.validation_failed",
                    "reader",
                    "Quillan fixture evidence state is invalid.",
                    adapter_id=self.adapter_id,
                )
            evidence.append(
                _QuillanEvidence(
                    evidence_id=_identifier(
                        row["evidence_id"], "evidence_id", adapter_id=self.adapter_id
                    ),
                    state=state,
                    revision=_positive_int(
                        row["revision"], "evidence revision", adapter_id=self.adapter_id
                    ),
                    approved_locator=_optional_string(
                        row["approved_locator"],
                        "approved_locator",
                        adapter_id=self.adapter_id,
                    ),
                    title=_string(row["title"], "evidence title", adapter_id=self.adapter_id),
                    summary=_string(
                        row["summary"], "evidence summary", adapter_id=self.adapter_id
                    ),
                )
            )
        feedback: list[_QuillanFeedback] = []
        for raw in _array(mapping["feedback"], "feedback", adapter_id=self.adapter_id):
            row = _exact_object(
                raw,
                frozenset(
                    {"approved_locator", "feedback_id", "revision", "summary", "title", "visibility"}
                ),
                "Quillan feedback",
                adapter_id=self.adapter_id,
            )
            visibility = _string(
                row["visibility"], "feedback visibility", adapter_id=self.adapter_id
            )
            if visibility not in {"student_facing", "private_teacher"}:
                raise ProducerReaderError(
                    "reader.validation_failed",
                    "reader",
                    "Quillan fixture feedback visibility is invalid.",
                    adapter_id=self.adapter_id,
                )
            feedback.append(
                _QuillanFeedback(
                    feedback_id=_identifier(
                        row["feedback_id"], "feedback_id", adapter_id=self.adapter_id
                    ),
                    visibility=visibility,
                    revision=_positive_int(
                        row["revision"], "feedback revision", adapter_id=self.adapter_id
                    ),
                    approved_locator=_optional_string(
                        row["approved_locator"],
                        "approved_locator",
                        adapter_id=self.adapter_id,
                    ),
                    title=_string(row["title"], "feedback title", adapter_id=self.adapter_id),
                    summary=_string(
                        row["summary"], "feedback summary", adapter_id=self.adapter_id
                    ),
                )
            )
        notes: list[_QuillanPrivateNote] = []
        for raw in _array(
            mapping["private_teacher_notes"],
            "private_teacher_notes",
            adapter_id=self.adapter_id,
        ):
            row = _exact_object(
                raw,
                frozenset({"native_path", "note_id", "text"}),
                "Quillan private note",
                adapter_id=self.adapter_id,
            )
            notes.append(
                _QuillanPrivateNote(
                    note_id=_identifier(row["note_id"], "note_id", adapter_id=self.adapter_id),
                    text=_string(row["text"], "private note", adapter_id=self.adapter_id),
                    native_path=_string(
                        row["native_path"], "native_path", adapter_id=self.adapter_id
                    ),
                )
            )
        return _QuillanFixtureManifest(
            assignment_id=_identifier(
                mapping["assignment_id"], "assignment_id", adapter_id=self.adapter_id
            ),
            submission_id=_identifier(
                mapping["submission_id"], "submission_id", adapter_id=self.adapter_id
            ),
            submission_revision=_positive_int(
                mapping["submission_revision"],
                "submission_revision",
                adapter_id=self.adapter_id,
            ),
            student_id=_identifier(
                mapping["student_id"], "student_id", adapter_id=self.adapter_id
            ),
            evidence=tuple(evidence),
            feedback=tuple(feedback),
            private_teacher_notes=tuple(notes),
            private_route_metadata=_string(
                mapping["private_route_metadata"],
                "private_route_metadata",
                adapter_id=self.adapter_id,
            ),
        )


class ConcordFixtureReader(_FixtureReaderBase):
    adapter_id = "vitrine_concord_fixture_adapter"
    descriptor = ProducerReaderDescriptor(
        public_reader_id="vitrine_fixture_concord_reader",
        reader_contract_version="vitrine_fixture_concord_reader_v1",
        package_identity="pds-vitrine development fixture reader",
        integration_kind="development_fixture",
    )

    def read(self, value: bytes) -> _ConcordFixtureManifest:
        data = _decode_fixture_bytes(value, adapter_id=self.adapter_id)
        mapping = _exact_object(
            data,
            frozenset(
                {
                    "activity_id",
                    "artifact",
                    "authors",
                    "contributions",
                    "fixture_contract",
                    "fixture_version",
                    "group_id",
                    "group_members",
                    "integration_kind",
                    "producer_module_id",
                    "producer_shape",
                    "scores",
                    "subjects",
                }
            ),
            "Concord fixture",
            adapter_id=self.adapter_id,
        )
        _require_fixture_header(
            mapping,
            adapter_id=self.adapter_id,
            fixture_contract=CONCORD_FIXTURE_MANIFEST_CONTRACT,
            producer_module_id="vitrine_concord_fixture",
            producer_shape="concord_artifact_relationship_score_shape",
        )
        artifact = _exact_object(
            mapping["artifact"],
            frozenset(
                {
                    "artifact_id",
                    "artifact_locator",
                    "artifact_revision",
                    "privacy_classification",
                    "representation_status",
                    "title",
                }
            ),
            "Concord artifact",
            adapter_id=self.adapter_id,
        )
        members = tuple(
            _identifier(item, "group_member", adapter_id=self.adapter_id)
            for item in _array(mapping["group_members"], "group_members", adapter_id=self.adapter_id)
        )
        if len(set(members)) != len(members):
            raise ProducerReaderError(
                "reader.validation_failed",
                "reader",
                "Concord fixture group_members must be unique.",
                adapter_id=self.adapter_id,
            )
        authors: list[_ConcordAuthor] = []
        for raw in _array(mapping["authors"], "authors", adapter_id=self.adapter_id):
            row = _exact_object(
                raw,
                frozenset(
                    {"author_id", "author_kind", "authorship_mode", "representation_status"}
                ),
                "Concord author",
                adapter_id=self.adapter_id,
            )
            author_kind = _string(
                row["author_kind"], "author_kind", adapter_id=self.adapter_id
            )
            if author_kind not in {"core_student", "concord_group"}:
                raise ProducerReaderError(
                    "reader.validation_failed",
                    "reader",
                    "Concord fixture author_kind is invalid.",
                    adapter_id=self.adapter_id,
                )
            authors.append(
                _ConcordAuthor(
                    author_kind=author_kind,
                    author_id=_identifier(
                        row["author_id"], "author_id", adapter_id=self.adapter_id
                    ),
                    authorship_mode=_string(
                        row["authorship_mode"], "authorship_mode", adapter_id=self.adapter_id
                    ),
                    representation_status=_string(
                        row["representation_status"],
                        "representation_status",
                        adapter_id=self.adapter_id,
                    ),
                )
            )
        subjects: list[_ConcordSubject] = []
        for raw in _array(mapping["subjects"], "subjects", adapter_id=self.adapter_id):
            row = _exact_object(
                raw,
                frozenset({"subject_id", "subject_kind"}),
                "Concord subject",
                adapter_id=self.adapter_id,
            )
            kind = _string(row["subject_kind"], "subject_kind", adapter_id=self.adapter_id)
            if kind not in {"core_student", "concord_group"}:
                raise ProducerReaderError(
                    "reader.validation_failed",
                    "reader",
                    "Concord fixture subject_kind is invalid.",
                    adapter_id=self.adapter_id,
                )
            subjects.append(
                _ConcordSubject(
                    subject_kind=kind,
                    subject_id=_identifier(
                        row["subject_id"], "subject_id", adapter_id=self.adapter_id
                    ),
                )
            )
        contributions: list[_ConcordContribution] = []
        for raw in _array(
            mapping["contributions"], "contributions", adapter_id=self.adapter_id
        ):
            row = _exact_object(
                raw,
                frozenset({"contribution_id", "contributor_id", "description"}),
                "Concord contribution",
                adapter_id=self.adapter_id,
            )
            contributions.append(
                _ConcordContribution(
                    contributor_id=_identifier(
                        row["contributor_id"],
                        "contributor_id",
                        adapter_id=self.adapter_id,
                    ),
                    contribution_id=_identifier(
                        row["contribution_id"],
                        "contribution_id",
                        adapter_id=self.adapter_id,
                    ),
                    description=_string(
                        row["description"], "contribution description", adapter_id=self.adapter_id
                    ),
                )
            )
        scores: list[_ConcordScore] = []
        for raw in _array(mapping["scores"], "scores", adapter_id=self.adapter_id):
            row = _exact_object(
                raw,
                frozenset(
                    {"disposition", "scale_id", "score_id", "target_id", "target_kind", "value"}
                ),
                "Concord score",
                adapter_id=self.adapter_id,
            )
            target_kind = _string(
                row["target_kind"], "target_kind", adapter_id=self.adapter_id
            )
            if target_kind not in {"concord_group", "core_student"}:
                raise ProducerReaderError(
                    "reader.validation_failed",
                    "reader",
                    "Concord fixture score target_kind is invalid.",
                    adapter_id=self.adapter_id,
                )
            disposition = _string(
                row["disposition"], "score disposition", adapter_id=self.adapter_id
            )
            allowed_dispositions = {
                "scored",
                "insufficient_evidence",
                "absent",
                "excused",
                "not_observed",
                "not_applicable",
                "deferred",
            }
            if disposition not in allowed_dispositions:
                raise ProducerReaderError(
                    "reader.validation_failed",
                    "reader",
                    "Concord fixture score disposition is invalid.",
                    adapter_id=self.adapter_id,
                )
            raw_value = row["value"]
            if disposition == "scored":
                if raw_value is None or isinstance(raw_value, (list, dict)):
                    raise ProducerReaderError(
                        "reader.validation_failed",
                        "reader",
                        "Scored Concord fixture row requires one scalar value.",
                        adapter_id=self.adapter_id,
                    )
                if isinstance(raw_value, float) and not math.isfinite(raw_value):
                    raise ProducerReaderError(
                        "reader.validation_failed",
                        "reader",
                        "Concord score value must be finite.",
                        adapter_id=self.adapter_id,
                    )
                if not isinstance(raw_value, (str, bool, int, float)):
                    raise ProducerReaderError(
                        "reader.validation_failed",
                        "reader",
                        "Concord score value must be a JSON scalar.",
                        adapter_id=self.adapter_id,
                    )
                value_scalar: str | int | float | bool | None = raw_value
            else:
                if raw_value is not None:
                    raise ProducerReaderError(
                        "reader.validation_failed",
                        "reader",
                        "Non-score Concord dispositions must not carry a value.",
                        adapter_id=self.adapter_id,
                    )
                value_scalar = None
            scores.append(
                _ConcordScore(
                    score_id=_identifier(
                        row["score_id"], "score_id", adapter_id=self.adapter_id
                    ),
                    target_kind=target_kind,
                    target_id=_identifier(
                        row["target_id"], "target_id", adapter_id=self.adapter_id
                    ),
                    disposition=disposition,
                    scale_id=_identifier(
                        row["scale_id"], "scale_id", adapter_id=self.adapter_id
                    ),
                    value=value_scalar,
                )
            )
        return _ConcordFixtureManifest(
            activity_id=_identifier(
                mapping["activity_id"], "activity_id", adapter_id=self.adapter_id
            ),
            artifact_id=_identifier(
                artifact["artifact_id"], "artifact_id", adapter_id=self.adapter_id
            ),
            artifact_revision=_positive_int(
                artifact["artifact_revision"],
                "artifact_revision",
                adapter_id=self.adapter_id,
            ),
            artifact_title=_string(
                artifact["title"], "artifact title", adapter_id=self.adapter_id
            ),
            artifact_locator=_string(
                artifact["artifact_locator"],
                "artifact_locator",
                adapter_id=self.adapter_id,
            ),
            group_id=_identifier(
                mapping["group_id"], "group_id", adapter_id=self.adapter_id
            ),
            representation_status=_string(
                artifact["representation_status"],
                "representation_status",
                adapter_id=self.adapter_id,
            ),
            privacy_classification=_string(
                artifact["privacy_classification"],
                "privacy_classification",
                adapter_id=self.adapter_id,
            ),
            group_members=members,
            authors=tuple(authors),
            subjects=tuple(subjects),
            contributions=tuple(contributions),
            scores=tuple(scores),
        )


def _require_fixture_header(
    mapping: Mapping[str, object],
    *,
    adapter_id: str,
    fixture_contract: str,
    producer_module_id: str,
    producer_shape: str,
) -> None:
    expected = {
        "fixture_contract": fixture_contract,
        "fixture_version": "1",
        "integration_kind": "development_fixture",
        "producer_module_id": producer_module_id,
        "producer_shape": producer_shape,
    }
    for key, value in expected.items():
        if mapping[key] != value:
            raise ProducerReaderError(
                "reader.incompatible",
                "reader",
                "Fixture header does not match this exact development contract.",
                adapter_id=adapter_id,
            )


SCOREFORM_FIXTURE_SUPPORT_KEY = ProducerAdapterSupportKey(
    producer_module_id="vitrine_scoreform_fixture",
    core_publication_schema_version="1",
    publication_kind="academic_result_set",
    manifest_contract_version=SCOREFORM_FIXTURE_MANIFEST_CONTRACT,
    producer_contract_version="vitrine_fixture_scoreform_academic_work_v1",
    source_record_kind=None,
    source_record_contract_version=None,
    required_capabilities=("multiple_attempts", "points", "question_evidence"),
)
QUILLAN_FIXTURE_SUPPORT_KEY = ProducerAdapterSupportKey(
    producer_module_id="vitrine_quillan_fixture",
    core_publication_schema_version="1",
    publication_kind="academic_result_set",
    manifest_contract_version=QUILLAN_FIXTURE_MANIFEST_CONTRACT,
    producer_contract_version="vitrine_fixture_quillan_academic_work_v1",
    source_record_kind="submission",
    source_record_contract_version="vitrine_fixture_quillan_submission_v1",
    required_capabilities=(),
)
CONCORD_FIXTURE_SUPPORT_KEY = ProducerAdapterSupportKey(
    producer_module_id="vitrine_concord_fixture",
    core_publication_schema_version="1",
    publication_kind="academic_result_set",
    manifest_contract_version=CONCORD_FIXTURE_MANIFEST_CONTRACT,
    producer_contract_version="vitrine_fixture_concord_academic_work_v1",
    source_record_kind="artifact_instance",
    source_record_contract_version="vitrine_fixture_concord_artifact_v1",
    required_capabilities=("criterion_scores",),
)

SCOREFORM_FIXTURE_SUPPORT_REQUEST = ProducerAdapterSupportRequest(
    producer_module_id=SCOREFORM_FIXTURE_SUPPORT_KEY.producer_module_id,
    core_publication_schema_version="1",
    publication_kind="academic_result_set",
    manifest_contract_version=SCOREFORM_FIXTURE_MANIFEST_CONTRACT,
    producer_contract_version=SCOREFORM_FIXTURE_SUPPORT_KEY.producer_contract_version,
    source_record_kind=None,
    source_record_contract_version=None,
    capabilities=("question_evidence", "multiple_attempts", "points"),
)
QUILLAN_FIXTURE_SUPPORT_REQUEST = ProducerAdapterSupportRequest(
    producer_module_id=QUILLAN_FIXTURE_SUPPORT_KEY.producer_module_id,
    core_publication_schema_version="1",
    publication_kind="academic_result_set",
    manifest_contract_version=QUILLAN_FIXTURE_MANIFEST_CONTRACT,
    producer_contract_version=QUILLAN_FIXTURE_SUPPORT_KEY.producer_contract_version,
    source_record_kind="submission",
    source_record_contract_version="vitrine_fixture_quillan_submission_v1",
    capabilities=(),
)
CONCORD_FIXTURE_SUPPORT_REQUEST = ProducerAdapterSupportRequest(
    producer_module_id=CONCORD_FIXTURE_SUPPORT_KEY.producer_module_id,
    core_publication_schema_version="1",
    publication_kind="academic_result_set",
    manifest_contract_version=CONCORD_FIXTURE_MANIFEST_CONTRACT,
    producer_contract_version=CONCORD_FIXTURE_SUPPORT_KEY.producer_contract_version,
    source_record_kind="artifact_instance",
    source_record_contract_version="vitrine_fixture_concord_artifact_v1",
    capabilities=("criterion_scores",),
)


class _FixtureProjectionAdapter:
    def __init__(
        self,
        declaration: ProducerProjectionAdapterDeclaration,
        reader: ProducerManifestReader,
        projector: Callable[[object], ProducerProjectionBatch],
    ) -> None:
        self._declaration = declaration
        self._reader = reader
        self._projector = projector

    @property
    def declaration(self) -> ProducerProjectionAdapterDeclaration:
        return self._declaration

    @property
    def reader(self) -> ProducerManifestReader:
        return self._reader

    def project(self, public_model: object) -> ProducerProjectionBatch:
        try:
            return self._projector(public_model)
        except ProducerProjectionError:
            raise
        except Exception as error:
            raise ProducerProjectionError(
                "projection.failed",
                "projection",
                "Development fixture projection failed.",
                adapter_id=self._declaration.adapter_id,
            ) from error


def _single_subject_privacy() -> SourcePrivacyMetadata:
    return SourcePrivacyMetadata(
        classification="student_record",
        subject_scope="single_subject",
        metadata_visibility="internal",
        collaborator_information_present=False,
        third_party_information_present=False,
        rights_review_required=False,
        redaction_review_required=False,
        multi_subject_review_required=False,
        minimum_necessary_projection_required=True,
        policy_reference="vitrine_fixture_minimum_necessary",
    )


def _collaborative_privacy(classification: str) -> SourcePrivacyMetadata:
    return SourcePrivacyMetadata(
        classification=classification,
        subject_scope="multi_subject",
        metadata_visibility="internal",
        collaborator_information_present=True,
        third_party_information_present=False,
        rights_review_required=False,
        redaction_review_required=True,
        multi_subject_review_required=True,
        minimum_necessary_projection_required=True,
        policy_reference="vitrine_fixture_collaborative_review",
    )


def _batch(
    declaration: ProducerProjectionAdapterDeclaration,
    sources: tuple[ProjectedProducerSource, ...],
) -> ProducerProjectionBatch:
    return ProducerProjectionBatch(
        adapter_id=declaration.adapter_id,
        adapter_contract_version=declaration.adapter_contract_version,
        reader_id=declaration.public_reader_id,
        reader_contract_version=declaration.reader_contract_version,
        candidate_projection_contract_version=declaration.candidate_projection_contract_version,
        support_key=declaration.support_key,
        projected_sources=sources,
        diagnostic_codes=(),
    )


def _scoreform_project(public_model: object) -> ProducerProjectionBatch:
    if not isinstance(public_model, _ScoreFormFixtureManifest):
        raise ProducerProjectionError(
            "projection.invalid_input",
            "projection",
            "ScoreForm fixture adapter requires its validated public fixture model.",
            adapter_id=SCOREFORM_DECLARATION.adapter_id,
        )
    sources: list[ProjectedProducerSource] = []
    for attempt in public_model.attempts:
        response_states = tuple(
            f"{response.question_number}:{response.state}" for response in attempt.responses
        )
        standard_alignments = tuple(
            f"{response.question_number}:{standard_id}"
            for response in attempt.responses
            for standard_id in response.standard_ids
        )
        producer_source = ProducerSourceReference(
            producer_module_id="vitrine_scoreform_fixture",
            producer_contract_version="vitrine_fixture_scoreform_academic_work_v1",
            source_record_kind="academic_result_attempt",
            source_record_id=f"{public_model.assignment_id}_attempt_{attempt.attempt_number}",
            source_record_contract_version="vitrine_fixture_scoreform_attempt_v1",
            native_revision=attempt.attempt_number,
            native_lifecycle="recorded",
            native_disposition="attempt",
            lineage_reference=f"{public_model.class_id}:{public_model.assignment_id}",
            reader_contract_version=SCOREFORM_DECLARATION.reader_contract_version,
            projection_contract_version=SCOREFORM_DECLARATION.candidate_projection_contract_version,
        )
        sources.append(
            ProjectedProducerSource(
                projection_kind="scoreform_fixture:attempt_summary",
                producer_source=producer_source,
                source_artifact=SourceArtifactReference(
                    artifact_id=f"{producer_source.source_record_id}_summary",
                    artifact_kind="assessment_summary",
                    representation_kind="scoreform_fixture:attempt_summary",
                    media_type=FIXTURE_MEDIA_TYPE,
                    source_locator=None,
                    native_revision=attempt.attempt_number,
                    source_digest=None,
                    byte_size=None,
                    language="en",
                    accessibility_relationship=None,
                ),
                source_relationships=(
                    ProjectedProducerRelationship(
                        source_subject_kind="core_student",
                        source_subject_id=public_model.student_id,
                        relationship_kind="attempt_subject",
                        relationship_authority="scoreform_fixture",
                        supporting_source_reference=producer_source.source_record_id,
                    ),
                ),
                source_privacy=_single_subject_privacy(),
                display_snapshot=ProjectionDisplaySnapshot(
                    title=f"{public_model.assignment_title} — Attempt {attempt.attempt_number}",
                    summary="Synthetic ScoreForm-shaped attempt summary.",
                    fields=(
                        ProjectionField(key="assignment_id", value=public_model.assignment_id),
                        ProjectionField(key="class_id", value=public_model.class_id),
                        ProjectionField(key="attempt_number", value=attempt.attempt_number),
                        ProjectionField(key="attempt_origin", value=attempt.attempt_origin),
                        ProjectionField(key="points_earned", value=attempt.points_earned),
                        ProjectionField(key="points_possible", value=attempt.points_possible),
                        ProjectionField(key="provenance_kind", value=attempt.provenance_kind),
                        ProjectionField(
                            key="provenance_source_revision",
                            value=attempt.provenance_source_revision,
                        ),
                        ProjectionField(key="recorded_at", value=attempt.recorded_at),
                        ProjectionField(key="response_states", value=response_states),
                        ProjectionField(key="standard_alignments", value=standard_alignments),
                    ),
                ),
            )
        )
    return _batch(SCOREFORM_DECLARATION, tuple(sources))


def _quillan_project(public_model: object) -> ProducerProjectionBatch:
    if not isinstance(public_model, _QuillanFixtureManifest):
        raise ProducerProjectionError(
            "projection.invalid_input",
            "projection",
            "Quillan fixture adapter requires its validated public fixture model.",
            adapter_id=QUILLAN_DECLARATION.adapter_id,
        )
    sources: list[ProjectedProducerSource] = []
    for evidence in public_model.evidence:
        if evidence.state not in {"selected", "approved"}:
            continue
        producer_source = ProducerSourceReference(
            producer_module_id="vitrine_quillan_fixture",
            producer_contract_version="vitrine_fixture_quillan_academic_work_v1",
            source_record_kind="submission_evidence",
            source_record_id=evidence.evidence_id,
            source_record_contract_version="vitrine_fixture_quillan_evidence_v1",
            native_revision=evidence.revision,
            native_lifecycle="reviewed",
            native_disposition=evidence.state,
            lineage_reference=public_model.submission_id,
            reader_contract_version=QUILLAN_DECLARATION.reader_contract_version,
            projection_contract_version=QUILLAN_DECLARATION.candidate_projection_contract_version,
        )
        sources.append(
            ProjectedProducerSource(
                projection_kind="quillan_fixture:student_work",
                producer_source=producer_source,
                source_artifact=SourceArtifactReference(
                    artifact_id=f"{evidence.evidence_id}_work",
                    artifact_kind="original_student_work",
                    representation_kind="quillan_fixture:student_work",
                    media_type="text/plain",
                    source_locator=evidence.approved_locator,
                    native_revision=evidence.revision,
                    source_digest=None,
                    byte_size=None,
                    language="en",
                    accessibility_relationship=None,
                ),
                source_relationships=(
                    ProjectedProducerRelationship(
                        source_subject_kind="core_student",
                        source_subject_id=public_model.student_id,
                        relationship_kind="submission_subject",
                        relationship_authority="quillan_fixture",
                        supporting_source_reference=public_model.submission_id,
                    ),
                ),
                source_privacy=_single_subject_privacy(),
                display_snapshot=ProjectionDisplaySnapshot(
                    title=evidence.title,
                    summary=evidence.summary,
                    fields=(
                        ProjectionField(key="assignment_id", value=public_model.assignment_id),
                        ProjectionField(key="submission_id", value=public_model.submission_id),
                        ProjectionField(key="evidence_state", value=evidence.state),
                    ),
                ),
            )
        )
    for feedback in public_model.feedback:
        if feedback.visibility != "student_facing":
            continue
        producer_source = ProducerSourceReference(
            producer_module_id="vitrine_quillan_fixture",
            producer_contract_version="vitrine_fixture_quillan_academic_work_v1",
            source_record_kind="student_feedback",
            source_record_id=feedback.feedback_id,
            source_record_contract_version="vitrine_fixture_quillan_feedback_v1",
            native_revision=feedback.revision,
            native_lifecycle="rendered",
            native_disposition="student_facing",
            lineage_reference=public_model.submission_id,
            reader_contract_version=QUILLAN_DECLARATION.reader_contract_version,
            projection_contract_version=QUILLAN_DECLARATION.candidate_projection_contract_version,
        )
        sources.append(
            ProjectedProducerSource(
                projection_kind="quillan_fixture:student_feedback",
                producer_source=producer_source,
                source_artifact=SourceArtifactReference(
                    artifact_id=f"{feedback.feedback_id}_feedback",
                    artifact_kind="rendered_feedback",
                    representation_kind="quillan_fixture:student_feedback",
                    media_type="text/markdown",
                    source_locator=feedback.approved_locator,
                    native_revision=feedback.revision,
                    source_digest=None,
                    byte_size=None,
                    language="en",
                    accessibility_relationship=None,
                ),
                source_relationships=(
                    ProjectedProducerRelationship(
                        source_subject_kind="core_student",
                        source_subject_id=public_model.student_id,
                        relationship_kind="submission_subject",
                        relationship_authority="quillan_fixture",
                        supporting_source_reference=public_model.submission_id,
                    ),
                ),
                source_privacy=_single_subject_privacy(),
                display_snapshot=ProjectionDisplaySnapshot(
                    title=feedback.title,
                    summary=feedback.summary,
                    fields=(
                        ProjectionField(key="assignment_id", value=public_model.assignment_id),
                        ProjectionField(key="submission_id", value=public_model.submission_id),
                        ProjectionField(key="feedback_visibility", value=feedback.visibility),
                    ),
                ),
            )
        )
    return _batch(QUILLAN_DECLARATION, tuple(sources))


def _concord_project(public_model: object) -> ProducerProjectionBatch:
    if not isinstance(public_model, _ConcordFixtureManifest):
        raise ProducerProjectionError(
            "projection.invalid_input",
            "projection",
            "Concord fixture adapter requires its validated public fixture model.",
            adapter_id=CONCORD_DECLARATION.adapter_id,
        )
    relationships: list[ProjectedProducerRelationship] = []
    for member in public_model.group_members:
        relationships.append(
            ProjectedProducerRelationship(
                source_subject_kind="core_student",
                source_subject_id=member,
                relationship_kind="group_member",
                relationship_authority="concord_fixture",
                supporting_source_reference=public_model.group_id,
            )
        )
    for author in public_model.authors:
        relationships.append(
            ProjectedProducerRelationship(
                source_subject_kind=author.author_kind,
                source_subject_id=author.author_id,
                relationship_kind="artifact_author",
                relationship_authority="concord_fixture",
                supporting_source_reference=public_model.artifact_id,
            )
        )
        if author.representation_status != "not_applicable":
            relationships.append(
                ProjectedProducerRelationship(
                    source_subject_kind=author.author_kind,
                    source_subject_id=author.author_id,
                    relationship_kind="represented_group",
                    relationship_authority="concord_fixture",
                    supporting_source_reference=public_model.group_id,
                )
            )
    for subject in public_model.subjects:
        relationships.append(
            ProjectedProducerRelationship(
                source_subject_kind=subject.subject_kind,
                source_subject_id=subject.subject_id,
                relationship_kind="artifact_subject",
                relationship_authority="concord_fixture",
                supporting_source_reference=public_model.artifact_id,
            )
        )
    for contribution in public_model.contributions:
        relationships.append(
            ProjectedProducerRelationship(
                source_subject_kind="core_student",
                source_subject_id=contribution.contributor_id,
                relationship_kind="documented_contributor",
                relationship_authority="concord_fixture",
                supporting_source_reference=contribution.contribution_id,
            )
        )
    artifact_source = ProducerSourceReference(
        producer_module_id="vitrine_concord_fixture",
        producer_contract_version="vitrine_fixture_concord_academic_work_v1",
        source_record_kind="artifact_instance",
        source_record_id=public_model.artifact_id,
        source_record_contract_version="vitrine_fixture_concord_artifact_v1",
        native_revision=public_model.artifact_revision,
        native_lifecycle="completed",
        native_disposition="collaborative_artifact",
        lineage_reference=public_model.activity_id,
        reader_contract_version=CONCORD_DECLARATION.reader_contract_version,
        projection_contract_version=CONCORD_DECLARATION.candidate_projection_contract_version,
    )
    sources: list[ProjectedProducerSource] = [
        ProjectedProducerSource(
            projection_kind="concord_fixture:artifact",
            producer_source=artifact_source,
            source_artifact=SourceArtifactReference(
                artifact_id=public_model.artifact_id,
                artifact_kind="collaborative_artifact",
                representation_kind="concord_fixture:artifact",
                media_type=(
                    "text/plain"
                    if public_model.artifact_locator.lower().endswith(".txt")
                    else "application/pdf"
                ),
                source_locator=public_model.artifact_locator,
                native_revision=public_model.artifact_revision,
                source_digest=None,
                byte_size=None,
                language="en",
                accessibility_relationship=None,
            ),
            source_relationships=tuple(relationships),
            source_privacy=_collaborative_privacy(public_model.privacy_classification),
            display_snapshot=ProjectionDisplaySnapshot(
                title=public_model.artifact_title,
                summary="Synthetic Concord-shaped collaborative Artifact.",
                fields=(
                    ProjectionField(key="activity_id", value=public_model.activity_id),
                    ProjectionField(key="group_id", value=public_model.group_id),
                    ProjectionField(
                        key="representation_status", value=public_model.representation_status
                    ),
                ),
            ),
        )
    ]
    for score in public_model.scores:
        target_relationship = (
            "group_score_target"
            if score.target_kind == "concord_group"
            else "individual_score_target"
        )
        score_source = ProducerSourceReference(
            producer_module_id="vitrine_concord_fixture",
            producer_contract_version="vitrine_fixture_concord_academic_work_v1",
            source_record_kind="score_record",
            source_record_id=score.score_id,
            source_record_contract_version="vitrine_fixture_concord_score_v1",
            native_revision=1,
            native_lifecycle="recorded",
            native_disposition=score.disposition,
            lineage_reference=public_model.activity_id,
            reader_contract_version=CONCORD_DECLARATION.reader_contract_version,
            projection_contract_version=CONCORD_DECLARATION.candidate_projection_contract_version,
        )
        fields = [
            ProjectionField(key="disposition", value=score.disposition),
            ProjectionField(key="scale_id", value=score.scale_id),
            ProjectionField(key="target_kind", value=score.target_kind),
            ProjectionField(key="target_id", value=score.target_id),
        ]
        if score.value is not None:
            fields.append(ProjectionField(key="native_value", value=score.value))
        sources.append(
            ProjectedProducerSource(
                projection_kind="concord_fixture:score_summary",
                producer_source=score_source,
                source_artifact=SourceArtifactReference(
                    artifact_id=f"{score.score_id}_summary",
                    artifact_kind="assessment_summary",
                    representation_kind="concord_fixture:score_summary",
                    media_type=FIXTURE_MEDIA_TYPE,
                    source_locator=None,
                    native_revision=1,
                    source_digest=None,
                    byte_size=None,
                    language="en",
                    accessibility_relationship=None,
                ),
                source_relationships=(
                    ProjectedProducerRelationship(
                        source_subject_kind=score.target_kind,
                        source_subject_id=score.target_id,
                        relationship_kind=target_relationship,
                        relationship_authority="concord_fixture",
                        supporting_source_reference=score.score_id,
                    ),
                ),
                source_privacy=_collaborative_privacy(public_model.privacy_classification),
                display_snapshot=ProjectionDisplaySnapshot(
                    title=f"Synthetic score summary {score.score_id}",
                    summary="Producer-native Score target and disposition preserved.",
                    fields=tuple(fields),
                ),
            )
        )
    return _batch(CONCORD_DECLARATION, tuple(sources))


SCOREFORM_DECLARATION = ProducerProjectionAdapterDeclaration(
    adapter_id="vitrine_scoreform_fixture_adapter",
    adapter_contract_version=FIXTURE_ADAPTER_CONTRACT_VERSION,
    candidate_projection_contract_version=FIXTURE_PROJECTION_CONTRACT_VERSION,
    support_key=SCOREFORM_FIXTURE_SUPPORT_KEY,
    public_reader_id=ScoreFormFixtureReader.descriptor.public_reader_id,
    reader_contract_version=ScoreFormFixtureReader.descriptor.reader_contract_version,
    reader_package_identity=ScoreFormFixtureReader.descriptor.package_identity,
    supported_source_families=("assessment_result",),
    supported_representation_families=("result_summary",),
    diagnostic_contract_version=FIXTURE_DIAGNOSTIC_CONTRACT_VERSION,
    integration_kind="development_fixture",
)
QUILLAN_DECLARATION = ProducerProjectionAdapterDeclaration(
    adapter_id="vitrine_quillan_fixture_adapter",
    adapter_contract_version=FIXTURE_ADAPTER_CONTRACT_VERSION,
    candidate_projection_contract_version=FIXTURE_PROJECTION_CONTRACT_VERSION,
    support_key=QUILLAN_FIXTURE_SUPPORT_KEY,
    public_reader_id=QuillanFixtureReader.descriptor.public_reader_id,
    reader_contract_version=QuillanFixtureReader.descriptor.reader_contract_version,
    reader_package_identity=QuillanFixtureReader.descriptor.package_identity,
    supported_source_families=("feedback", "original_work"),
    supported_representation_families=("feedback", "original_work"),
    diagnostic_contract_version=FIXTURE_DIAGNOSTIC_CONTRACT_VERSION,
    integration_kind="development_fixture",
)
CONCORD_DECLARATION = ProducerProjectionAdapterDeclaration(
    adapter_id="vitrine_concord_fixture_adapter",
    adapter_contract_version=FIXTURE_ADAPTER_CONTRACT_VERSION,
    candidate_projection_contract_version=FIXTURE_PROJECTION_CONTRACT_VERSION,
    support_key=CONCORD_FIXTURE_SUPPORT_KEY,
    public_reader_id=ConcordFixtureReader.descriptor.public_reader_id,
    reader_contract_version=ConcordFixtureReader.descriptor.reader_contract_version,
    reader_package_identity=ConcordFixtureReader.descriptor.package_identity,
    supported_source_families=("collaborative_work", "score_summary"),
    supported_representation_families=("collaborative_work", "result_summary"),
    diagnostic_contract_version=FIXTURE_DIAGNOSTIC_CONTRACT_VERSION,
    integration_kind="development_fixture",
)


def build_development_fixture_adapter_registry() -> ProducerProjectionAdapterRegistry:
    """Build the explicit development fixture registry.

    This function performs no installed package discovery and reads no fixture
    payloads. Callers must separately supply immutable fixture bytes to a selected
    reader.
    """

    adapters: tuple[ProducerProjectionAdapter, ...] = (
        _FixtureProjectionAdapter(
            SCOREFORM_DECLARATION, ScoreFormFixtureReader(), _scoreform_project
        ),
        _FixtureProjectionAdapter(
            QUILLAN_DECLARATION, QuillanFixtureReader(), _quillan_project
        ),
        _FixtureProjectionAdapter(
            CONCORD_DECLARATION, ConcordFixtureReader(), _concord_project
        ),
    )
    return ProducerProjectionAdapterRegistry(adapters=adapters)


__all__ = [
    "CONCORD_FIXTURE_MANIFEST_CONTRACT",
    "CONCORD_FIXTURE_SUPPORT_KEY",
    "CONCORD_FIXTURE_SUPPORT_REQUEST",
    "QUILLAN_FIXTURE_MANIFEST_CONTRACT",
    "QUILLAN_FIXTURE_SUPPORT_KEY",
    "QUILLAN_FIXTURE_SUPPORT_REQUEST",
    "SCOREFORM_FIXTURE_MANIFEST_CONTRACT",
    "SCOREFORM_FIXTURE_SUPPORT_KEY",
    "SCOREFORM_FIXTURE_SUPPORT_REQUEST",
    "ConcordFixtureReader",
    "QuillanFixtureReader",
    "ScoreFormFixtureReader",
    "build_development_fixture_adapter_registry",
]
